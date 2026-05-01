from notes_app.services.note_service import NoteService


def _resolve_note_id(service: NoteService, note_id: str) -> str:
    """Resolve numeric list selections (1-based) to a note id."""
    if not note_id.isdigit():
        return note_id

    index = int(note_id)
    if index < 1:
        return note_id

    notes = service.list_notes()
    if index > len(notes):
        return note_id
    return notes[index - 1].id


def run_read(service: NoteService, note_id: str) -> tuple[str, bool]:
    """Return (output, ok). ok is False when the note is not found."""
    resolved_note_id = _resolve_note_id(service, note_id)
    note = service.get_note(resolved_note_id)
    if note is None:
        slug = note_id.removesuffix(".md")
        return f"Error: Note '{slug}' not found.", False

    tags_str = ", ".join(note.tags) if note.tags else "(none)"
    priority_label = {
        1: "high",
        2: "medium high",
        3: "normal",
        4: "medium low",
        5: "low",
    }.get(note.priority, "normal")
    lines = [
        f"id:       {note.id}",
        f"title:    {note.title}",
        f"author:   {note.author or '(unknown)'}",
        f"created:  {note.created.isoformat()}",
        f"modified: {note.modified.isoformat()}",
        f"status:   {note.status}",
        f"priority: {note.priority} ({priority_label})",
        f"tags:     {tags_str}",
        "-" * 60,
        note.content,
    ]
    return "\n".join(lines), True
