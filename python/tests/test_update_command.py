from datetime import datetime, timezone

import pytest

from notes_app.cli.commands.update_command import run_update
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


_CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)
_MODIFIED = datetime(2026, 2, 1, tzinfo=timezone.utc)


def _make_note() -> Note:
    return Note(
        id="my-note",
        title="Original Title",
        created=_CREATED,
        modified=_MODIFIED,
        tags=("old-tag",),
        content="Original content.",
    )


def _service_with_note() -> tuple[NoteService, InMemoryNoteRepository]:
    repo = InMemoryNoteRepository([_make_note()])
    return NoteService(repo), repo


def test_update_title() -> None:
    service, repo = _service_with_note()

    output, ok = run_update(service, note_id="my-note", args=["--title", "New Title"])

    assert ok is True
    assert "my-note.md" in output
    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.title == "New Title"


def test_update_tags() -> None:
    service, repo = _service_with_note()

    output, ok = run_update(service, note_id="my-note", args=["--tags", "python,demo"])

    assert ok is True
    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.tags == ("python", "demo")


def test_update_content() -> None:
    service, repo = _service_with_note()

    output, ok = run_update(service, note_id="my-note", args=["--content", "New body."])

    assert ok is True
    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.content == "New body."


def test_update_all_fields() -> None:
    service, repo = _service_with_note()

    output, ok = run_update(
        service,
        note_id="my-note",
        args=["--title", "T", "--tags", "a,b", "--content", "C"],
    )

    assert ok is True
    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.title == "T"
    assert saved.tags == ("a", "b")
    assert saved.content == "C"


def test_update_modified_timestamp_changes() -> None:
    service, repo = _service_with_note()

    run_update(service, note_id="my-note", args=["--title", "Changed"])

    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.modified > _MODIFIED


def test_update_created_timestamp_unchanged() -> None:
    service, repo = _service_with_note()

    run_update(service, note_id="my-note", args=["--title", "Changed"])

    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.created == _CREATED


def test_update_accepts_md_suffix() -> None:
    service, repo = _service_with_note()

    output, ok = run_update(service, note_id="my-note.md", args=["--title", "Via suffix"])

    assert ok is True
    assert repo.get_by_id("my-note") is not None


def test_update_missing_note_returns_error() -> None:
    service, _ = _service_with_note()

    output, ok = run_update(service, note_id="ghost", args=["--title", "X"])

    assert ok is False
    assert "ghost" in output
    assert "not found" in output.lower()


def test_update_no_flags_returns_error() -> None:
    service, _ = _service_with_note()

    output, ok = run_update(service, note_id="my-note", args=[])

    assert ok is False


def test_update_unknown_flag_returns_error() -> None:
    service, _ = _service_with_note()

    output, ok = run_update(service, note_id="my-note", args=["--body", "x"])

    assert ok is False


def test_update_empty_tags_clears_tags() -> None:
    service, repo = _service_with_note()

    output, ok = run_update(service, note_id="my-note", args=["--tags", ""])

    assert ok is True
    saved = repo.get_by_id("my-note")
    assert saved is not None
    assert saved.tags == ()
