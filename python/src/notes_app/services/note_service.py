import re
from dataclasses import replace
from datetime import datetime, timezone

from notes_app.models.note import Note
from notes_app.repositories.note_repository import NoteRepository
from notes_app.services.asset_service import AssetService


class NoteService(AssetService[Note]):
    """Use-case layer: business logic without CLI or storage details."""

    def __init__(self, repository: NoteRepository):
        self._repository = repository

    def create_note(self, title: str, content: str, tags: tuple[str, ...] = ()) -> Note:
        slug = self._slugify(title)
        note = Note.create(note_id=slug, title=title, content=content, tags=tags)
        self._repository.save(note)
        return note

    def list_notes(self) -> list[Note]:
        return list(self._repository.list_notes())

    def get_note(self, note_id: str) -> Note | None:
        slug = note_id.removesuffix(".md")
        return self._repository.get_by_id(slug)

    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        tags: tuple[str, ...] | None = None,
        content: str | None = None,
    ) -> Note | None:
        slug = note_id.removesuffix(".md")
        existing = self._repository.get_by_id(slug)
        if existing is None:
            return None
        updated = replace(
            existing,
            title=title if title is not None else existing.title,
            tags=tags if tags is not None else existing.tags,
            content=content if content is not None else existing.content,
            modified=datetime.now(timezone.utc),
        )
        self._repository.save(updated)
        return updated

    def delete_note(self, note_id: str) -> Note | None:
        slug = note_id.removesuffix(".md")
        existing = self._repository.get_by_id(slug)
        if existing is None:
            return None
        deleted = self._repository.delete_by_id(slug)
        if not deleted:
            return None
        return existing

    # --- AssetService[Note] interface ---

    def list_assets(self) -> list[Note]:
        return self.list_notes()

    def get_asset(self, item_id: str) -> Note | None:
        return self.get_note(item_id)

    def delete_asset(self, item_id: str) -> Note | None:
        return self.delete_note(item_id)

    @staticmethod
    def _slugify(title: str) -> str:
        lowered = title.strip().lower()
        collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
        slug = collapsed.strip("-")
        return slug or "untitled"
