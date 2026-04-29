from abc import abstractmethod
from typing import Iterable

from notes_app.models.note import Note
from notes_app.repositories.asset_repository import AssetRepository


class NoteRepository(AssetRepository[Note]):
    """
    Storage boundary for notes.

    Inherits the generic ``AssetRepository[Note]`` interface and
    re-exposes ``list_notes`` as an alias for ``list_all`` so that
    existing call sites require no changes.
    """

    @abstractmethod
    def save(self, item: Note) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_notes(self) -> Iterable[Note]:
        raise NotImplementedError

    def list_all(self) -> Iterable[Note]:
        """Satisfies ``AssetRepository.list_all``; delegates to ``list_notes``."""
        return self.list_notes()

    @abstractmethod
    def get_by_id(self, note_id: str) -> Note | None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_id(self, note_id: str) -> bool:
        raise NotImplementedError
