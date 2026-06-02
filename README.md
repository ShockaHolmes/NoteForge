# future-proof

# Build a Personal Notes Manager

A multi-phase educational project for managing personal notes with structured metadata.

It is also the first time we consider the idea of **future-proof** software.

## Overview

Personal Notes Manager is a text-based note-taking system that stores notes as UTF-8 text files with YAML headers for metadata. 
This project serves as an educational tool for students to learn file manipulation, parsing, and progressively more advanced application architectures.

It's `future-proof` because of its reliance on text files kept in a special directory.

Developers often create their own tools, programs they maintain for their own use.
This project 

https://zcw.guru/kristofer/javapygitignore

## Future-Proof software

"Future-proof" software is code designed to remain useful, maintainable, and adaptable as technology evolves and requirements change over time. Think of it like building a house with a strong foundation that can support renovations and additions years later.

**Why future-proofing matters:**
When you write software, you're not just solving today's problem - you're creating something that will likely need to change. User needs evolve, new technologies emerge, and business requirements shift. Future-proof code makes these inevitable changes easier and less expensive.

**Key principles for future-proof software:**

**Modularity and separation of concerns** - Break your code into distinct, focused pieces that do one thing well. If you need to change how data is stored, you shouldn't have to rewrite your user interface code too. If you store your notes in text files now, but a database in the next version, how do you make sure you can move amongst different storage tech?

**Use established standards and conventions** - Following widely-adopted patterns means other developers can understand your code, and it's more likely to work well with future tools and libraries. And text files, based on _UNICODE_, is one of the most well-respected storage modalities. (So is _Sqlite3_, see [Library of Congress; Recommended Formats Statement](https://www.loc.gov/preservation/resources/rfs/data.html))

**Avoid hard-coding values** - Instead of writing `if (users.length > 100)`, use a configurable constant like `if (users.length > MAX_USERS)`. This makes it easy to adjust limits without hunting through code. These items can be kept together, so that they can be reviewed and changed as needed in Future YEARS.

**Choose stable, well-supported technologies** - While it's tempting to use the newest framework, _mature technologies_ with strong communities tend to have better long-term support.

**Write clear documentation and tests** - Future you (or other developers) will thank you when they need to modify code written months or years ago. So, **unit tests** and _test-driven development_ is a critical part of this project. Test early and often. And make sure your _Future You_ knows how to run the test and read the comments and PLAN and SPEC documents.

The goal isn't to predict the future perfectly, but to write code that bends rather than breaks when change inevitably comes. It's about making smart trade-offs between solving immediate needs and maintaining flexibility for tomorrow's challenges.

## Project Phases

This project is designed to be implemented in three distinct phases:

### Phase 1: Command Line Interface (CLI)
- all notes kept in a "dot" folder in HOME directory
- Basic note creation, reading, updating, and deletion via command line
- YAML header parsing and manipulation
- Note searching and filtering capabilities
- Simple formatting options
- Unit tests for many of the common operations

### Phase 2: REST Server with JavaScript Frontend
- Web-based access to notes
- Web-based access to datasets (CSV/JSON) for Data Engineer workflows
- Mobile-responsive design
- API documentation for potential extensions
- backup all note to an S3 bucket kept by user

### Phase 3: Graphical User Interface (GUI)
- Web (vanilla JS) application with intuitive UI
- Rich text editing features
- Visual organization of notes (folders/tags)
- Enhanced search functionality with highlighting
- Export options (PDF, HTML, etc.)

## File Structure

Notes are stored as plain (UTF-8) text files with a `.note` extension (or any extension you prefer). 
All the files are kept in a "hidden" folder in your HOME directory.
Each note follows this structure:

```
---
title: My Example Note
author: Zip Coder
created: 2025-05-20T10:30:00Z
modified: 2025-05-20T10:45:00Z
tags: [example, documentation]
---

This is the content of my note.
It can contain multiple paragraphs and basic formatting.

You can include lists:
- Item 1
- Item 2
- Item 3

And other simple markdown markup as needed.
```

### Dataset Files (Phase 2)

