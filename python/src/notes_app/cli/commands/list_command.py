from notes_app.services.note_service import NoteService


def run_list(service: NoteService) -> str:
    notes = service.list_notes()
    if not notes:
        return "No notes found."

    lines: list[str] = ["Notes:", "=" * 60]
    for note in notes:
        lines.append("")
        lines.append(f"{note.slug}.md")
        lines.append(f"  Title: {note.title}")
        lines.append(f"  Created: {note.created.isoformat()}")
        if note.tags:
            lines.append(f"  Tags: {', '.join(note.tags)}")

    lines.append("")
    lines.append(f"{len(notes)} note(s) found.")
    return "\n".join(lines)
