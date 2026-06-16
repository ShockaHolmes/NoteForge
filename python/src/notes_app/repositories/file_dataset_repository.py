"""Filesystem-backed repository for dataset assets."""

import csv
import io
import json
import logging
import os
import tempfile
from dataclasses import replace
from datetime import datetime
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
        self._write_text_atomic(sidecar_path, render_sidecar(normalized))

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
        self._write_text_atomic(sidecar_path, render_sidecar(updated))

        return updated

    def profile(self, dataset: Dataset) -> dict[str, object]:
        """Return dataset profiling data from sidecar metadata or computed stats."""
        sidecar_path = self._sidecar_path_for(dataset)
        sidecar_profile = self._read_profile_from_sidecar(sidecar_path)
        if sidecar_profile is not None:
            return sidecar_profile

        if not dataset.path:
            raise ValueError("Dataset has no raw file to profile.")

        data_path = self._datasets_dir / dataset.path
        if not data_path.exists():
            raise FileNotFoundError(f"Dataset file '{dataset.path}' was not found.")

        ext = Path(dataset.path).suffix.lstrip(".").lower() or dataset.format.lower()
        if ext == "csv":
            return self._profile_csv(data_path)
        if ext == "json":
            return self._profile_json(data_path)
        raise ValueError(f"Profiling is not supported for dataset format '{ext}'.")

    def save_profile(self, dataset: Dataset, profile: dict[str, object]) -> None:
        """Persist profile payload into the dataset sidecar metadata."""
        sidecar_path = self._sidecar_path_for(dataset)
        if not sidecar_path.exists():
            return
        try:
            raw_data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
            data = raw_data if isinstance(raw_data, dict) else {}
            data["profile"] = profile
            self._write_text_atomic(sidecar_path, yaml.safe_dump(data, sort_keys=False))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            _LOG.warning("Unable to save profile for sidecar %s: %s", sidecar_path.name, exc)

    def preview(self, dataset: Dataset, limit: int) -> dict[str, object]:
        """Return a preview payload for a CSV or JSON dataset file."""
        if limit < 1:
            raise ValueError("Preview limit must be at least 1.")
        if not dataset.path:
            raise ValueError("Dataset has no raw file to preview.")

        data_path = self._datasets_dir / dataset.path
        if not data_path.exists():
            raise FileNotFoundError(f"Dataset file '{dataset.path}' was not found.")

        ext = Path(dataset.path).suffix.lstrip(".").lower() or dataset.format.lower()
        if ext == "csv":
            headers, rows = self._preview_csv(data_path, limit)
            return {"headers": headers, "rows": rows}
        if ext == "json":
            records = self._preview_json(data_path, limit)
            return {"records": records}

        raise ValueError(f"Preview is not supported for dataset format '{ext}'.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_text_atomic(path: Path, text: str, encoding: str = "utf-8") -> None:
        """Write *text* to *path* atomically using a temp file and ``os.replace``.

        Ensures that readers never observe a partially-written sidecar file,
        which would otherwise cause spurious 404 errors when a background
        profiling thread rewrites the sidecar concurrently with a read request.
        """
        dir_path = path.parent
        fd, tmp_name = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding=encoding) as fh:
                fh.write(text)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

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
    def _read_profile_from_sidecar(sidecar_path: Path) -> dict[str, object] | None:
        """Return sidecar profile payload when present and valid."""
        if not sidecar_path.exists():
            return None
        try:
            data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
            profile = data.get("profile") if isinstance(data, dict) else None
            return profile if isinstance(profile, dict) else None
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
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

    @staticmethod
    def _preview_csv(data_path: Path, limit: int) -> tuple[list[str], list[list[str]]]:
        """Return CSV headers and first N data rows."""
        try:
            with data_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                try:
                    headers = [h.strip() for h in next(reader)]
                except StopIteration:
                    return [], []
                rows: list[list[str]] = []
                for row in reader:
                    rows.append(row)
                    if len(rows) >= limit:
                        break
                return headers, rows
        except UnicodeDecodeError as exc:
            raise ValueError(
                "CSV file is not valid UTF-8 and could not be previewed."
            ) from exc

    @staticmethod
    def _preview_json(data_path: Path, limit: int) -> list[object]:
        """Return first N JSON records for arrays, or one record for objects."""
        try:
            raw = data_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "JSON file is not valid UTF-8 and could not be previewed."
            ) from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON file. Please upload valid JSON.") from exc

        if isinstance(payload, list):
            return list(payload[:limit])
        if isinstance(payload, dict):
            return [payload]
        return [payload]

    @staticmethod
    def _profile_csv(data_path: Path) -> dict[str, object]:
        """Compute basic column profile stats for a CSV file."""
        try:
            with data_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                headers = reader.fieldnames or []
                missing_counts = {header: 0 for header in headers}
                observed_types: dict[str, set[str]] = {header: set() for header in headers}
                row_count = 0
                for row in reader:
                    row_count += 1
                    for header in headers:
                        value = row.get(header)
                        if value is None or str(value).strip() == "":
                            missing_counts[header] += 1
                            continue
                        inferred = FileDatasetRepository._infer_text_type(str(value).strip())
                        observed_types[header].add(inferred)
        except UnicodeDecodeError as exc:
            raise ValueError("CSV file is not valid UTF-8 and could not be profiled.") from exc

        columns = [
            {
                "name": header,
                "inferredType": FileDatasetRepository._resolve_inferred_type(observed_types[header]),
                "missingValues": missing_counts[header],
            }
            for header in headers
        ]
        return {"source": "computed", "rowCount": row_count, "columns": columns}

    @staticmethod
    def _profile_json(data_path: Path) -> dict[str, object]:
        """Compute basic column profile stats for a JSON file."""
        try:
            raw = data_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("JSON file is not valid UTF-8 and could not be profiled.") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON file. Please upload valid JSON.") from exc

        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            records = [payload]
        else:
            records = []

        field_names: list[str] = []
        seen: set[str] = set()
        for item in records:
            for key in item.keys():
                key_str = str(key)
                if key_str not in seen:
                    seen.add(key_str)
                    field_names.append(key_str)

        missing_counts = {name: 0 for name in field_names}
        observed_types: dict[str, set[str]] = {name: set() for name in field_names}
        for item in records:
            for name in field_names:
                if name not in item or item[name] is None or item[name] == "":
                    missing_counts[name] += 1
                    continue
                observed_types[name].add(FileDatasetRepository._infer_json_type(item[name]))

        columns = [
            {
                "name": name,
                "inferredType": FileDatasetRepository._resolve_inferred_type(observed_types[name]),
                "missingValues": missing_counts[name],
            }
            for name in field_names
        ]
        return {"source": "computed", "rowCount": len(records), "columns": columns}

    @staticmethod
    def _infer_text_type(value: str) -> str:
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return "boolean"
        if FileDatasetRepository._is_int(value):
            return "integer"
        if FileDatasetRepository._is_float(value):
            return "number"
        if FileDatasetRepository._is_datetime(value):
            return "datetime"
        return "string"

    @staticmethod
    def _infer_json_type(value: object) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return FileDatasetRepository._infer_text_type(value)
        return "string"

    @staticmethod
    def _resolve_inferred_type(types: set[str]) -> str:
        if not types:
            return "unknown"
        if types == {"integer"}:
            return "integer"
        if types.issubset({"integer", "number"}):
            return "number"
        if len(types) == 1:
            return next(iter(types))
        return "string"

    @staticmethod
    def _is_int(value: str) -> bool:
        try:
            int(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_float(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_datetime(value: str) -> bool:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