In Phase 2, a Data Engineer can also store datasets as plain files, using `.csv` and `.json`.
To keep the design future-proof, each dataset file has a sidecar YAML metadata file.

Example layout in your hidden HOME notes directory:

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

Example dataset sidecar metadata (`sales-2026-q1.dataset.yml`):

```yaml
id: ds_01jq9z9em8g2
title: Sales Q1 2026
author: Zip Coder
created: 2026-03-13T10:30:00Z
modified: 2026-03-13T10:45:00Z
tags: [sales, finance, quarterly]
format: csv
path: sales-2026-q1.csv
rowCount: 15230
schema:
  - name: order_id
    type: string
  - name: amount
    type: number
  - name: order_date
    type: datetime
```

## YAML Header Specification

The YAML header is delimited by triple dashes (`---`) and contains metadata about the note:

| Field | Description | Type | Required |
|-------|-------------|------|----------|
| title | The title of the note | String | Yes |
| created | Creation timestamp (ISO 8601) | DateTime | No |
| modified | Last modification timestamp (ISO 8601) | DateTime | No |
| tags | Categories or labels for the note | Array of Strings | No |
| author | Creator of the note | String | Yes |
| status | Completion or review status | String | No |
| priority | Importance level | Integer (1-5) | No |

Additional custom fields can be added as needed.

There a few sample note files in [test-notes/](./test-notes)

## Phase 1: CLI Implementation

### Running the CLI

All CLI commands are run from the `python/` directory using the package-based entry point.
The notes directory (`~/.notes/notes/`) is created automatically on first run.

```bash
# Navigate to the Python implementation directory
cd python

# Display help
PYTHONPATH=src python3 -m notes_app.cli.main help

# Create a new note
PYTHONPATH=src python3 -m notes_app.cli.main create "My First Note" "This is the note content."

# List all notes
PYTHONPATH=src python3 -m notes_app.cli.main list

# Read a specific note (replace <note-id> with the ID shown in the list output)
PYTHONPATH=src python3 -m notes_app.cli.main read <note-id>

# Update a note's title, tags, or content
PYTHONPATH=src python3 -m notes_app.cli.main update <note-id> --title "Updated Title"
PYTHONPATH=src python3 -m notes_app.cli.main update <note-id> --tags "work,important"
PYTHONPATH=src python3 -m notes_app.cli.main update <note-id> --content "Revised content here."

# Delete a note
PYTHONPATH=src python3 -m notes_app.cli.main delete <note-id>

# Search notes by keyword (searches title, tags, and body)
PYTHONPATH=src python3 -m notes_app.cli.main search "keyword"
```

**PROTIP:** Seed your notes directory with the sample notes to have something to work with right away:

```bash
mkdir -p ~/.notes/notes
cp test-notes/*.md ~/.notes/notes/
```

### Command Reference

These commands can all be run from "anywhere" in your file system, and they are manipulating
notes kept in your hidden HOME directory.

Any "notes" command, when run, checks to see if there exists a hidden notes directory in your HOME,
and if not, runs the equivalent of a "notes init" command, creating the hidden directory.

```
notes --help                     # Display help information
notes create                     # Create a new note (opens in default editor)
notes list                       # List all notes
notes list --tag "coursework"    # List notes with specific tag
notes read <note-id>             # Display a specific note
notes edit <note-id>             # Edit a specific note
notes delete <note-id>           # Delete a specific note, asks confirmation before removal
notes search "query"             # Search notes for text (title, tags, content)
notes stats                      # Display statistics about your notes
```

### Technical Requirements

- Java 11+ or Python 3.11+
- YAML parser library
- Filesystem access & manipulation
- Text editor integration (nano?)
- Extra Credit: github integration for the notes storage
- Extra Credit: note encryption (and key management)

## Phase 2: REST Server Implementation

Maybe instead of Phase 2? Maybe this week, maybe in the future.

What is this stuff anyway? Well, Ask your friendly, globe-girdling AI.

### Starting the API Server

