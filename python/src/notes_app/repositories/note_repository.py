from abc import ABC, abstractmethod
from typing import Iterable

from notes_app.models.note import Note


class NoteRepository(ABC):
    """Storage boundary used by services."""

    @abstractmethod
    def save(self, note: Note) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_notes(self) -> Iterable[Note]:
        raise NotImplementedError
