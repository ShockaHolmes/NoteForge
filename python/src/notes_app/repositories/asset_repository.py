"""Generic storage boundary shared by all asset repositories."""

from abc import ABC, abstractmethod
from typing import Generic, Iterable, TypeVar

from notes_app.models.asset import Asset

T = TypeVar("T", bound=Asset)


class AssetRepository(ABC, Generic[T]):
    """
    Generic storage boundary used by asset services.

    Concrete repositories (e.g. ``FileNoteRepository``, a future
    ``FileDatasetRepository``) inherit from ``AssetRepository[T]``
    and implement all four abstract methods.
    """

    @abstractmethod
    def save(self, item: T) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> Iterable[T]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, item_id: str) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_id(self, item_id: str) -> bool:
        raise NotImplementedError
