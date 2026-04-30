from notes_app.services.note_service import NoteService


def run_read(service: NoteService, note_id: str) -> tuple[str, bool]:
    """Return (output, ok). ok is False when the note is not found."""
    note = service.get_note(note_id)
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