```bash
# Navigate to the Python implementation directory
cd python

# Install dependencies (FastAPI + Uvicorn)
pip install fastapi uvicorn pyyaml

# Start the API server (auto-reloads on code changes)
PYTHONPATH=src uvicorn notes_app.api.app:app --reload --port 8000
```

Once running, visit:
- **Interactive docs (Swagger UI):** http://localhost:8000/docs
- **Alternative docs (ReDoc):** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

### Managing Notes via the API

```bash
# List all notes
curl http://localhost:8000/api/notes

# Create a note
curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "My API Note", "content": "Hello from the API.", "tags": ["example", "api"]}'

# Read a specific note (replace <note-id> with the ID returned from create/list)
curl http://localhost:8000/api/notes/<note-id>

# Update a note (PATCH supports partial updates)
curl -X PATCH http://localhost:8000/api/notes/<note-id> \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "tags": ["updated"]}'

# Replace a note fully (PUT)
curl -X PUT http://localhost:8000/api/notes/<note-id> \
  -H "Content-Type: application/json" \
  -d '{"title": "Replaced Note", "content": "Completely new content.", "tags": []}'

# Delete a note
curl -X DELETE http://localhost:8000/api/notes/<note-id>

# Search notes by keyword
curl "http://localhost:8000/api/search?q=example"
```

### Uploading and Managing Datasets via the API

Datasets (CSV or JSON files) are uploaded via multipart form-data and stored in `~/.notes/datasets/`.
Each upload automatically creates a sidecar YAML metadata file alongside the data file.

```bash
# Upload a CSV dataset
curl -X POST http://localhost:8000/api/datasets \
  -F "title=Sales Q1 2026" \
  -F "author=Zip Coder" \
  -F "tags=sales,finance,quarterly" \
  -F "file=@sales-2026-q1.csv"

# Upload a JSON dataset
curl -X POST http://localhost:8000/api/datasets \
  -F "title=Customer Events" \
  -F "author=Zip Coder" \
  -F "tags=events,customers" \
  -F "file=@customer-events.json"

# List all datasets
curl http://localhost:8000/api/datasets

# Get dataset metadata
curl http://localhost:8000/api/datasets/<dataset-id>

# Preview the first N rows of a dataset
curl "http://localhost:8000/api/datasets/<dataset-id>/preview?limit=10"

# Profile a dataset (column stats, inferred types, null counts)
curl http://localhost:8000/api/datasets/<dataset-id>/profile

# Update dataset metadata (title, tags, status, priority)
curl -X PATCH http://localhost:8000/api/datasets/<dataset-id> \
  -H "Content-Type: application/json" \
  -d '{"title": "Sales Q1 2026 (Revised)", "tags": ["sales", "finance"]}'

# Delete a dataset and its sidecar metadata
curl -X DELETE http://localhost:8000/api/datasets/<dataset-id>
```

### API Endpoints

```
GET    /api/notes                    # List all notes
POST   /api/notes                    # Create a new note
GET    /api/notes/:id                # Retrieve a specific note
PUT    /api/notes/:id                # Replace a specific note
PATCH  /api/notes/:id                # Partially update a specific note
DELETE /api/notes/:id                # Delete a specific note
GET    /api/search?q=query           # Search notes and datasets

GET    /api/datasets                 # List datasets
POST   /api/datasets                 # Upload dataset (CSV/JSON)
GET    /api/datasets/:id             # Retrieve dataset metadata
PATCH  /api/datasets/:id             # Update dataset metadata
DELETE /api/datasets/:id             # Delete dataset and sidecar metadata
GET    /api/datasets/:id/preview     # Preview first N rows
GET    /api/datasets/:id/profile     # Column stats, inferred types, null counts
```

### Phase 2 Integration Notes

- Keep notes and datasets as separate asset types behind a shared service interface.
- Store raw dataset files unchanged; store metadata in sidecar YAML files.
- Add optional role-based permissions (viewer, editor, data-engineer, admin).
- Run dataset profiling asynchronously after upload so API remains responsive.
- Include datasets in backup/restore manifests for consistent S3 recovery.

### Technical Requirements

