"""Filesystem-backed repository for dataset assets."""

from dataclasses import replace
from pathlib import Path
from typing import Iterable

from notes_app.models.dataset import Dataset
from notes_app.models.dataset_metadata import DatasetMetadata
from notes_app.repositories.dataset_repository import DatasetRepository
from notes_app.repositories.dataset_sidecar import parse_sidecar, render_sidecar


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
            text = path.read_text(encoding="utf-8")
            results.append(parse_sidecar(text))
        return results

    def get_by_id(self, item_id: str) -> Dataset | None:
        for dataset in self.list_all():
            if dataset.id == item_id:
                return dataset
        return None

    def delete_by_id(self, item_id: str) -> bool:
        for sidecar_path in sorted(self._datasets_dir.glob("*.dataset.yml")):
            text = sidecar_path.read_text(encoding="utf-8")
            dataset = parse_sidecar(text)
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
