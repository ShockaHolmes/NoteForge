from datetime import datetime, timezone

from notes_app.cli.commands.delete_command import run_delete
from notes_app.models.note import Note
from notes_app.repositories.note_repository import NoteRepository
from notes_app.services.note_service import NoteService


class InMemoryNoteRepository(NoteRepository):
    def __init__(self, notes: list[Note]):
        self._notes = list(notes)

    def save(self, note: Note) -> None:
        self._notes = [n for n in self._notes if n.id != note.id]
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
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Note(
        id=note_id,
        title="My Note",
        created=now,
        modified=now,
        tags=("python",),
        content="hello",
    )


def test_run_delete_deletes_by_id_after_confirmation() -> None:
    repo = InMemoryNoteRepository([_make_note()])
    service = NoteService(repo)
    prompts: list[str] = []

    def confirm(prompt: str) -> str:
        prompts.append(prompt)
        return "y"

    output, ok = run_delete(service, note_id="my-note", confirm_fn=confirm)

    assert ok is True
    assert "Deleted note 'my-note.md'" in output
    assert prompts
    assert "my-note" in prompts[0]
    assert repo.get_by_id("my-note") is None


def test_run_delete_accepts_filename_with_md_suffix() -> None:
    repo = InMemoryNoteRepository([_make_note()])
    service = NoteService(repo)

    output, ok = run_delete(service, note_id="my-note.md", confirm_fn=lambda _p: "yes")

    assert ok is True
    assert "Deleted note 'my-note.md'" in output
    assert repo.get_by_id("my-note") is None


def test_run_delete_cancel_keeps_note() -> None:
    repo = InMemoryNoteRepository([_make_note()])
    service = NoteService(repo)

    output, ok = run_delete(service, note_id="my-note", confirm_fn=lambda _p: "n")

    assert ok is True
    assert output == "Delete cancelled."
    assert repo.get_by_id("my-note") is not None


def test_run_delete_missing_note_returns_clear_error() -> None:
    service = NoteService(InMemoryNoteRepository([]))

    output, ok = run_delete(service, note_id="missing", confirm_fn=lambda _p: "y")

    assert ok is False
    assert "missing" in output
    assert "not found" in output.lower()