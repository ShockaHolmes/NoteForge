from pydantic import BaseModel, Field


class SearchResultResponse(BaseModel):
    asset_type: str = Field(alias="assetType")
    id: str
    title: str
    context: str

    model_config = {"populate_by_name": True}
