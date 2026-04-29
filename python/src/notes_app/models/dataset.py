"""Domain entity for a dataset asset."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import SupportsInt

from notes_app.models.asset import Asset, AssetType


@dataclass(frozen=True)
class DatasetSchemaField:
    """Describes a single column in a dataset's schema."""

    name: str
    type: str
    nullable: bool = True


@dataclass(frozen=True)
class Dataset(Asset):
    """
    Domain entity representing one dataset.

    Fields mirror the canonical dataset-metadata-schema.example.yml so that
    a ``FileDatasetRepository`` can round-trip the sidecar YAML without loss.
    """

    # --- required (no defaults) ---
    id: str
    title: str
    created: datetime
    modified: datetime

    # --- common Asset fields ---
    author: str = ""
    tags: tuple[str, ...] = ()

    # --- dataset-specific ---
    status: str = ""
    priority: int = 0
    format: str = ""
    encoding: str = "utf-8"
    path: str = ""
    size_bytes: int = 0
    row_count: int = 0
    column_count: int = 0
    schema_fields: tuple[DatasetSchemaField, ...] = ()
    version: int = 1

    @property
    def asset_type(self) -> AssetType:
        return AssetType.DATASET

    @staticmethod
    def create(
        dataset_id: str,
        title: str,
        author: str = "",
        tags: tuple[str, ...] = (),
    ) -> "Dataset":
        now = datetime.now(timezone.utc)
        return Dataset(
            id=dataset_id,
            title=title,
            created=now,
            modified=now,
            author=author,
            tags=tags,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "created": self._to_iso(self.created),
            "modified": self._to_iso(self.modified),
            "tags": list(self.tags),
            "status": self.status,
            "priority": self.priority,
            "format": self.format,
            "encoding": self.encoding,
            "path": self.path,
            "sizeBytes": self.size_bytes,
            "rowCount": self.row_count,
            "columnCount": self.column_count,
            "schema": [
                {"name": f.name, "type": f.type, "nullable": f.nullable}
                for f in self.schema_fields
            ],
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Dataset":
        dataset_id = str(data.get("id") or "untitled")
        title = str(data.get("title") or dataset_id)
        created = cls._from_iso(data.get("created"))
        modified = cls._from_iso(data.get("modified"), fallback=created)
        author = str(data.get("author") or "")
        tags_value = data.get("tags", [])
        tags = cls._normalize_tags(tags_value)
        schema_raw = data.get("schema", [])
        schema_fields: tuple[DatasetSchemaField, ...]
        if isinstance(schema_raw, list):
            schema_fields = tuple(
                DatasetSchemaField(
                    name=str(f.get("name", "")),
                    type=str(f.get("type", "")),
                    nullable=bool(f.get("nullable", True)),
                )
                for f in schema_raw
                if isinstance(f, dict)
            )
        else:
            schema_fields = ()
        return cls(
            id=dataset_id,
            title=title,
            created=created,
            modified=modified,
            author=author,
            tags=tags,
            status=str(data.get("status") or ""),
            priority=cls._to_int(data.get("priority"), default=0),
            format=str(data.get("format") or ""),
            encoding=str(data.get("encoding") or "utf-8"),
            path=str(data.get("path") or ""),
            size_bytes=cls._to_int(data.get("sizeBytes"), default=0),
            row_count=cls._to_int(data.get("rowCount"), default=0),
            column_count=cls._to_int(data.get("columnCount"), default=0),
            schema_fields=schema_fields,
            version=cls._to_int(data.get("version"), default=1),
        )

    @staticmethod
    def _normalize_tags(value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            stripped = value.strip()
            return (stripped,) if stripped else ()
        if isinstance(value, (list, tuple)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()

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
