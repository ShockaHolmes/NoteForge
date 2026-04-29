"""Abstract storage boundary for dataset assets."""

from abc import abstractmethod

from notes_app.models.dataset import Dataset
from notes_app.repositories.asset_repository import AssetRepository


class DatasetRepository(AssetRepository[Dataset]):
    """
    Storage boundary used by DatasetService.

    Extends ``AssetRepository[Dataset]`` with ``save_with_file`` to support
    storing raw data files (CSV, JSON) alongside their sidecar metadata.
    """

    @abstractmethod
    def save_with_file(
        self,
        dataset: Dataset,
        file_bytes: bytes,
        filename: str,
    ) -> Dataset:
        """
        Persist *file_bytes* as *filename* and write the accompanying sidecar.

        Returns the updated Dataset with ``path`` and ``size_bytes`` filled in.
        """
        raise NotImplementedError
