"""Interactive shell (menu) for the notes application."""

import shlex
import sys
from collections.abc import Callable

from notes_app.cli.commands.backup_command import run_backup
from notes_app.cli.commands.create_command import run_create
from notes_app.cli.commands.delete_command import run_delete
from notes_app.cli.commands.help_command import render_help
from notes_app.cli.commands.list_command import run_list
from notes_app.cli.commands.read_command import run_read
from notes_app.cli.commands.restore_command import run_restore
from notes_app.cli.commands.search_command import run_search
from notes_app.cli.commands.update_command import run_update
from notes_app.services.backup_service import BackupService
from notes_app.services.note_service import NoteService

PROMPT = "notes> "
PROGRAM_NAME = "notes shell"

SUPPORTED_COMMANDS = (
    "help",
    "list",
    "create",
    "search",
    "read",
    "update",
    "delete",
    "backup",
    "restore",
    "quit",
)


def _show_help() -> None:
    """Display help for all available commands."""
    print(render_help(PROGRAM_NAME))


def _handle_command(
    command: str,
    args: list[str],
    service: NoteService,
    backup_service: BackupService | None,
) -> bool:
    """Dispatch a single command.  Returns False when the user requests quit."""
    if command == "quit":
        return False

    if command == "help":
        _show_help()

    elif command == "list":
        print(run_list(service))

    elif command == "create":
        if len(args) < 2:
            print("Error: create requires <title> and <content>.")
            print('Usage: create "Title" "Content"')
        else:
            title = args[0]
            content = " ".join(args[1:])
            print(run_create(service, title=title, content=content))

    elif command == "search":
        if not args:
            print("Error: search requires <query>.")
            print("Usage: search <query>")
        else:
            query = " ".join(args)
            print(run_search(service, query=query))

    elif command == "read":
        if not args:
            print("Error: read requires <id>.")
            print("Usage: read <id>")
        else:
            output, ok = run_read(service, note_id=args[0])
            if ok:
                print(output)
            else:
                print(output, file=sys.stderr)

    elif command == "update":
        if len(args) < 2:
            print("Error: update requires <id> and at least one flag.")
            print('Usage: update <id> [--title "..."] [--tags "tag1,tag2"] [--content "..."]')
        else:
            output, ok = run_update(service, note_id=args[0], args=list(args[1:]))
            if ok:
                print(output)
            else:
                print(output, file=sys.stderr)

    elif command == "delete":
        if not args:
            print("Error: delete requires <id>.")
            print("Usage: delete <id>")
        else:
            output, ok = run_delete(service, note_id=args[0])
            if ok:
                print(output)
            else:
                print(output, file=sys.stderr)

    elif command == "backup":
        if backup_service is None:
            print("Error: backup service is not available.", file=sys.stderr)
        else:
            output_dir = args[0] if args else None
            output, ok = run_backup(backup_service, output_dir=output_dir)
            if ok:
                print(output)
            else:
                print(output, file=sys.stderr)

    elif command == "restore":
        if backup_service is None:
            print("Error: backup service is not available.", file=sys.stderr)
        elif not args:
            print("Error: restore requires <backup.zip>.")
            print("Usage: restore <backup.zip>")
        else:
            output, ok = run_restore(backup_service, backup_path=args[0])
            if ok:
                print(output)
            else:
                print(output, file=sys.stderr)

    else:
        print(f"Unknown command: '{command}'")
        print(f"Supported commands: {', '.join(SUPPORTED_COMMANDS)}")
        print("Type 'help' for usage details.")

    return True


def run_shell(
    service: NoteService,
    backup_service: BackupService | None = None,
    input_fn: Callable[[str], str] = input,
) -> None:
    """Run the interactive notes shell until the user quits."""
    print("Future Proof Notes Manager - Interactive Shell")
    print("Type 'help' for available commands, 'quit' to exit.")
    print()

    while True:
        try:
            line = input_fn(PROMPT).strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit.")
            continue

        if not line:
            continue

        try:
            parts = shlex.split(line)
        except ValueError:
            print("Error: could not parse input (unmatched quotes?).")
            continue

        command = parts[0].lower()
        args = parts[1:]

        keep_running = _handle_command(command, args, service, backup_service)
        if not keep_running:
            break


def main() -> int:
    """Start the interactive notes shell."""
    from notes_app.cli.main import build_backup_service, build_service  # local import avoids cycles

    service = build_service()
    backup_service = build_backup_service()

    run_shell(service, backup_service=backup_service)
    print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
