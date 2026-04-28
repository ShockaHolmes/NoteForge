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
    assert "Tags: tag1, tag2" in output
    assert "1 note(s) found." in output
