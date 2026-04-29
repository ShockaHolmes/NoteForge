"""Use-case layer for dataset assets."""

import re
from dataclasses import replace
from datetime import datetime, timezone

from notes_app.models.dataset import Dataset
from notes_app.repositories.dataset_repository import DatasetRepository
from notes_app.services.asset_service import AssetService


class DatasetService(AssetService[Dataset]):
    """Business logic for dataset CRUD — no CLI or storage details."""

    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------
    # Domain operations
    # ------------------------------------------------------------------

    def create_dataset(
        self,
        title: str,
        author: str = "",
        tags: tuple[str, ...] = (),
        file_bytes: bytes | None = None,
        original_filename: str | None = None,
    ) -> Dataset:
        """Create and persist a new dataset, optionally with a raw data file."""
        dataset_id = self._slugify(title)
        dataset = Dataset.create(
            dataset_id=dataset_id,
            title=title,
            author=author,
            tags=tags,
        )
        if file_bytes is not None and original_filename:
            return self._repository.save_with_file(dataset, file_bytes, original_filename)
        self._repository.save(dataset)
        return dataset

    def list_datasets(self) -> list[Dataset]:
        return list(self._repository.list_all())

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        return self._repository.get_by_id(dataset_id)

    def update_dataset(
        self,
        dataset_id: str,
        title: str | None = None,
        tags: tuple[str, ...] | None = None,
        status: str | None = None,
        priority: int | None = None,
    ) -> Dataset | None:
        existing = self._repository.get_by_id(dataset_id)
        if existing is None:
            return None
        updated = replace(
            existing,
            title=title if title is not None else existing.title,
            tags=tags if tags is not None else existing.tags,
            status=status if status is not None else existing.status,
            priority=priority if priority is not None else existing.priority,
            modified=datetime.now(timezone.utc),
        )
        self._repository.save(updated)
        return updated

    def delete_dataset(self, dataset_id: str) -> Dataset | None:
        existing = self._repository.get_by_id(dataset_id)
        if existing is None:
            return None
        deleted = self._repository.delete_by_id(dataset_id)
        if not deleted:
            return None
        return existing

    # ------------------------------------------------------------------
    # AssetService[Dataset] interface
    # ------------------------------------------------------------------

    def list_assets(self) -> list[Dataset]:
        return self.list_datasets()

    def get_asset(self, item_id: str) -> Dataset | None:
        return self.get_dataset(item_id)

    def delete_asset(self, item_id: str) -> Dataset | None:
        return self.delete_dataset(item_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(title: str) -> str:
        lowered = title.strip().lower()
        collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
        slug = collapsed.strip("-")
        return slug or "untitled"
