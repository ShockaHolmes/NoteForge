from notes_app.services.note_service import NoteService


def run_list(service: NoteService) -> str:
    notes = service.list_notes()
    if not notes:
        return "No notes found."

    lines: list[str] = ["Notes:", "=" * 60]
    for index, note in enumerate(notes, start=1):
        priority_label = {
            1: "high",
            2: "medium high",
            3: "normal",
            4: "medium low",
            5: "low",
        }.get(note.priority, "normal")
        lines.append("")
        lines.append(f"[{index}] {note.slug}.md")
        lines.append(f"  Title: {note.title}")
        lines.append(f"  Author: {note.author or '(unknown)'}")
        lines.append(f"  Created: {note.created.isoformat()}")
        lines.append(f"  Modified: {note.modified.isoformat()}")
        lines.append(f"  Status: {note.status}")
        lines.append(f"  Priority: {note.priority} ({priority_label})")
        if note.tags:
            lines.append(f"  Tags: {', '.join(note.tags)}")

    lines.append("")
    lines.append(f"{len(notes)} note(s) found.")
    return "\n".join(lines)
