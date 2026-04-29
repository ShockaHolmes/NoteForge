from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from notes_app.api.dependencies import get_dataset_service
from notes_app.api.schemas.dataset_schemas import (
    DatasetResponse,
    DatasetSchemaField,
    DatasetUpdateRequest,
)
from notes_app.models.dataset import Dataset
from notes_app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


# ---------------------------------------------------------------------------
# Response helper
# ---------------------------------------------------------------------------

def _to_response(dataset: Dataset) -> DatasetResponse:
    return DatasetResponse(
        id=dataset.id,
        title=dataset.title,
        author=dataset.author or None,
        created=dataset.created,
        modified=dataset.modified,
        tags=list(dataset.tags),
        status=dataset.status or None,
        priority=dataset.priority or None,
        format=dataset.format or None,
        encoding=dataset.encoding or None,
        path=dataset.path or None,
        size_bytes=dataset.size_bytes or None,
        row_count=dataset.row_count or None,
        column_count=dataset.column_count or None,
        schema_fields=[
            DatasetSchemaField(name=f.name, type=f.type, nullable=f.nullable)
            for f in dataset.schema_fields
        ],
        version=dataset.version,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[DatasetResponse])
def list_datasets(
    service: DatasetService = Depends(get_dataset_service),
) -> list[DatasetResponse]:
    return [_to_response(d) for d in service.list_datasets()]


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    title: str = Form(..., min_length=1, max_length=200),
    author: str = Form(default=""),
    tags: str = Form(default="", description="Comma-separated list of tags"),
    file: UploadFile | None = File(default=None),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetResponse:
    """Create a dataset (multipart/form-data). The ``file`` field is optional.
    Accepted file types: CSV, JSON."""
    tag_tuple = tuple(t.strip() for t in tags.split(",") if t.strip())
    file_bytes: bytes | None = None
    original_filename: str | None = None
    if file is not None:
        file_bytes = await file.read()
        original_filename = file.filename
    try:
        dataset = service.create_dataset(
            title=title,
            author=author,
            tags=tag_tuple,
            file_bytes=file_bytes,
            original_filename=original_filename,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _to_response(dataset)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetResponse:
    dataset = service.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
    return _to_response(dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: str,
    body: DatasetUpdateRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetResponse:
    tags = tuple(body.tags) if body.tags is not None else None
    dataset = service.update_dataset(
        dataset_id,
        title=body.title,
        tags=tags,
        status=body.status,
        priority=body.priority,
    )
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
    return _to_response(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
) -> None:
    result = service.delete_dataset(dataset_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
