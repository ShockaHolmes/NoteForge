from notes_app.services.note_service import NoteService


def run_create(service: NoteService, title: str, content: str) -> str:
    note = service.create_note(title=title, content=content)
    return f"Created note '{note.slug}.md'"
