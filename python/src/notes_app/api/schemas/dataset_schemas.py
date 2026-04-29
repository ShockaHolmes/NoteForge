from datetime import datetime

from pydantic import BaseModel, Field


class DatasetSchemaField(BaseModel):
    name: str
    type: str
    nullable: bool = True


class DatasetResponse(BaseModel):
    id: str
    title: str
    author: str | None = None
    created: datetime
    modified: datetime
    tags: list[str] = Field(default_factory=list)
    status: str | None = None
    priority: int | None = None
    format: str | None = None
    encoding: str | None = None
    path: str | None = None
    size_bytes: int | None = Field(default=None, alias="sizeBytes")
    row_count: int | None = Field(default=None, alias="rowCount")
    column_count: int | None = Field(default=None, alias="columnCount")
    schema_fields: list[DatasetSchemaField] = Field(default_factory=list, alias="schema")

    model_config = {"populate_by_name": True}
    version: int = 1


class DatasetMetadataSummaryResponse(BaseModel):
    title: str
    format: str | None = None
    path: str | None = None
    row_count: int | None = Field(default=None, alias="rowCount")
    column_count: int | None = Field(default=None, alias="columnCount")
    tags: list[str] = Field(default_factory=list)
    created: datetime
    modified: datetime

    model_config = {"populate_by_name": True}


class DatasetUploadResponse(BaseModel):
    id: str
    metadata: DatasetMetadataSummaryResponse


class DatasetCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    format: str | None = None
    path: str | None = None


class DatasetUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    tags: list[str] | None = None
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
