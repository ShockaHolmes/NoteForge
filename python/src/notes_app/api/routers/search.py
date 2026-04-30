from fastapi import APIRouter, Depends, Query

from notes_app.api.dependencies import get_dataset_service, get_note_service
from notes_app.api.schemas.search_schemas import SearchResultResponse
from notes_app.models.asset import AssetType
from notes_app.services.dataset_service import DatasetService
from notes_app.services.note_service import NoteService

router = APIRouter(prefix="/search", tags=["search"])


def _note_search_context(note, term: str) -> str | None:
    lowered = term.lower()
    if lowered in note.title.lower():
        return f"title: {note.title}"

    for tag in note.tags:
        if lowered in tag.lower():
            return f"tag: {tag}"

    metadata_values = [
        note.id,
        note.author,
        note.status,
        str(note.priority),
        note.created.isoformat(),
        note.modified.isoformat(),
    ]
    for value in metadata_values:
        if lowered in str(value).lower():
            return f"metadata: {value}"

    body = note.content or ""
    idx = body.lower().find(lowered)
    if idx != -1:
        start = max(0, idx - 30)
        end = min(len(body), idx + len(term) + 30)
        excerpt = body[start:end].replace("\n", " ").strip()
        return f"body: ...{excerpt}..."

    return None


def _dataset_search_context(dataset, term: str) -> str | None:
    lowered = term.lower()
    if lowered in dataset.title.lower():
        return f"title: {dataset.title}"

    for tag in dataset.tags:
        if lowered in tag.lower():
            return f"tag: {tag}"

    for field in dataset.schema_fields:
        if lowered in field.name.lower() or lowered in field.type.lower():
            return f"schema: {field.name} ({field.type})"

    metadata_values = [
        dataset.id,
        dataset.author,
        dataset.created.isoformat(),
        dataset.modified.isoformat(),
        dataset.format,
        dataset.path,
        dataset.status,
        str(dataset.priority),
        str(dataset.row_count),
        str(dataset.column_count),
    ]
    for value in metadata_values:
        if lowered in str(value).lower():
            return f"metadata: {value}"

    return None


@router.get("", response_model=list[SearchResultResponse])
def search_assets(
    q: str = Query(..., min_length=1, description="Search query"),
    note_service: NoteService = Depends(get_note_service),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> list[SearchResultResponse]:
    results: list[SearchResultResponse] = []

    for note in note_service.list_notes():
        context = _note_search_context(note, q)
        if context is not None:
            results.append(
                SearchResultResponse(
                    asset_type=AssetType.NOTE.value,
                    id=note.id,
                    title=note.title,
                    context=context,
                )
            )

    for dataset in dataset_service.list_datasets():
        context = _dataset_search_context(dataset, q)
        if context is not None:
            results.append(
                SearchResultResponse(
                    asset_type=AssetType.DATASET.value,
                    id=dataset.id,
                    title=dataset.title,
                    context=context,
                )
            )

    return results
