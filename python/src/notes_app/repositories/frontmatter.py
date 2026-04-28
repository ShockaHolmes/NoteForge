from datetime import datetime, timezone

from notes_app.models.note import Note


def render_frontmatter(note: Note) -> str:
    metadata = note.to_metadata_dict()
    tags_str = ", ".join(str(tag) for tag in metadata["tags"])
    return (
        "---\n"
        f"id: {metadata['id']}\n"
        f"title: {metadata['title']}\n"
        f"created: {metadata['created']}\n"
        f"modified: {metadata['modified']}\n"
        f"tags: [{tags_str}]\n"
        "---\n\n"
    )


def parse_note_text(slug: str, text: str) -> Note:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return Note.create(note_id=slug, title=slug, content=text)

    yaml_end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            yaml_end = i
            break

    if yaml_end == -1:
        return Note.create(note_id=slug, title=slug, content=text)

    metadata: dict[str, str] = {}
    for line in lines[1:yaml_end]:
        stripped = line.strip()
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            metadata[key.strip()] = value.strip()

    body = "\n".join(lines[yaml_end + 1 :]).lstrip("\n")

    metadata.setdefault("id", slug)
    metadata["tags"] = _parse_tags(metadata.get("tags", ""))

    return Note.from_metadata_dict(metadata, content=body)


def _parse_tags(value: str) -> tuple[str, ...]:
    trimmed = value.strip()
    if not trimmed:
        return ()
    if trimmed.startswith("[") and trimmed.endswith("]"):
        inner = trimmed[1:-1].strip()
        if not inner:
            return ()
        parts = [piece.strip() for piece in inner.split(",")]
        return tuple(part for part in parts if part)
    return (trimmed,)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _from_iso(value: str | None, fallback: datetime | None = None) -> datetime:
    if not value:
        return fallback if fallback is not None else datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
