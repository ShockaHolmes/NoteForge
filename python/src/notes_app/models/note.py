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
    status: str = "draft"
    priority: int = 3
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
        status: str = "draft",
        priority: int = 3,
    ) -> "Note":
        now = datetime.now(timezone.utc)
        return Note(
            id=note_id,
            title=title,
            created=now,
            modified=now,
            author=author,
            tags=tags,
            status=Note._normalize_status(status),
            priority=Note._normalize_priority(priority),
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
            "status": self.status,
            "priority": self.priority,
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
        status = cls._normalize_status(data.get("status"))
        priority = cls._normalize_priority(data.get("priority"))
        content = str(data.get("content") or "")
        return cls(
            id=note_id,
            title=title,
            created=created,
            modified=modified,
            author=author,
            tags=tags,
            status=status,
            priority=priority,
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
            "status": self.status,
            "priority": self.priority,
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
    def _normalize_status(value: object) -> str:
        status = str(value or "draft").strip().lower()
        if status in {"complete", "completed", "done"}:
            return "complete"
        if status in {"active", "in-progress", "inprogress", "updating"}:
            return "active"
        if status in {"draft", "incomplete", "new"}:
            return "draft"
        return "draft"

    @staticmethod
    def _normalize_priority(value: object) -> int:
        try:
            priority = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 3
        return priority if priority in {1, 2, 3, 4, 5} else 3

    @staticmethod
    def _to_iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _from_iso(value: object, fallback: datetime | None = None) -> datetime:
        if not value:
            return fallback if fallback is not None else datetime.now(timezone.utc)
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
