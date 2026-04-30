from datetime import datetime

from pydantic import BaseModel, Field


class NoteResponse(BaseModel):
    id: str
    title: str
    author: str = ""
    created: datetime
    modified: datetime
    tags: list[str] = Field(default_factory=list)
    status: str = "draft"
    priority: int = Field(default=3, ge=1, le=3)
    content: str = ""


class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    author: str = ""
    status: str = "draft"
    priority: int = Field(default=3, ge=1, le=5)


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    tags: list[str] | None = None
    author: str | None = None
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


class NoteSearchResponse(BaseModel):
    id: str
    title: str
    context: str
