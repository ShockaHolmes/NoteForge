from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error body returned for 400, 403, and 404 responses."""

    detail: str
