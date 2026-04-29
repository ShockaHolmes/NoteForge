from notes_app.models.note import Note
from notes_app.repositories.note_repository import NoteRepository
from notes_app.services.note_service import NoteService


class InMemoryNoteRepository(NoteRepository):
    def __init__(self):
        self._notes: list[Note] = []

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


def test_service_lists_titles_without_filesystem() -> None:
    repository = InMemoryNoteRepository()
    service = NoteService(repository)

    service.create_note("First Note", "hello")
    service.create_note("Second Note", "world")

    notes = service.list_notes()
    assert [note.title for note in notes] == ["First Note", "Second Note"]


def test_service_slugifies_title() -> None:
    repository = InMemoryNoteRepository()
    service = NoteService(repository)

    note = service.create_note("My First Note!", "hello")

    assert note.slug == "my-first-note"


def test_service_deletes_existing_note() -> None:
    repository = InMemoryNoteRepository()
    service = NoteService(repository)
    service.create_note("First Note", "hello")

    deleted = service.delete_note("first-note")

    assert deleted is not None
    assert service.get_note("first-note") is None
