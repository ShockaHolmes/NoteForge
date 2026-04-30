# Future Proof Notes - Python

Python implementation of the `future-proof` notes manager, covering Phase 1 (CLI) and Phase 2 (REST API + datasets + backup).

---

## Quick Start

### Prerequisites

```bash
cd python
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt   # fastapi, uvicorn, pyyaml, pytest, etc.
```

### Run the CLI

```bash
cd python
PYTHONPATH=src python -m notes_app.cli.main help
```

### Start the API server

```bash
cd python
PYTHONPATH=src uvicorn notes_app.api.app:app --reload
# Interactive docs: http://localhost:8000/docs
```

---

## Storage Layout

All data lives under `~/.notes/` by default.

```
~/.notes/
├── notes/
│   ├── 2026-04-30-my-first-note.md          # note markdown + YAML frontmatter
│   └── 2026-04-30-meeting-summary.md
└── datasets/
    ├── sales-2026-q1.csv                    # raw data file — never rewritten
    ├── sales-2026-q1.dataset.yml            # sidecar metadata (id, title, schema …)
    ├── customer-events.json
    └── customer-events.dataset.yml
```

Override the default paths with environment variables:

```bash
export NOTES_HOME=/data/my-notes
export DATASETS_HOME=/data/my-datasets
```

### Note file format

Each note is a Markdown file with a YAML frontmatter block:

```markdown
---
id: 2026-04-30-my-first-note
title: My First Note
created: 2026-04-30T10:00:00
modified: 2026-04-30T10:05:00
tags: [work, ideas]
---

Body text goes here.
```

### Dataset sidecar format

Each uploaded dataset gets a companion `.dataset.yml` file:

```yaml
id: sales-2026-q1
title: Sales Q1 2026
author: alice
created: 2026-04-30T10:00:00
modified: 2026-04-30T10:00:00
tags: [sales, quarterly]
format: csv
path: sales-2026-q1.csv
rowCount: 500
columnCount: 4
schema:
  - name: date
    type: string
  - name: region
    type: string
  - name: revenue
    type: float
  - name: units
    type: integer
```

See [docs/dataset-metadata-schema.example.yml](../docs/dataset-metadata-schema.example.yml) for the full spec.

---

## Phase 1 — CLI

### All commands

```bash
PYTHONPATH=src python -m notes_app.cli.main <command> [args]
```

| Command | Description |
|---|---|
| `help` | Show help text |
| `create <title> <content>` | Create a new note |
| `list` | List all notes |
| `read <id>` | Display a note by id or filename |
| `search <query>` | Search title, tags, and body |
| `update <id> [--title "…"] [--tags "t1,t2"] [--content "…"]` | Update a note |
| `delete <id>` | Delete a note |
| `backup [output-dir]` | Zip backup of notes + datasets |
| `restore <backup.zip>` | Restore from a zip backup |

### Examples

```bash
# Create a note
PYTHONPATH=src python -m notes_app.cli.main create "Meeting notes" "Discussed Q2 roadmap"

# List all notes
PYTHONPATH=src python -m notes_app.cli.main list

# Read a note (use the id shown by list)
PYTHONPATH=src python -m notes_app.cli.main read 2026-04-30-meeting-notes

# Search across title, tags, and body
PYTHONPATH=src python -m notes_app.cli.main search roadmap

# Update title and tags
PYTHONPATH=src python -m notes_app.cli.main update 2026-04-30-meeting-notes \
  --title "Q2 Meeting Notes" --tags "work,q2"

# Update content only
PYTHONPATH=src python -m notes_app.cli.main update 2026-04-30-meeting-notes \
  --content "Updated content here"

# Delete a note
PYTHONPATH=src python -m notes_app.cli.main delete 2026-04-30-meeting-notes

# Backup to the current directory
PYTHONPATH=src python -m notes_app.cli.main backup

# Backup to a specific folder
PYTHONPATH=src python -m notes_app.cli.main backup /tmp/backups

# Restore from a backup zip
PYTHONPATH=src python -m notes_app.cli.main restore /tmp/backups/notes-backup-2026-04-30T120000.zip
```

---

## Phase 2 — REST API

Start the server before making any requests:

```bash
cd python
PYTHONPATH=src uvicorn notes_app.api.app:app --reload
```

Both `/api/` and `/api/v1/` prefixes are supported for every endpoint.

### Role-based access

Pass an `X-Role` header on requests that require elevated privileges.

| Role | Can do |
|---|---|
| `viewer` (default) | Read notes, datasets, search |
| `editor` | Everything above + upload datasets |
| `data-engineer` | Everything above + delete datasets |
| `admin` | Full access |

---

### Notes API

#### List all notes

```bash
curl http://localhost:8000/api/notes
```

```json
[
  {
    "id": "2026-04-30-meeting-notes",
    "title": "Meeting notes",
    "created": "2026-04-30T10:00:00",
    "modified": "2026-04-30T10:05:00",
    "tags": ["work"],
    "content": "Discussed Q2 roadmap"
  }
]
```

#### Create a note

```bash
curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "New idea", "content": "Build something great", "tags": ["ideas"]}'
```

Returns `201 Created` with the new note object.

#### Get a note by id

```bash
curl http://localhost:8000/api/notes/2026-04-30-new-idea
```

Returns `404` with `{"detail": "Note '...' not found."}` if the id does not exist.

