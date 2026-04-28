import re

from notes_app.models.note import Note
from notes_app.repositories.note_repository import NoteRepository


class NoteService:
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

    @staticmethod
    def _slugify(title: str) -> str:
        lowered = title.strip().lower()
        collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
        slug = collapsed.strip("-")
        return slug or "untitled"
