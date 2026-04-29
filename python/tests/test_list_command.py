from datetime import datetime, timezone

from notes_app.cli.commands.list_command import run_list
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


def test_run_list_renders_notes1_style_output() -> None:
    note = Note(
        id="sample",
        title="Sample",
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        modified=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("tag1", "tag2"),
        content="hello",
    )
    service = NoteService(InMemoryNoteRepository([note]))

    output = run_list(service)

    assert "Notes:" in output
    assert "sample.md" in output
    assert "Title: Sample" in output
    assert "Modified: " in output
    assert "Tags: tag1, tag2" in output
    assert "1 note(s) found." in output


def test_run_list_empty_shows_helpful_message() -> None:
    service = NoteService(InMemoryNoteRepository([]))

    output = run_list(service)

    assert output == "No notes found."
