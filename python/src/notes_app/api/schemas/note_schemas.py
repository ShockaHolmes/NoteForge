from datetime import datetime

from pydantic import BaseModel, Field


class NoteResponse(BaseModel):
    id: str
    title: str
    created: datetime
    modified: datetime
    tags: list[str] = Field(default_factory=list)
    content: str = ""


class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = ""
    tags: list[str] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    tags: list[str] | None = None


class NoteSearchResponse(BaseModel):
    id: str
    title: str
    context: str
