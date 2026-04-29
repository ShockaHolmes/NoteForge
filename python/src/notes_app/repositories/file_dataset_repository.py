"""Filesystem-backed repository for dataset assets."""

import csv
import io
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import yaml

from notes_app.models.dataset import Dataset, DatasetSchemaField
from notes_app.models.dataset_metadata import DatasetMetadata
from notes_app.repositories.dataset_repository import DatasetRepository
from notes_app.repositories.dataset_sidecar import parse_sidecar, render_sidecar


_LOG = logging.getLogger(__name__)


class FileDatasetRepository(DatasetRepository):
    """
    Stores each dataset as two files inside *datasets_dir*:

    - ``<original-filename>``          — the raw data file (CSV / JSON), written once
    - ``<original-filename>.dataset.yml`` — YAML sidecar with all metadata

    For metadata-only datasets (no data file):

    - ``<dataset-id>.dataset.yml``     — YAML sidecar only
    """

    def __init__(self, datasets_dir: Path) -> None:
        self._datasets_dir = datasets_dir
        self._datasets_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # AssetRepository[Dataset] implementation
    # ------------------------------------------------------------------

    def save(self, item: Dataset) -> None:
        """Write (or overwrite) the sidecar for *item*."""
        normalized = replace(item, path=DatasetMetadata._normalize_relative_path(item.path))
        sidecar_path = self._sidecar_path_for(normalized)
        sidecar_path.write_text(render_sidecar(normalized), encoding="utf-8")

    def list_all(self) -> Iterable[Dataset]:
        results: list[Dataset] = []
        for path in sorted(self._datasets_dir.glob("*.dataset.yml")):
            dataset = self._load_sidecar_dataset(path)
            if dataset is not None:
                results.append(dataset)
        return results

    def get_by_id(self, item_id: str) -> Dataset | None:
        for dataset in self.list_all():
            if dataset.id == item_id:
                return dataset
        return None

    def delete_by_id(self, item_id: str) -> bool:
        for sidecar_path in sorted(self._datasets_dir.glob("*.dataset.yml")):
            dataset = self._load_sidecar_dataset(sidecar_path)
            if dataset is None:
                continue
            if dataset.id == item_id:
                # Remove the data file if it exists
                if dataset.path:
                    data_path = self._datasets_dir / dataset.path
                    if data_path.exists():
                        data_path.unlink()
                sidecar_path.unlink()
                return True
        return False

    # ------------------------------------------------------------------
    # DatasetRepository extension
    # ------------------------------------------------------------------

    def save_with_file(
        self,
        dataset: Dataset,
        file_bytes: bytes,
        filename: str,
    ) -> Dataset:
        """
        Write *file_bytes* to *filename* (unchanged) and save the sidecar.

        Updates ``path``, ``size_bytes``, and ``format`` (from file extension)
        on the returned Dataset.
        """
        # Validate extension before writing anything
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext not in ("csv", "json"):
            raise ValueError(
                f"Unsupported file type '.{ext}'. Only CSV and JSON files are accepted."
            )

        relative_name = DatasetMetadata._normalize_relative_path(Path(filename).name)

        # Write data file unchanged
        data_path = self._datasets_dir / relative_name
        data_path.write_bytes(file_bytes)

        # Populate file-derived metadata fields
        updated = replace(
            dataset,
            path=relative_name,
            size_bytes=len(file_bytes),
            format=ext if not dataset.format else dataset.format,
        )
        if ext == "csv":
            row_count, schema_fields = self._inspect_csv(file_bytes)
            updated = replace(
                updated,
                row_count=row_count,
                column_count=len(schema_fields),
                schema_fields=schema_fields,
            )
        if ext == "json":
            row_count, schema_fields = self._inspect_json(file_bytes)
            updated = replace(
                updated,
                row_count=row_count,
                column_count=len(schema_fields),
                schema_fields=schema_fields,
            )

        # Write sidecar next to the data file
        sidecar_path = self._datasets_dir / f"{relative_name}.dataset.yml"
        sidecar_path.write_text(render_sidecar(updated), encoding="utf-8")

        return updated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sidecar_path_for(self, dataset: Dataset) -> Path:
        """Return the sidecar path that corresponds to *dataset*."""
        if dataset.path:
            return self._datasets_dir / f"{dataset.path}.dataset.yml"
        return self._datasets_dir / f"{dataset.id}.dataset.yml"

    def _load_sidecar_dataset(self, sidecar_path: Path) -> Dataset | None:
        """Read one sidecar file safely, returning None when it is invalid."""
        try:
            text = sidecar_path.read_text(encoding="utf-8")
            return parse_sidecar(text)
        except (OSError, UnicodeDecodeError, ValueError, TypeError, yaml.YAMLError) as exc:
            _LOG.warning("Skipping invalid dataset sidecar %s: %s", sidecar_path.name, exc)
            return None

    @staticmethod
    def _inspect_csv(file_bytes: bytes) -> tuple[int, tuple[DatasetSchemaField, ...]]:
        """Return (data_row_count, schema_fields) from raw CSV bytes."""
        try:
            decoded = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "CSV file is not valid UTF-8 and could not be inspected."
            ) from exc

        reader = csv.reader(io.StringIO(decoded))
        try:
            header = next(reader)
        except StopIteration:
            return 0, ()

        columns = [name.strip() for name in header if name.strip()]
        data_row_count = sum(1 for _ in reader)
        schema_fields = tuple(
            DatasetSchemaField(name=column, type="string", nullable=True)
            for column in columns
        )
        return data_row_count, schema_fields

    @staticmethod
    def _inspect_json(file_bytes: bytes) -> tuple[int, tuple[DatasetSchemaField, ...]]:
        """Return (row_count, schema_fields) inferred from JSON bytes."""
        try:
            decoded = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "JSON file is not valid UTF-8 and could not be inspected."
            ) from exc

        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON file. Please upload valid JSON.") from exc

        if isinstance(payload, list):
            row_count = len(payload)
            field_names: list[str] = []
            seen: set[str] = set()
            for item in payload:
                if isinstance(item, dict):
                    for key in item.keys():
                        key_str = str(key)
                        if key_str not in seen:
                            seen.add(key_str)
                            field_names.append(key_str)
        elif isinstance(payload, dict):
            row_count = 1
            field_names = [str(key) for key in payload.keys()]
        else:
            row_count = 0
            field_names = []

        schema_fields = tuple(
            DatasetSchemaField(name=field_name, type="string", nullable=True)
            for field_name in field_names
        )
        return row_count, schema_fields
