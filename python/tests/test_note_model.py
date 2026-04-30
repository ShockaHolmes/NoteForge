from datetime import datetime, timezone

from notes_app.models.note import Note


ISO_CREATED = "2026-04-28T12:00:00Z"
ISO_MODIFIED = "2026-04-28T13:30:00Z"


def test_note_to_dict_includes_shared_fields() -> None:
    note = Note(
        id="note-123",
        title="Shared Note",
        created=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
        modified=datetime(2026, 4, 28, 13, 30, tzinfo=timezone.utc),
        tags=("python", "phase-1"),
        content="hello world",
    )

    data = note.to_dict()

    assert data == {
        "id": "note-123",
        "title": "Shared Note",
        "author": "",
        "created": ISO_CREATED,
        "modified": ISO_MODIFIED,
        "tags": ["python", "phase-1"],
        "status": "draft",
        "priority": 3,
        "content": "hello world",
    }


def test_note_from_dict_round_trips_shared_fields() -> None:
    note = Note.from_dict(
        {
            "id": "note-123",
            "title": "Shared Note",
            "created": ISO_CREATED,
            "modified": ISO_MODIFIED,
            "tags": ["python", "phase-1"],
            "status": "complete",
            "priority": 1,
            "content": "hello world",
        }
    )

    assert note.id == "note-123"
    assert note.title == "Shared Note"
    assert note.tags == ("python", "phase-1")
    assert note.status == "complete"
    assert note.priority == 1
    assert note.content == "hello world"
    assert note.created.isoformat() == "2026-04-28T12:00:00+00:00"
    assert note.modified.isoformat() == "2026-04-28T13:30:00+00:00"


def test_note_metadata_conversion_supports_yaml_boundary() -> None:
    metadata = {
        "id": "note-456",
        "title": "Frontmatter Note",
        "author": "",
        "created": ISO_CREATED,
        "modified": ISO_MODIFIED,
        "tags": ["yaml", "cli"],
        "status": "draft",
        "priority": 3,
    }

    note = Note.from_metadata_dict(metadata, content="body text")

    assert note.to_metadata_dict() == metadata
    assert note.content == "body text"