- Express.js/Flask/Django REST framework (python)
- Spring/Springboot
- **Frontend:** VanillaJS (first)
- Authentication system (don't want just anyone reading your notes)
- Database integration (optional, should still use file system)
- API documentation (Swagger/OpenAPI)
- CSV/JSON parsing and validation libraries
- File upload handling and size limits
- Background job capability for dataset profiling (threads/queue)

## Phase 3: GUI Implementation

Maybe this week, maybe next time we come back around to this project.

### Features

- Note browser panel (folder structure or tag-based)
- Rich text editor with markdown support
- Real-time preview
- Drag and drop organization
- Dark/light theme options
- Backup and restore functionality

### Technical Requirements

- HTML/CSS for UI (vanilla JS)
- Local storage management
- Cross-platform compatibility


## Learning Objectives

Students will gain experience with:

1. File I/O operations
2. Data parsing and validation
3. Command-line argument processing
4. User interface design principles
5. Client-server architecture
6. REST API development
7. Frontend-backend integration
8. Project planning and progressive enhancement

## Getting Started

### Prerequisites

- Python 3.11+ (for the Python implementation)
- Java 11+ (for the Java implementation)
- `pip` for installing Python dependencies
- Basic understanding of Java or Python

### Installation

```bash
# Clone the repository
# CHOOSE your Project's Name NOW.... _don't use future-proof_. **See Below for Suggested Names**
git clone https://github.com/yourusername/future-proof.git yournotesnamehere

# Navigate to the project directory
cd yournotesnamehere

# (Python) Install dependencies
pip install fastapi uvicorn pyyaml

# Seed your notes directory with the sample notes so you have something to work with
mkdir -p ~/.notes/notes
cp test-notes/*.md ~/.notes/notes/
```

## Lab notes

See https://github.com/ZipCodeCore/memo for example of a fork of this, and fork of `memo` with a Go impl by github.com/kristofer by way of example.

## Contributing

This project is designed for educational purposes. Students are encouraged to:

1. Fork the repository
2. Create a dev branch
3. Implement their assigned features
4. Submit a pull request for review

## License

[MIT license]

## Acknowledgments

- Every amazing personal notes project out there.
- Unix file system. Without it, we'd be sunk.
- Markdown: the way techies write.

## Possible Project Names

Possible Names for your version of this project (or make up your own!)
- NoteNexus
- MindScribe
- ThoughtVault
- StudyStream
- MemoPad Pro
- BrainWave Notes
- Scholarly Jotter
- InsightKeeper
- Knowledge Capsule
- NoteCraft
- MindMapper
- StudyPulse
- ThoughtHub
- NoteWorthy
- IdeaTracker
- StudySync
- RecallPro
- ClassCompass
- MindfulNotes
- LearnLogger

## But I wanna do a databse "NOW!!!"

**Why Build Your Note-Taking App with the Filesystem?**

Using the filesystem instead of a database or cloud service for your note-taking app isn't just a simpler starting point—it's a masterclass in fundamental programming concepts that every developer needs to understand.

**You're learning the foundation underneath everything**

Every piece of software ultimately interacts with files. Databases? They store data in files. Web servers? They serve files. Cloud applications? They manage files across distributed systems. By working directly with the filesystem, you're learning the bedrock skills that power everything else.

**Essential skills you'll develop:**

**File I/O operations** - You'll master reading from and writing to files, which is core to virtually every application. Whether you're processing configuration files, importing data, or generating reports, these skills transfer everywhere.

**Data serialization and parsing** - Converting your note objects into text (JSON, Markdown, XML) and back again teaches you how data moves between memory and storage. This same concept applies when sending data over networks or saving user preferences.

**Directory structure and organization** - Deciding how to organize notes (by date? by topic? in nested folders?) teaches you about data modeling and hierarchical thinking. These concepts directly apply to database design, URL routing in web apps, and organizing any complex system.

**Error handling and edge cases** - What happens when a file is corrupted? When the disk is full? When two processes try to write the same file? Filesystem programming forces you to think about real-world failure scenarios.

**Performance considerations** - You'll discover why reading one large file might be faster than many small ones, or why scanning hundreds of files can be slow. These insights apply to database queries, API calls, and system optimization everywhere.

**Practical examples from your note-taking app:**

**File naming and collision handling** - When a user creates two notes with the same title, how do you handle it? Do you append timestamps? Create numbered versions? This teaches you about unique identifiers and conflict resolution.

**Incremental loading** - If you have thousands of notes, you can't load them all into memory. You'll learn to read file lists, load metadata first, and fetch full content on demand—the same patterns used in web pagination and lazy loading.

**Search without databases** - Building search functionality by scanning files teaches you about indexing, text processing, and performance trade-offs. Later, when you use a database, you'll understand what it's doing behind the scenes.

**Backup and versioning** - How do you prevent data loss? How do you track changes? You might implement simple versioning by copying files or creating timestamps, learning the concepts behind version control systems.

**Cross-platform compatibility** - Different operating systems handle file paths differently. Learning to work with `/` vs `\` separators and absolute vs relative paths teaches you about portability and system-level programming.

**The learning progression:**

You'll start simple—just saving text to a file. Then you'll want better organization, so you'll create folders. Then you'll want metadata, so you'll learn JSON. Then you'll want search, so you'll read multiple files efficiently. Each step builds naturally on the last.

**Why this beats starting with a database:**

Databases hide complexity behind convenient APIs. While that's great for building applications quickly, it means you miss fundamental concepts about how data is actually stored and retrieved. When you eventually use databases (and you will), you'll understand the problems they're solving because you've faced those problems yourself.

**Real-world relevance:**

Many successful applications started as filesystem-based tools. Git manages millions of files efficiently. Static site generators like Jekyll process thousands of markdown files. Log analysis tools parse massive text files. Configuration management systems organize files across servers.

**Skills that transfer everywhere:**

The file handling patterns you learn will apply when you're processing CSV data, managing configuration files, building deployment scripts, or working with any system that stores and retrieves information. You're not just building a note-taking app—you're learning to think like a systems programmer.

Starting with the filesystem gives you a deep understanding of how computers actually work with data. It's messier and more complex than using a database, but that complexity teaches you invaluable problem-solving skills. Every challenge you solve—from handling concurrent access to organizing large amounts of data—prepares you for the real-world complexities you'll face as a professional developer.

## Ahem, about that Test-Driven Development thingie

**What is Test-Driven Development (TDD)?**

Test-Driven Development is a programming approach where you write tests *before* writing the actual code. It follows a simple cycle called "Red-Green-Refactor":

1. **Red**: Write a failing test that describes what you want your code to do
2. **Green**: Write the minimal code needed to make that test pass
3. **Refactor**: Clean up and improve the code while keeping tests passing

Think of it like writing a recipe backwards - you first describe what the finished dish should taste like, then figure out how to cook it.

**Why beginners should embrace TDD:**

**Clarifies your thinking** - Writing tests first forces you to think through exactly what your function should do before you get lost in implementation details. It's like sketching before painting.

**Catches bugs early** - Tests act as a safety net. When you change code later, your tests immediately tell you if you broke something that was previously working.

**Improves code design** - Code that's easy to test tends to be well-organized and modular. TDD naturally pushes you toward better architecture.

**Builds confidence** - You can refactor and improve your code fearlessly, knowing your tests will catch any mistakes.

**Serves as documentation** - Good tests show other developers (including future you) how your code is supposed to work.

**Need to Make Sure** - There are 3-4 test _For Every Method!!!_ Lots o'tests, many, many tests. So Many Tests!!

**How to do TDD:**

These test examples are in **JavaScript**, so use them only as conceptual examples.
You will write this app in either Java or Python, and use the standard filesystem (using text files as your data format) for your _storage infrastructure_.
Someday soon, you may get the chance (or motivation) to store the notes in a database of some kind, but for now, text files.

Let's say you're building a function to validate note titles. Here's the TDD process:

**Step 1 (Red)**: Write a failing test
```javascript
test('should reject empty note titles', () => {
  expect(validateNoteTitle('')).toBe(false);
});
```

**Step 2 (Green)**: Write minimal code to pass
```javascript
function validateNoteTitle(title) {
  return title !== '';
}
```

**Step 3 (Refactor)**: Improve while keeping tests green
```javascript
function validateNoteTitle(title) {
  return typeof title === 'string' && title.trim().length > 0;
}
```

Then repeat: add more tests for edge cases, implement features incrementally.
**Start small, with a tiny core of functionality.**
And then _build outwards_, add capabilities (and TESTs Tests tests) as you go!

**TDD in your note-taking CLI application:**

Here are specific areas where TDD would be valuable:

**Note creation and validation**
- Test that notes require titles
- Test that notes can have optional tags
- Test that duplicate titles are handled appropriately
- Test that special characters in titles are escaped properly

**Search functionality**
- Test searching by keywords finds correct notes
- Test case-insensitive search works
- Test searching with multiple tags
- Test handling of search terms with special characters

**File operations**
- Test that notes are saved to the correct file format
- Test that corrupted files are handled gracefully
- Test that backup creation works
- Test that notes can be exported to different formats

**Command parsing**
- Test that CLI commands are parsed correctly (`add`, `search`, `delete`)
- Test that invalid commands show helpful error messages
- Test that command flags work as expected (`--tag`, `--date`)

**Example TDD workflow for your CLI app:**

```javascript
// Test first
test('should create note with title and content', () => {
  const note = createNote('My First Note', 'This is the content');
  expect(note.title).toBe('My First Note');
  expect(note.content).toBe('This is the content');
  expect(note.createdAt).toBeInstanceOf(Date);
});

// Then implement
function createNote(title, content) {
  return {
    title: title,
    content: content,
    createdAt: new Date(),
    id: generateId()
  };
}
```

**Getting started:**
1. Choose a testing framework (`junit` for Java, `pytest` and/or `unittest` for Python, etc.)
2. Start with simple, pure functions (like validation, method correctness or formatting)
3. Write one test, make it pass, then add another
4. Don't try to test everything at once - build up gradually

TDD might feel slow initially, but it pays huge dividends as your application grows. 
You'll spend less time debugging mysterious bugs and more time confidently adding new features. 
For a personal project like this note-taking app, it also helps you think through the user experience before getting caught up in implementation details.

## Finally

_Why does choosing to use text files in a standard directory structure using Markdown as a note format, make the project "future proof"?_

Using text files in a standard directory structure with Markdown as a note format makes a project "future proof" for several compelling reasons:

**Universal Compatibility**
- Plain text files (.txt, .md) are readable by virtually any operating system and text editor, eliminating dependency on proprietary software
- UTF-8 encoding ensures support for multiple languages and special characters across all modern systems

**Longevity and Stability**
- Text files have remained a stable format for decades and will likely be readable for decades to come
- Unlike proprietary formats that can become obsolete when companies discontinue support

**Version Control Friendly**
- Text files integrate seamlessly with version control systems like Git
- Changes can be tracked line by line, enabling precise collaboration and history tracking

**Portable and Accessible**
- Files can be easily transferred between devices and platforms
- Low storage requirements compared to binary formats

**Human Readable**
- Content remains accessible without specialized software
- Even if the application becomes obsolete, notes remain directly readable

**Open Standards**
- Markdown is an open specification with wide industry support
- Not controlled by a single entity that could change or abandon the format

**Flexibility and Extensibility**
- Directory structures can be organized according to user preference
- Metadata in YAML headers can evolve over time without breaking backward compatibility
- New features can be added without rendering old files unusable

**Searchable**
- Plain text is easily searchable using standard system tools or simple scripts
- No need for specialized databases that might become obsolete

**Data Sovereignty**
- Users maintain complete control over their data
- No dependence on cloud services that may change terms or shut down

**Resilient Against Software Evolution**
- Even as the application evolves through its three phases (CLI → GUI → web), the underlying data format remains consistent
- Allows for migration to newer systems without data loss

This approach creates a foundation that can withstand technological change,
hence is `future-proof`, ensuring that notes remain accessible regardless of future software and hardware developments.
