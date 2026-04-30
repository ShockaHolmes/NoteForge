from fastapi import APIRouter, Depends, HTTPException, Query, status

from notes_app.api.dependencies import get_note_service
from notes_app.api.schemas.error_schemas import ErrorResponse
from notes_app.api.schemas.note_schemas import (
    NoteCreateRequest,
    NoteResponse,
    NoteSearchResponse,
    NoteUpdateRequest,
)
from notes_app.cli.commands.search_command import _matching_context
from notes_app.services.note_service import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])


def _to_response(note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        title=note.title,
        created=note.created,
        modified=note.modified,
        tags=list(note.tags),
        content=note.content,
    )


@router.get("", response_model=list[NoteResponse])
def list_notes(service: NoteService = Depends(get_note_service)) -> list[NoteResponse]:
    return [_to_response(n) for n in service.list_notes()]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED,
             responses={400: {"model": ErrorResponse}})
def create_note(
    body: NoteCreateRequest,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    note = service.create_note(
        title=body.title,
        content=body.content,
        tags=tuple(body.tags),
    )
    return _to_response(note)


@router.get("/search", response_model=list[NoteSearchResponse])
def search_notes(
    q: str = Query(..., min_length=1, description="Search term"),
    service: NoteService = Depends(get_note_service),
) -> list[NoteSearchResponse]:
    results = []
    for note in service.list_notes():
        context = _matching_context(note, q)
        if context is not None:
            results.append(NoteSearchResponse(id=note.id, title=note.title, context=context))
    return results


@router.get("/{note_id}", response_model=NoteResponse,
            responses={404: {"model": ErrorResponse}})
def get_note(
    note_id: str,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    note = service.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found.")
    return _to_response(note)


@router.patch("/{note_id}", response_model=NoteResponse,
              responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_note(
    note_id: str,
    body: NoteUpdateRequest,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    tags = tuple(body.tags) if body.tags is not None else None
    note = service.update_note(
        note_id=note_id,
        title=body.title,
        tags=tags,
        content=body.content,
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found.")
    return _to_response(note)


@router.put("/{note_id}", response_model=NoteResponse,
            responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def replace_note(
    note_id: str,
    body: NoteCreateRequest,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    note = service.update_note(
        note_id=note_id,
        title=body.title,
        tags=tuple(body.tags),
        content=body.content,
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found.")
    return _to_response(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses={404: {"model": ErrorResponse}})
def delete_note(
    note_id: str,
    service: NoteService = Depends(get_note_service),
) -> None:
    deleted = service.delete_note(note_id)
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found.")
