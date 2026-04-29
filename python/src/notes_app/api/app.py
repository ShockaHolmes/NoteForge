from fastapi import FastAPI

from notes_app.api.routers import datasets, notes


def create_app() -> FastAPI:
    app = FastAPI(
        title="FutureProof Notes API",
        description="REST API for notes and dataset metadata management.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(notes.router, prefix="/api/v1")
    app.include_router(datasets.router, prefix="/api/v1")
    app.include_router(datasets.router, prefix="/api")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
