from notes_app.services.note_service import NoteService


def parse_update_flags(args: list[str]) -> tuple[dict[str, str], bool]:
    """Parse --title, --tags, --author, --status, --priority, --content flags.

    Returns (fields, ok). ok is False when an unknown flag is encountered.
    Recognised flags: --title, --tags, --author, --status, --priority, --content.
    """
    fields: dict[str, str] = {}
    known = {"--title", "--tags", "--author", "--status", "--priority", "--content"}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag in known:
            if i + 1 >= len(args):
                return {}, False
            fields[flag.lstrip("-")] = args[i + 1]
            i += 2
        else:
            return {}, False
    return fields, True


def run_update(service: NoteService, note_id: str, args: list[str]) -> tuple[str, bool]:
    """Return (output, ok). ok is False on error."""
    fields, ok = parse_update_flags(args)
    if not ok:
        return (
            "Error: update flags must be --title, --tags, --author, --status, --priority, or --content.\n"
            "Usage: update <id> [--title \"...\"] [--tags \"tag1,tag2\"] [--author \"...\"] "
            "[--status draft|active|complete] [--priority 1|2|3|4|5] [--content \"...\"]" ,
            False,
        )
    if not fields:
        return "Error: provide at least one update flag.", False

    tags: tuple[str, ...] | None = None
    if "tags" in fields:
        raw = fields["tags"].strip()
        tags = tuple(t.strip() for t in raw.split(",") if t.strip()) if raw else ()

    priority: int | None = None
    if "priority" in fields:
        raw_priority = fields["priority"].strip()
        if not raw_priority:
            return "Error: --priority must be 1 (High), 2 (Medium High), 3 (Normal), 4 (Medium Low), or 5 (Low).", False
        try:
            priority = int(raw_priority)
        except ValueError:
            return "Error: --priority must be 1 (High), 2 (Medium High), 3 (Normal), 4 (Medium Low), or 5 (Low).", False
        if priority not in {1, 2, 3, 4, 5}:
            return "Error: --priority must be 1 (High), 2 (Medium High), 3 (Normal), 4 (Medium Low), or 5 (Low).", False

    status = fields.get("status")
    if status is not None:
        normalized = status.strip().lower()
        if normalized not in {"draft", "active", "complete", "completed", "done", "incomplete"}:
            return "Error: --status must be 'draft', 'active', or 'complete'.", False

    note = service.update_note(
        note_id=note_id,
        title=fields.get("title"),
        tags=tags,
        author=fields.get("author"),
        status=status,
        priority=priority,
        content=fields.get("content"),
    )
    if note is None:
        slug = note_id.removesuffix(".md")
        return f"Error: Note '{slug}' not found.", False

    return f"Updated note '{note.slug}.md'", True
