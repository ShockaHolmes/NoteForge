from fastapi import Depends

from notes_app.config.storage import ensure_notes_dir
from notes_app.repositories.file_note_repository import FileNoteRepository
from notes_app.services.note_service import NoteService
from notes_app.config.storage import ensure_datasets_dir
from notes_app.repositories.file_dataset_repository import FileDatasetRepository
from notes_app.services.dataset_service import DatasetService


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
