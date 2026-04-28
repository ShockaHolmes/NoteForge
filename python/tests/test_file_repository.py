from pathlib import Path

from notes_app.models.note import Note
from notes_app.repositories.file_note_repository import FileNoteRepository


def test_file_repository_writes_and_reads_frontmatter(tmp_path: Path) -> None:
    repository = FileNoteRepository(tmp_path)
    note = Note.create(
        note_id="sample-note",
        title="Sample Note",
        content="This is note content.",
        tags=("school", "python"),
    )

    repository.save(note)
    saved_path = tmp_path / "sample-note.md"
    text = saved_path.read_text(encoding="utf-8")

    assert text.startswith("---\n")
    assert "title: Sample Note" in text
    assert "tags: [school, python]" in text

    notes = list(repository.list_notes())
    assert len(notes) == 1
    assert notes[0].title == "Sample Note"
    assert notes[0].content == "This is note content."
    assert notes[0].tags == ("school", "python")
