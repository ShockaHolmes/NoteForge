from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from notes_app.api.routers import datasets, notes, search


def create_app() -> FastAPI:
    app = FastAPI(
        title="FutureProof Notes API",
        description="REST API for notes and dataset metadata management.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return 400 with a clear message for all schema/field validation failures."""
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = " -> ".join(str(p) for p in first.get("loc", []) if p != "body")
            msg = first.get("msg", "Invalid request")
            detail = f"{loc}: {msg}" if loc else msg
        else:
            detail = "Bad request."
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": detail},
        )

    app.include_router(notes.router, prefix="/api/v1")
    app.include_router(datasets.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(notes.router, prefix="/api")
    app.include_router(datasets.router, prefix="/api")
    app.include_router(search.router, prefix="/api")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
