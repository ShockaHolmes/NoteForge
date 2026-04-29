from pathlib import Path
from typing import Iterable

from notes_app.models.note import Note
from notes_app.repositories.frontmatter import parse_note_text, render_frontmatter
from notes_app.repositories.note_repository import NoteRepository


class FileNoteRepository(NoteRepository):
    """Filesystem-backed repository for markdown notes."""

    def __init__(self, notes_dir: Path):
        self._notes_dir = notes_dir
        self._notes_dir.mkdir(parents=True, exist_ok=True)

    def save(self, note: Note) -> None:
        note_path = self._notes_dir / f"{note.slug}.md"
        text = f"{render_frontmatter(note)}{note.content}"
        note_path.write_text(text, encoding="utf-8")

    def list_notes(self) -> Iterable[Note]:
        notes: list[Note] = []
        for path in sorted(self._notes_dir.glob("*.md")):
            note_text = path.read_text(encoding="utf-8")
            notes.append(parse_note_text(path.stem, note_text))
        return notes

    def get_by_id(self, note_id: str) -> Note | None:
        note_path = self._notes_dir / f"{note_id}.md"
        if not note_path.exists():
            return None
        note_text = note_path.read_text(encoding="utf-8")
        return parse_note_text(note_id, note_text)
