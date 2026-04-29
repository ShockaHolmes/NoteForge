from collections.abc import Callable

from notes_app.services.note_service import NoteService


def run_delete(
    service: NoteService,
    note_id: str,
    confirm_fn: Callable[[str], str] = input,
) -> tuple[str, bool]:
    note = service.get_note(note_id)
    if note is None:
        slug = note_id.removesuffix(".md")
        return f"Error: Note '{slug}' not found.", False

    prompt = f"Delete note '{note.id}' ({note.title})? [y/N]: "
    answer = confirm_fn(prompt).strip().lower()
    if answer not in {"y", "yes"}:
        return "Delete cancelled.", True

    deleted = service.delete_note(note.id)
    if deleted is None:
        return f"Error: Note '{note.id}' not found.", False
    return f"Deleted note '{note.id}.md'", True