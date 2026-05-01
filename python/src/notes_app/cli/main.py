import sys
from pathlib import Path

# When run directly as a script (python main.py), add src/ to sys.path so
# that the notes_app package can be found without needing PYTHONPATH.
if __name__ == "__main__":
    _src = Path(__file__).resolve().parents[2]  # .../python/src
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from notes_app.cli.commands.backup_command import run_backup
from notes_app.cli.commands.create_command import run_create
from notes_app.cli.commands.delete_command import run_delete
from notes_app.cli.commands.help_command import render_help
from notes_app.cli.commands.list_command import run_list
from notes_app.cli.commands.read_command import run_read
from notes_app.cli.commands.restore_command import run_restore
from notes_app.cli.commands.search_command import run_search
from notes_app.cli.commands.update_command import run_update
from notes_app.cli.menu import run_menu
from notes_app.config.storage import ensure_datasets_dir, ensure_notes_dir
from notes_app.repositories.file_note_repository import FileNoteRepository
from notes_app.services.backup_service import BackupService
from notes_app.services.note_service import NoteService


def build_service() -> NoteService:
    notes_dir = ensure_notes_dir()
    repository = FileNoteRepository(notes_dir)
    return NoteService(repository)


def build_backup_service() -> BackupService:
    return BackupService(
        notes_dir=ensure_notes_dir(),
        datasets_dir=ensure_datasets_dir(),
    )


def _parse_kv_flags(raw_args: list[str], allowed: set[str]) -> tuple[dict[str, str], bool]:
    parsed: dict[str, str] = {}
    i = 0
    while i < len(raw_args):
        flag = raw_args[i]
        if flag not in allowed or i + 1 >= len(raw_args):
            return {}, False
        parsed[flag.lstrip("-")] = raw_args[i + 1]
        i += 2
    return parsed, True


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        return run_menu(build_service())

    command = args[0].lower()
    service = build_service()

    if command == "help":
        print(render_help("python -m notes_app.cli.main"))
        return 0

    if command == "menu":
        return run_menu(service)

    if command == "create":
        if len(args) < 3:
            print("Error: create requires <title> and <content>.", file=sys.stderr)
            print(
                "Usage: python -m notes_app.cli.main create \"Title\" \"Content\" "
                "[--tags \"tag1,tag2\"] [--author \"name\"] [--status draft|active|complete] "
                "[--priority 1|2|3|4|5]",
                file=sys.stderr,
            )
            return 1
        title = args[1]
        remainder = list(args[2:])
        split_index = len(remainder)
        for idx, token in enumerate(remainder):
            if token.startswith("--"):
                split_index = idx
                break

        content_tokens = remainder[:split_index]
        extra = remainder[split_index:]
        if not content_tokens:
            print("Error: create requires <content> before flags.", file=sys.stderr)
            return 1
        content = " ".join(content_tokens)

        parsed, ok = _parse_kv_flags(
            extra,
            allowed={"--tags", "--author", "--status", "--priority"},
        )
        if not ok:
            print(
                "Error: invalid create flags. Allowed: --tags, --author, --status, --priority.",
                file=sys.stderr,
            )
            return 1

        tags_raw = parsed.get("tags", "").strip()
        tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip()) if tags_raw else ()

        priority = 3
        if "priority" in parsed:
            try:
                priority = int(parsed["priority"])
            except ValueError:
                print("Error: --priority must be 1 (High), 2 (Medium High), 3 (Normal), 4 (Medium Low), or 5 (Low).", file=sys.stderr)
                return 1
            if priority not in {1, 2, 3, 4, 5}:
                print("Error: --priority must be 1 (High), 2 (Medium High), 3 (Normal), 4 (Medium Low), or 5 (Low).", file=sys.stderr)
                return 1

        status = parsed.get("status", "draft").strip().lower()
        if status not in {"draft", "active", "complete", "completed", "done", "incomplete"}:
            print("Error: --status must be 'draft', 'active', or 'complete'.", file=sys.stderr)
            return 1

        print(
            run_create(
                service,
                title=title,
                content=content,
                tags=tags,
                author=parsed.get("author", ""),
                status=status,
                priority=priority,
            )
        )
        return 0

    if command == "list":
        print(run_list(service))
        return 0

    if command == "search":
        if len(args) < 2:
            print("Error: search requires <query>.", file=sys.stderr)
            print("Usage: python -m notes_app.cli.main search <query>", file=sys.stderr)
            return 1
        query = " ".join(args[1:])
        print(run_search(service, query=query))
        return 0

    if command == "read":
        if len(args) < 2:
            print("Error: read requires <id|number>.", file=sys.stderr)
            print("Usage: python -m notes_app.cli.main read <id|number>", file=sys.stderr)
            return 1
        output, ok = run_read(service, note_id=args[1])
        if not ok:
            print(output, file=sys.stderr)
            return 1
        print(output)
        return 0

    if command == "update":
        if len(args) < 3:
            print("Error: update requires <id> and at least one flag.", file=sys.stderr)
            print(
                "Usage: python -m notes_app.cli.main update <id> [--title \"...\"] [--tags \"tag1,tag2\"] "
                "[--author \"...\"] [--status complete|incomplete] [--priority 1|2|3|4|5] [--content \"...\"]",
                file=sys.stderr,
            )
            return 1
        output, ok = run_update(service, note_id=args[1], args=list(args[2:]))
        if not ok:
            print(output, file=sys.stderr)
            return 1
        print(output)
        return 0

    if command == "delete":
        if len(args) < 2:
            print("Error: delete requires <id>.", file=sys.stderr)
            print("Usage: python -m notes_app.cli.main delete <id>", file=sys.stderr)
            return 1
        output, ok = run_delete(service, note_id=args[1])
        if not ok:
            print(output, file=sys.stderr)
            return 1
        print(output)
        return 0

    if command == "backup":
        output_dir = args[1] if len(args) >= 2 else None
        output, ok = run_backup(build_backup_service(), output_dir=output_dir)
        if not ok:
            print(output, file=sys.stderr)
            return 1
        print(output)
        return 0

    if command == "restore":
        if len(args) < 2:
            print("Error: restore requires <backup.zip>.", file=sys.stderr)
            print("Usage: python -m notes_app.cli.main restore <backup.zip>", file=sys.stderr)
            return 1
        output, ok = run_restore(build_backup_service(), backup_path=args[1])
        if not ok:
            print(output, file=sys.stderr)
            return 1
        print(output)
        return 0

    print(f"Error: Unknown command '{command}'", file=sys.stderr)
    print("Usage: python -m notes_app.cli.main <command> [args]", file=sys.stderr)
    print("Supported commands: menu, help, create, list, search, read, update, delete, backup, restore", file=sys.stderr)
    print("Run 'python -m notes_app.cli.main help' to see full command usage.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
