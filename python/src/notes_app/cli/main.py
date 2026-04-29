import sys

from notes_app.cli.commands.create_command import run_create
from notes_app.cli.commands.delete_command import run_delete
from notes_app.cli.commands.help_command import render_help
from notes_app.cli.commands.list_command import run_list
from notes_app.cli.commands.read_command import run_read
from notes_app.cli.commands.search_command import run_search
from notes_app.cli.commands.update_command import run_update
from notes_app.config.storage import ensure_notes_dir
from notes_app.repositories.file_note_repository import FileNoteRepository
from notes_app.services.note_service import NoteService


def build_service() -> NoteService:
    notes_dir = ensure_notes_dir()
    repository = FileNoteRepository(notes_dir)
    return NoteService(repository)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Error: Missing command.", file=sys.stderr)
        print("Usage: python -m notes_app.cli.main <command> [args]", file=sys.stderr)
        print("Try 'python -m notes_app.cli.main help' for more information.", file=sys.stderr)
        return 1

    command = args[0].lower()
    service = build_service()

    if command == "help":
        print(render_help("python -m notes_app.cli.main"))
        return 0

    if command == "create":
        if len(args) < 3:
            print("Error: create requires <title> and <content>.", file=sys.stderr)
            print("Usage: python -m notes_app.cli.main create \"Title\" \"Content\"", file=sys.stderr)
            return 1
        title = args[1]
        content = " ".join(args[2:])
        print(run_create(service, title=title, content=content))
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
            print("Error: read requires <id>.", file=sys.stderr)
            print("Usage: python -m notes_app.cli.main read <id>", file=sys.stderr)
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
            print("Usage: python -m notes_app.cli.main update <id> [--title \"...\"] [--tags \"tag1,tag2\"] [--content \"...\"]", file=sys.stderr)
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

    print(f"Error: Unknown command '{command}'", file=sys.stderr)
    print("Usage: python -m notes_app.cli.main <command> [args]", file=sys.stderr)
    print("Supported commands: help, create, list, search, read, update, delete", file=sys.stderr)
    print("Run 'python -m notes_app.cli.main help' to see full command usage.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
