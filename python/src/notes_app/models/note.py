from dataclasses import dataclass
from datetime import datetime, timezone

from notes_app.models.asset import Asset, AssetType


@dataclass(frozen=True)
class Note(Asset):
    """Domain entity representing one note."""

    id: str
    title: str
    created: datetime
    modified: datetime
    author: str = ""
    tags: tuple[str, ...] = ()
    content: str = ""

    @property
    def asset_type(self) -> AssetType:
        return AssetType.NOTE

    @property
    def slug(self) -> str:
        """Backward-compatible alias for filesystem-oriented code."""
        return self.id

    @staticmethod
    def create(
        note_id: str,
        title: str,
        content: str,
        tags: tuple[str, ...] = (),
        author: str = "",
    ) -> "Note":
        now = datetime.now(timezone.utc)
        return Note(
            id=note_id,
            title=title,
            created=now,
            modified=now,
            author=author,
            tags=tags,
            content=content,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "created": self._to_iso(self.created),
            "modified": self._to_iso(self.modified),
            "tags": list(self.tags),
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Note":
        note_id = str(data.get("id") or data.get("slug") or "untitled")
        title = str(data.get("title") or note_id)
        created = cls._from_iso(data.get("created"))
        modified = cls._from_iso(data.get("modified"), fallback=created)
        author = str(data.get("author") or "")
        tags_value = data.get("tags", [])
        tags = cls._normalize_tags(tags_value)
        content = str(data.get("content") or "")
        return cls(
            id=note_id,
            title=title,
            created=created,
            modified=modified,
            author=author,
            tags=tags,
            content=content,
        )

    def to_metadata_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "created": self._to_iso(self.created),
            "modified": self._to_iso(self.modified),
            "tags": list(self.tags),
        }

    @classmethod
    def from_metadata_dict(
        cls,
        metadata: dict[str, object],
        content: str,
    ) -> "Note":
        data = dict(metadata)
        data["content"] = content
        return cls.from_dict(data)

    @staticmethod
    def _normalize_tags(value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ()
            return (stripped,)
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
