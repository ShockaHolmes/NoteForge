"""Metadata model for dataset sidecar YAML files."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import SupportsInt

import yaml

from notes_app.models.dataset import Dataset, DatasetSchemaField


@dataclass(frozen=True)
class DatasetMetadata:
    """Represents the persisted contents of one ``.dataset.yml`` file."""

    id: str
    title: str
    author: str
    created: datetime
    modified: datetime
    tags: tuple[str, ...] = ()
    status: str = ""
    priority: int = 0
    format: str = ""
    path: str = ""
    size_bytes: int = 0
    row_count: int = 0
    column_count: int = 0
    schema: tuple[DatasetSchemaField, ...] = ()
    version: int = 1

    @classmethod
    def from_dataset(cls, dataset: Dataset) -> "DatasetMetadata":
        return cls(
            id=dataset.id,
            title=dataset.title,
            author=dataset.author,
            created=dataset.created,
            modified=dataset.modified,
            tags=dataset.tags,
            status=dataset.status,
            priority=dataset.priority,
            format=dataset.format,
            path=cls._normalize_relative_path(dataset.path),
            size_bytes=dataset.size_bytes,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            schema=dataset.schema_fields,
            version=dataset.version,
        )

    def to_dataset(self) -> Dataset:
        return Dataset(
            id=self.id,
            title=self.title,
            author=self.author,
            created=self.created,
            modified=self.modified,
            tags=self.tags,
            status=self.status,
            priority=self.priority,
            format=self.format,
            path=self._normalize_relative_path(self.path),
            size_bytes=self.size_bytes,
            row_count=self.row_count,
            column_count=self.column_count,
            schema_fields=self.schema,
            version=self.version,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "assetType": "dataset",
            "title": self.title,
            "author": self.author,
            "created": self._to_iso(self.created),
            "modified": self._to_iso(self.modified),
            "tags": list(self.tags),
            "status": self.status,
            "priority": self.priority,
            "format": self.format,
            "path": self._normalize_relative_path(self.path),
            "sizeBytes": self.size_bytes,
            "rowCount": self.row_count,
            "columnCount": self.column_count,
            "schema": [
                {"name": field.name, "type": field.type, "nullable": field.nullable}
                for field in self.schema
            ],
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DatasetMetadata":
        schema_raw = data.get("schema", [])
        schema: tuple[DatasetSchemaField, ...] = ()
        if isinstance(schema_raw, list):
            schema = tuple(
                DatasetSchemaField(
                    name=str(field.get("name") or ""),
                    type=str(field.get("type") or ""),
                    nullable=bool(field.get("nullable", True)),
                )
                for field in schema_raw
                if isinstance(field, dict)
            )
        return cls(
            id=str(data.get("id") or "untitled"),
            title=str(data.get("title") or data.get("id") or "untitled"),
            author=str(data.get("author") or ""),
            created=cls._from_iso(data.get("created")),
            modified=cls._from_iso(data.get("modified"), fallback=cls._from_iso(data.get("created"))),
            tags=cls._normalize_tags(data.get("tags", [])),
            status=str(data.get("status") or ""),
            priority=cls._to_int(data.get("priority"), default=0),
            format=str(data.get("format") or ""),
            path=cls._normalize_relative_path(str(data.get("path") or "")),
            size_bytes=cls._to_int(data.get("sizeBytes"), default=0),
            row_count=cls._to_int(data.get("rowCount"), default=0),
            column_count=cls._to_int(data.get("columnCount"), default=0),
            schema=schema,
            version=cls._to_int(data.get("version"), default=1),
        )

    def to_yaml(self) -> str:
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, text: str) -> "DatasetMetadata":
        data: dict[str, object] = yaml.safe_load(text) or {}
        return cls.from_dict(data)

    @staticmethod
    def _normalize_tags(value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            stripped = value.strip()
            return (stripped,) if stripped else ()
        if isinstance(value, (list, tuple)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()

    @staticmethod
    def _normalize_relative_path(value: str) -> str:
        candidate = value.strip()
        if not candidate:
            return ""
        path = PurePosixPath(candidate.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Dataset metadata path must be relative to the datasets folder.")
        return path.as_posix()

    @staticmethod
    def _to_iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _from_iso(value: object, fallback: datetime | None = None) -> datetime:
        if not value:
            return fallback if fallback is not None else datetime.now(timezone.utc)
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)

    @staticmethod
    def _to_int(value: object, default: int) -> int:
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        if isinstance(value, SupportsInt):
            return int(value)
        return default
