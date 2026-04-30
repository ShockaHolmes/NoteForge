from notes_app.services.note_service import NoteService


def run_create(
    service: NoteService,
    title: str,
    content: str,
    tags: tuple[str, ...] = (),
    author: str = "",
    status: str = "draft",
    priority: int = 3,
) -> str:
    note = service.create_note(
        title=title,
        content=content,
        tags=tags,
        author=author,
        status=status,
        priority=priority,
    )
    return f"Created note '{note.slug}.md'"
