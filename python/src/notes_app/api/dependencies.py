from typing import Callable

from fastapi import Depends, Header, HTTPException, status

from notes_app.config.storage import ensure_datasets_dir
from notes_app.config.storage import ensure_notes_dir
from notes_app.repositories.file_dataset_repository import FileDatasetRepository
from notes_app.repositories.file_note_repository import FileNoteRepository
from notes_app.services.dataset_service import DatasetService
from notes_app.services.note_service import NoteService

_SUPPORTED_ROLES = {"viewer", "editor", "data-engineer", "admin"}


def get_note_service() -> NoteService:
    notes_dir = ensure_notes_dir()
    repository = FileNoteRepository(notes_dir)
    return NoteService(repository)


NoteServiceDep = Depends(get_note_service)


def get_dataset_service() -> DatasetService:
    datasets_dir = ensure_datasets_dir()
    repository = FileDatasetRepository(datasets_dir)
    return DatasetService(repository)


DatasetServiceDep = Depends(get_dataset_service)


def get_current_role(x_role: str = Header(default="viewer", alias="X-Role")) -> str:
    role = x_role.strip().lower()
    if role not in _SUPPORTED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Invalid role. Supported roles: viewer, editor, "
                "data-engineer, admin."
            ),
        )
    return role


def require_role(allowed_roles: set[str]) -> Callable[[str], str]:
    def _check(current_role: str = Depends(get_current_role)) -> str:
        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this dataset operation.",
            )
        return current_role

    return _check


require_dataset_upload_role = require_role({"editor", "data-engineer", "admin"})
require_dataset_delete_role = require_role({"data-engineer", "admin"})
