from notes_app.services.note_service import NoteService


def parse_update_flags(args: list[str]) -> tuple[dict[str, str], bool]:
    """Parse --title, --tags, --content flags from a flat arg list.

    Returns (fields, ok). ok is False when an unknown flag is encountered.
    Recognised flags: --title, --tags, --content.
    """
    fields: dict[str, str] = {}
    known = {"--title", "--tags", "--content"}
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
            "Error: update flags must be --title <v>, --tags <v>, or --content <v>.\n"
            "Usage: update <id> [--title \"...\"] [--tags \"tag1,tag2\"] [--content \"...\"]",
            False,
        )
    if not fields:
        return "Error: provide at least one of --title, --tags, or --content.", False

    tags: tuple[str, ...] | None = None
    if "tags" in fields:
        raw = fields["tags"].strip()
        tags = tuple(t.strip() for t in raw.split(",") if t.strip()) if raw else ()

    note = service.update_note(
        note_id=note_id,
        title=fields.get("title"),
        tags=tags,
        content=fields.get("content"),
    )
    if note is None:
        slug = note_id.removesuffix(".md")
        return f"Error: Note '{slug}' not found.", False

    return f"Updated note '{note.slug}.md'", True
