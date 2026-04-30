from notes_app.models.note import Note
from notes_app.services.note_service import NoteService


def get_search_matches(service: NoteService, query: str) -> tuple[str, list[tuple[Note, str]]]:
    """Return (output_string, matches). matches is empty when nothing is found."""
    term = query.strip()
    if not term:
        return "Error: search query cannot be empty.", []

    matches: list[tuple[Note, str]] = []
    for note in service.list_notes():
        context = _matching_context(note, term)
        if context is not None:
            matches.append((note, context))

    if not matches:
        return f"No notes matched '{term}'.", []

    lines: list[str] = [f"Search results for '{term}':", "=" * 60]
    for i, (note, context) in enumerate(matches, 1):
        lines.append("")
        lines.append(f"[{i}]  id: {note.id}")
        lines.append(f"     title: {note.title}")
        lines.append(f"     context: {context}")

    lines.append("")
    lines.append(f"{len(matches)} match(es) found.")
    return "\n".join(lines), matches


def run_search(service: NoteService, query: str) -> str:
    output, _ = get_search_matches(service, query)
    return output


def _matching_context(note: Note, term: str) -> str | None:
    lowered_term = term.lower()

    if lowered_term in note.title.lower():
        return f"title: {note.title}"

    if any(lowered_term in tag.lower() for tag in note.tags):
        tags = ", ".join(note.tags) if note.tags else "(none)"
        return f"tags: {tags}"

    if lowered_term in (note.author or "").lower():
        return f"author: {note.author}"

    if lowered_term in note.status.lower():
        return f"status: {note.status}"

    priority_terms = {
        1: ("1", "high", "priority 1"),
        2: ("2", "medium", "priority 2"),
        3: ("3", "normal", "priority 3", "low"),
    }
    if any(lowered_term == token for token in priority_terms.get(note.priority, ())):
        return f"priority: {note.priority}"

    body_context = _body_excerpt(note.content, term)
    if body_context is not None:
        return body_context

    return None


def _body_excerpt(body: str, term: str, radius: int = 30) -> str | None:
    lowered_body = body.lower()
    lowered_term = term.lower()
    index = lowered_body.find(lowered_term)
    if index == -1:
        return None

    start = max(0, index - radius)
    end = min(len(body), index + len(term) + radius)
    excerpt = body[start:end].replace("\n", " ").strip()
    if start > 0:
        excerpt = f"...{excerpt}"
    if end < len(body):
        excerpt = f"{excerpt}..."
    return excerpt