#### Update a note (partial)

```bash
curl -X PATCH http://localhost:8000/api/notes/2026-04-30-new-idea \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated idea", "tags": ["ideas", "priority"]}'
```

Only the fields provided are changed. Omitted fields are left as-is.

#### Replace a note (full)

```bash
curl -X PUT http://localhost:8000/api/notes/2026-04-30-new-idea \
  -H "Content-Type: application/json" \
  -d '{"title": "Replaced", "content": "Completely new content", "tags": []}'
```

#### Delete a note

```bash
curl -X DELETE http://localhost:8000/api/notes/2026-04-30-new-idea
```

Returns `204 No Content` on success.

#### Search notes

```bash
curl "http://localhost:8000/api/notes/search?q=roadmap"
```

```json
[
  {
    "id": "2026-04-30-meeting-notes",
    "title": "Meeting notes",
    "assetType": "note",
    "context": "body: ...Discussed Q2 roadmap..."
  }
]
```

Returns `400` if `q` is missing or empty.

---

### Datasets API

#### List all datasets

```bash
curl http://localhost:8000/api/datasets
```

#### Upload a CSV or JSON dataset (requires `editor` role or higher)

```bash
curl -X POST http://localhost:8000/api/datasets \
  -H "X-Role: editor" \
  -F "title=Sales Q1 2026" \
  -F "author=alice" \
  -F "tags=sales,quarterly" \
  -F "file=@/path/to/sales-q1.csv"
```

```json
{
  "id": "sales-2026-q1",
  "metadata": {
    "title": "Sales Q1 2026",
    "format": "csv",
    "path": "sales-2026-q1.csv",
    "rowCount": 500,
    "columnCount": 4,
    "tags": ["sales", "quarterly"],
    "created": "2026-04-30T10:00:00",
    "modified": "2026-04-30T10:00:00"
  }
}
```

- Returns `400` for unsupported file types or malformed content.
- Returns `403` if the role is insufficient.
- The `file` field is optional — omit it to register metadata-only (sidecar without a raw file).

#### Get dataset metadata

```bash
curl http://localhost:8000/api/datasets/sales-2026-q1
```

Returns the full dataset record including `schema` (column names and types).

#### Update dataset metadata (partial)

```bash
curl -X PATCH http://localhost:8000/api/datasets/sales-2026-q1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Sales Q1 2026 (revised)", "tags": ["sales", "revised"]}'
```

#### Preview first N rows

```bash
curl "http://localhost:8000/api/datasets/sales-2026-q1/preview?limit=10"
```

```json
{
  "id": "sales-2026-q1",
  "format": "csv",
  "rows": [
    {"date": "2026-01-01", "region": "North", "revenue": 12000.0, "units": 300}
  ],
  "totalRows": 1
}
```

#### Column profile

```bash
curl http://localhost:8000/api/datasets/sales-2026-q1/profile
```

```json
{
  "id": "sales-2026-q1",
  "columns": [
    {"name": "revenue", "type": "float", "min": 500.0, "max": 95000.0, "nullCount": 0}
  ]
}
```

#### Delete a dataset (requires `data-engineer` role or higher)

```bash
curl -X DELETE http://localhost:8000/api/datasets/sales-2026-q1 \
  -H "X-Role: data-engineer"
```

Returns `204 No Content`. Returns `403` if the role is insufficient.

---

### Unified Search API

Search across both notes and datasets in one call:

```bash
curl "http://localhost:8000/api/search?q=quarterly"
```

```json
[
  {
    "id": "sales-2026-q1",
    "title": "Sales Q1 2026",
    "assetType": "dataset",
    "context": "tag: quarterly"
  }
]
```

Returns `400` if `q` is missing or empty.

---

### Error response shape

All `4xx` errors return a consistent JSON body:

```json
{"detail": "Human-readable description of the problem."}
```

| Status | Meaning |
|---|---|
| `400` | Bad request — missing field, invalid value, bad file format |
| `403` | Forbidden — role insufficient for this operation |
| `404` | Not found — note or dataset id does not exist |

---

## Running Tests

```bash
cd python
PYTHONPATH=src python -m pytest              # all tests
PYTHONPATH=src python -m pytest --tb=short   # compact failure output
PYTHONPATH=src python -m pytest tests/test_api_notes.py -v   # single file
```

---

## Starter Code Reference

The `notes0.py`, `notes1.py`, and `noteshell.py` files are the original starter scripts. They demonstrate the basic CLI skeleton and YAML frontmatter concept but are superseded by the `src/notes_app/` package.

```bash
# Smoke-test the original starter script
python3 notes0.py help
python3 smoke_test_notes0.py
```

## Project Structure

```
python/
├── src/
│   └── notes_app/
│       ├── api/          # FastAPI app, routers, schemas, dependencies
│       ├── cli/          # CLI dispatcher and per-command handlers
│       ├── config/       # Storage path resolution (NOTES_HOME / DATASETS_HOME)
│       ├── models/       # Frozen dataclasses: Note, Dataset, Asset
│       ├── repositories/ # Filesystem adapters (FileNoteRepository, etc.)
│       └── services/     # Business logic: NoteService, DatasetService, BackupService
└── tests/                # pytest test suite (173 tests)
- Include datasets in backup/restore manifests.
- Add role checks for dataset operations (`viewer`, `editor`, `data-engineer`, `admin`).
