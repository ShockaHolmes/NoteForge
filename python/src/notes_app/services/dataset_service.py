"""Use-case layer for dataset assets."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone

from notes_app.models.dataset import Dataset
from notes_app.repositories.dataset_repository import DatasetRepository
from notes_app.services.asset_service import AssetService


_LOG = logging.getLogger(__name__)
_PROFILE_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dataset-profile")


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
            saved = self._repository.save_with_file(dataset, file_bytes, original_filename)
            self._enqueue_profile_job(saved.id)
            return saved
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

    def preview_dataset(
        self,
        dataset_id: str,
        limit: int,
    ) -> tuple[Dataset, dict[str, object]] | None:
        dataset = self._repository.get_by_id(dataset_id)
        if dataset is None:
            return None
        preview = self._repository.preview(dataset, limit)
        return dataset, preview

    def profile_dataset(
        self,
        dataset_id: str,
    ) -> tuple[Dataset, dict[str, object]] | None:
        dataset = self._repository.get_by_id(dataset_id)
        if dataset is None:
            return None
        profile = self._repository.profile(dataset)
        return dataset, profile

    def _enqueue_profile_job(self, dataset_id: str) -> None:
        """Queue background profiling so uploads do not block on long profiling work."""
        _PROFILE_EXECUTOR.submit(self._run_profile_job, dataset_id)

    def _run_profile_job(self, dataset_id: str) -> None:
        """Compute and persist profile data in sidecar metadata."""
        dataset = self._repository.get_by_id(dataset_id)
        if dataset is None:
            return
        try:
            profile = self._repository.profile(dataset)
            self._repository.save_profile(dataset, profile)
        except Exception:
            # Profiling failures should not remove or corrupt original dataset files.
            _LOG.exception("Background profiling failed for dataset '%s'", dataset_id)

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
