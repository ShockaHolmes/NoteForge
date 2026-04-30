from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from notes_app.api.dependencies import (
    get_dataset_service,
    require_dataset_delete_role,
    require_dataset_upload_role,
)
from notes_app.api.schemas.error_schemas import ErrorResponse
from notes_app.api.schemas.dataset_schemas import (
    DatasetProfileResponse,
    DatasetMetadataSummaryResponse,
    DatasetPreviewResponse,
    DatasetResponse,
    DatasetSchemaField,
    DatasetUploadResponse,
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


def _to_upload_response(dataset: Dataset) -> DatasetUploadResponse:
    return DatasetUploadResponse(
        id=dataset.id,
        metadata=DatasetMetadataSummaryResponse(
            title=dataset.title,
            format=dataset.format or None,
            path=dataset.path or None,
            row_count=dataset.row_count or None,
            column_count=dataset.column_count or None,
            tags=list(dataset.tags),
            created=dataset.created,
            modified=dataset.modified,
        ),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[DatasetResponse])
def list_datasets(
    service: DatasetService = Depends(get_dataset_service),
) -> list[DatasetResponse]:
    return [_to_response(d) for d in service.list_datasets()]


@router.post("", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED,
             responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def create_dataset(
    title: str = Form(..., min_length=1, max_length=200),
    author: str = Form(default=""),
    tags: str = Form(default="", description="Comma-separated list of tags"),
    file: UploadFile | None = File(default=None),
    _role: str = Depends(require_dataset_upload_role),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetUploadResponse:
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
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _to_upload_response(dataset)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse,
            responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def preview_dataset(
    dataset_id: str,
    limit: int = Query(5, ge=1, le=1000, description="Number of rows/records to preview"),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetPreviewResponse:
    try:
        result = service.preview_dataset(dataset_id, limit)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    dataset, preview = result
    return DatasetPreviewResponse(
        id=dataset.id,
        format=dataset.format or None,
        limit=limit,
        headers=preview.get("headers") if isinstance(preview.get("headers"), list) else None,
        rows=preview.get("rows") if isinstance(preview.get("rows"), list) else None,
        records=preview.get("records") if isinstance(preview.get("records"), list) else None,
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse,
            responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def profile_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetProfileResponse:
    try:
        result = service.profile_dataset(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    dataset, profile = result
    source = str(profile.get("source") or "computed")
    row_count = profile.get("rowCount")
    columns = profile.get("columns") if isinstance(profile.get("columns"), list) else []
    return DatasetProfileResponse(
        id=dataset.id,
        format=dataset.format or None,
        source=source,
        row_count=int(row_count) if isinstance(row_count, int) else 0,
        columns=columns,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse,
            responses={404: {"model": ErrorResponse}})
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


@router.patch("/{dataset_id}", response_model=DatasetResponse,
              responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
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


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def delete_dataset(
    dataset_id: str,
    _role: str = Depends(require_dataset_delete_role),
    service: DatasetService = Depends(get_dataset_service),
) -> None:
    result = service.delete_dataset(dataset_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
