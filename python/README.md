# Future Proof Notes - Python

Python implementation track for the `future-proof` notes manager.

## Phase 1 Focus

Implement core note management features:
- Create, read, update, delete (CRUD) text notes
- Store notes as markdown files in `~/.notes/notes/`
- Support basic metadata (title, created/modified timestamps, tags) in YAML frontmatter
- Implement a simple CLI for managing notes
- Implement a basic search function that searches note content and metadata

But to get started, you'll need to read the python files here. they are Starter classes, and you can run them to see how they work. They are not complete, but they will give you a good starting point for your implementation. You can also refer to the Java implementation for guidance on how to structure your code and implement the required features.

```bash
# Show help
python3 notes0.py help

# No command (shows error)
python3 notes0.py

# Unknown command (shows error)
python3 notes0.py create

# Or as an executable:
./python/notes0.py help

```

## Acceptance Checks (notes0)

Run these from this directory (`python/`):

```bash
# Help output
python3 notes0.py help

# Missing command error
python3 notes0.py

# Unknown command error
python3 notes0.py frobnicate
```

Expected behavior:
- `python3 notes0.py help` prints usage and available commands.
- `python3 notes0.py` exits with code `1` and prints a missing-command error.
- Unknown commands (for example `frobnicate`) exit with code `1` and print a clear error that includes supported commands.

### One-Command Smoke Test

You can validate all three checks automatically:

```bash
python3 smoke_test_notes0.py
```

Expected result:
- Exit code `0` with `PASS: notes0 acceptance smoke tests`.
- Exit code `1` with failing check details if any behavior regresses.

## Starter Code Decisions (Keep/Change/Replace)

The team should use this as baseline guidance while moving from starter code to full Phase 1 features:

- Keep:
	- CLI skeleton flow (`setup -> parse args -> dispatch -> finish`) in `notes0.py`.
	- Centralized help and exit handling in `notes0.py`.
	- YAML front matter parsing idea in `notes1.py` as a temporary parser.

- Change:
	- Command handling from simple `if/elif` branching to a command map/module-based command handlers.
	- Error messaging to be consistent, explicit, and testable across all commands.
	- Notes directory setup to support `init` behavior and configurable paths.

- Replace:
	- The minimal YAML parser in `notes1.py` with a robust YAML library-based parser.
	- One-file scripts with a package structure (`src/` style modules for CLI, services, and storage).
	- Ad-hoc print-based validation with unit-tested validation and typed data structures.

## Phase 1 Project Folder Structure

The Phase 1 starter structure now separates CLI flow from storage concerns:

```
python/
	src/
		notes_app/
			cli/
				commands/
			models/
			repositories/
			services/
	tests/
```

Short layout explanation:
- `cli/`: parses commands and prints output; it does not read/write files directly.
- `models/`: domain objects (for example, `Note`).
- `repositories/`: storage adapters and interfaces (filesystem lives here).
- `services/`: business logic/use cases that depend on repository interfaces.
- `tests/`: verifies service behavior independently from filesystem/CLI.

Shared `Note` model:
- lives in `src/notes_app/models/note.py`
- supports `id`, `title`, `created`, `modified`, `tags`, and `content`
- exposes `to_dict()` / `from_dict()` for shared application and API use
- exposes `to_metadata_dict()` / `from_metadata_dict()` for YAML frontmatter boundaries

Try the package-based CLI starter:

```bash
PYTHONPATH=src python3 -m notes_app.cli.main help
PYTHONPATH=src python3 -m notes_app.cli.main create "My Note" "hello from phase 1"
PYTHONPATH=src python3 -m notes_app.cli.main list
```

The package CLI now follows the same direction as `notes1.py` list behavior:
- notes are persisted as markdown files with YAML frontmatter metadata
- `list` prints filename, title, created timestamp, and tags

Run tests with pytest:

```bash
cd python
python3 -m pytest
```

## Phase 2 Focus

Add REST + web support for both:
- text notes
- dataset files (`.csv`, `.json`) for Data Engineer workflows

## Dataset Support (CSV/JSON)

Use filesystem-first storage with sidecar YAML metadata.

Example layout:

```
~/.notes/
	notes/
		2026-03-13-my-note.note
	datasets/
		sales-2026-q1.csv
		sales-2026-q1.dataset.yml
		customer-events.json
		customer-events.dataset.yml
```

Dataset sidecar fields (minimum):
- `id`, `title`, `author`, `created`, `modified`, `tags`
- `format` (`csv` or `json`)
- `path` (relative to `datasets/`)
- `rowCount`
- `schema` (list of `{name, type}`)

Canonical spec example:
- [docs/dataset-metadata-schema.example.yml](../docs/dataset-metadata-schema.example.yml)

## Phase 2 API Endpoints

```
GET    /api/notes
POST   /api/notes
GET    /api/notes/:id
PUT    /api/notes/:id
DELETE /api/notes/:id

GET    /api/datasets
POST   /api/datasets             # Upload CSV/JSON
GET    /api/datasets/:id
DELETE /api/datasets/:id
GET    /api/datasets/:id/preview # First N rows
GET    /api/datasets/:id/profile # Column stats and inferred types

GET    /api/search?q=query       # Search notes + datasets
```

## Python Technical Guidance

- Framework: Flask or FastAPI
- Validation/parsing:
	- `csv` (stdlib)
	- `json` (stdlib)
	- `PyYAML` for sidecar metadata
- Upload handling:
	- enforce allowed types (`.csv`, `.json`)
	- enforce max upload size
	- ensure UTF-8 decoding
- Profiling jobs:
	- run async profiling after upload (thread pool or task queue)
	- persist profile output back into sidecar metadata

## Integration Notes

- Keep a shared `Asset` model (`note` or `dataset`) behind service/repository interfaces.
- Store raw datasets unchanged; never rewrite uploaded source by default.
- Include datasets in backup/restore manifests.
- Add role checks for dataset operations (`viewer`, `editor`, `data-engineer`, `admin`).
