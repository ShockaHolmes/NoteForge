# API Framework Decision — FastAPI

## Decision

**FastAPI** is the chosen framework for the Phase 2 Python API.

## Why FastAPI

### 1. Fits the existing codebase style

The Phase 1 codebase uses Python type annotations throughout — frozen dataclasses, annotated function signatures, and `to_dict` / `from_dict` data conversion on domain models. FastAPI is built on Pydantic and reads those same type hints for automatic request validation and serialisation. The existing `NoteService` plugs directly into FastAPI's `Depends()` dependency injection pattern with no rewiring.

### 2. Automatic API documentation

FastAPI generates OpenAPI/Swagger UI at `/docs` and ReDoc at `/redoc` with zero extra configuration. This matters for the datasets API where the schema is rich (`schema`, `profile`, `source` blocks in the metadata) — having interactive docs helps the team validate endpoint contracts early.

### 3. Built-in input validation without extra libraries

Pydantic models validate request bodies, query parameters, and path parameters automatically, returning structured RFC 7807-style error responses. Flask would require `marshmallow`, `wtforms`, or manual validation to achieve the same result.

### 4. Async-ready for dataset operations

Dataset file ingest, profiling, and index building are natural candidates for `async def` handlers. FastAPI supports sync and async route handlers side by side, so Phase 2 can start sync and migrate hot paths to async incrementally.

### 5. Compared to Flask

| Concern | Flask | FastAPI |
|---|---|---|
| Request validation | Manual or plugin | Built-in via Pydantic |
| API docs | Plugin (flask-restx etc.) | Built-in OpenAPI |
| Type safety | Not enforced | Enforced at runtime + static analysis |
| Async support | Bolted on via Quart | First-class |
| Dependency injection | Manual globals or app context | `Depends()` pattern |
| Test client | Werkzeug test client | HTTPX `TestClient` (async-compatible) |

Flask is a good choice for simple web apps; FastAPI is the better fit here because the project already speaks Pydantic's language.

## API Scope — Phase 2

### Notes resource (`/api/v1/notes`)
- `GET    /api/v1/notes` — list all notes
- `POST   /api/v1/notes` — create a note
- `GET    /api/v1/notes/{id}` — read a note
- `PATCH  /api/v1/notes/{id}` — update title, tags, or content
- `DELETE /api/v1/notes/{id}` — delete a note
- `GET    /api/v1/notes/search?q=` — search title, tags, and body

### Datasets resource (`/api/v1/datasets`)
- `GET    /api/v1/datasets` — list dataset metadata records
- `POST   /api/v1/datasets` — register a dataset sidecar
- `GET    /api/v1/datasets/{id}` — read a dataset metadata record
- `PATCH  /api/v1/datasets/{id}` — update a dataset record
- `DELETE /api/v1/datasets/{id}` — remove a dataset record

## Module layout

```
python/src/notes_app/
└── api/
    ├── __init__.py
    ├── app.py             # FastAPI app factory
    ├── dependencies.py    # Shared Depends() providers
    ├── routers/
    │   ├── __init__.py
    │   ├── notes.py       # Notes CRUD + search router
    │   └── datasets.py    # Datasets router (Phase 2)
    └── schemas/
        ├── __init__.py
        ├── note_schemas.py     # Pydantic request/response models for notes
        └── dataset_schemas.py  # Pydantic request/response models for datasets
```
