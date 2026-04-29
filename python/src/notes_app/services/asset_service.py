"""Generic use-case boundary shared by all asset services."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from notes_app.models.asset import Asset

T = TypeVar("T", bound=Asset)


class AssetService(ABC, Generic[T]):
    """
    Shared service interface for all asset types.

    Concrete services (e.g. ``NoteService``, a future ``DatasetService``)
    inherit from ``AssetService[T]`` and implement the three abstract methods
    that cover retrieval and deletion.  Creation and updates are left to
    concrete subclasses because their parameter shapes differ by asset type.
    """

    @abstractmethod
    def list_assets(self) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def get_asset(self, item_id: str) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def delete_asset(self, item_id: str) -> T | None:
        raise NotImplementedError
