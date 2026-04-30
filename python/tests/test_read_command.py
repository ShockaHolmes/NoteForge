from datetime import datetime, timezone

from notes_app.cli.commands.read_command import run_read
from notes_app.models.note import Note
from notes_app.repositories.note_repository import NoteRepository
from notes_app.services.note_service import NoteService


class InMemoryNoteRepository(NoteRepository):
    def __init__(self, notes: list[Note]):
        self._notes = notes

    def save(self, note: Note) -> None:
        self._notes.append(note)

    def list_notes(self):
        return list(self._notes)

    def get_by_id(self, note_id: str) -> Note | None:
        return next((n for n in self._notes if n.id == note_id), None)

    def delete_by_id(self, note_id: str) -> bool:
        before = len(self._notes)
        self._notes = [note for note in self._notes if note.id != note_id]
        return len(self._notes) != before


def _make_note(note_id: str = "my-note") -> Note:
    return Note(
        id=note_id,
        title="My Note",
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        modified=datetime(2026, 3, 15, tzinfo=timezone.utc),
        tags=("python", "demo"),
        content="Hello from the body.",
    )


def test_run_read_shows_metadata_and_content() -> None:
    service = NoteService(InMemoryNoteRepository([_make_note()]))

    output, ok = run_read(service, note_id="my-note")

    assert ok is True
    assert "id:       my-note" in output
    assert "title:    My Note" in output
    assert "author:   (unknown)" in output
    assert "created:  " in output
    assert "modified: " in output
    assert "status:   draft" in output
    assert "priority: 3 (normal)" in output
    assert "tags:     python, demo" in output
    assert "Hello from the body." in output


def test_run_read_accepts_filename_with_md_suffix() -> None:
    service = NoteService(InMemoryNoteRepository([_make_note()]))

    output, ok = run_read(service, note_id="my-note.md")

    assert ok is True
    assert "id:       my-note" in output


def test_run_read_missing_note_returns_error() -> None:
    service = NoteService(InMemoryNoteRepository([]))

    output, ok = run_read(service, note_id="missing")

    assert ok is False
    assert "missing" in output
    assert "not found" in output.lower()


def test_run_read_note_with_no_tags_shows_none() -> None:
    note = Note(
        id="no-tags",
        title="No Tags",
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        modified=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=(),
        content="body",
    )
    service = NoteService(InMemoryNoteRepository([note]))

    output, ok = run_read(service, note_id="no-tags")

    assert ok is True
    assert "tags:     (none)" in output
