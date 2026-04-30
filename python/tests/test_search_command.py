from datetime import datetime, timezone

from notes_app.cli.commands.search_command import run_search
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


def _make_note(
    note_id: str,
    title: str,
    tags: tuple[str, ...],
    content: str,
    author: str = "",
    status: str = "draft",
    priority: int = 3,
) -> Note:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Note(
        id=note_id,
        title=title,
        created=now,
        modified=now,
        author=author,
        tags=tags,
        status=status,
        priority=priority,
        content=content,
    )


def _service() -> NoteService:
    notes = [
        _make_note("t1", "Python Release Notes", ("dev",), "General updates.", author="alex"),
        _make_note("t2", "Meeting Log", ("school", "research"), "Covered deadlines.", status="complete", priority=1),
        _make_note("t3", "Journal", ("personal",), "Learning rust and python patterns daily.", author="sam", priority=2),
    ]
    return NoteService(InMemoryNoteRepository(notes))


def test_search_matches_title() -> None:
    output = run_search(_service(), query="release")

    assert "id: t1" in output
    assert "title: Python Release Notes" in output
    assert "context: title: Python Release Notes" in output


def test_search_matches_tags() -> None:
    output = run_search(_service(), query="research")

    assert "id: t2" in output
    assert "title: Meeting Log" in output
    assert "context: tags: school, research" in output


def test_search_matches_body_with_context_excerpt() -> None:
    output = run_search(_service(), query="patterns")

    assert "id: t3" in output
    assert "title: Journal" in output
    assert "context: " in output
    assert "patterns" in output.lower()


def test_search_no_results_message() -> None:
    output = run_search(_service(), query="nonexistent-term")

    assert output == "No notes matched 'nonexistent-term'."


def test_search_matches_author() -> None:
    output = run_search(_service(), query="alex")
    assert "id: t1" in output
    assert "context: author: alex" in output


def test_search_matches_status() -> None:
    output = run_search(_service(), query="complete")
    assert "id: t2" in output
    assert "context: status: complete" in output


def test_search_matches_priority_alias() -> None:
    output = run_search(_service(), query="high")
    assert "id: t2" in output
    assert "context: priority: 1" in output