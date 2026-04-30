"""
NoteForge interactive menu.

Launched automatically when the CLI is run without arguments.
"""

from __future__ import annotations

from pathlib import Path

from notes_app.cli.commands.backup_command import run_backup
from notes_app.cli.commands.create_command import run_create
from notes_app.cli.commands.delete_command import run_delete
from notes_app.cli.commands.help_command import render_help
from notes_app.cli.commands.list_command import run_list
from notes_app.cli.commands.read_command import run_read
from notes_app.cli.commands.restore_command import run_restore
from notes_app.cli.commands.search_command import run_search
from notes_app.cli.commands.update_command import run_update
from notes_app.config.storage import ensure_datasets_dir, ensure_notes_dir
from notes_app.services.backup_service import BackupService
from notes_app.services.note_service import NoteService

# ── cosmetics ────────────────────────────────────────────────────────────────

_COLOR_CYAN    = "\033[96m"
_COLOR_GOLD    = "\033[93m"
_COLOR_MAGENTA = "\033[95m"
_COLOR_BOLD    = "\033[1m"
_COLOR_RESET   = "\033[0m"

_BOX_W      = 58
_BOX_TOP    = "╔" + "═" * _BOX_W + "╗"
_BOX_BOTTOM = "╚" + "═" * _BOX_W + "╝"
_BOX_EMPTY  = "║" + " " * _BOX_W + "║"

_BANNER_ART = [
    "   _   _       _       _____                              ",
    "  | \\ | | ___ | |_ ___| ____|__  _ __ __ _  ___          ",
    "  |  \\| |/ _ \\| __/ _ \\  _| / _|| '__/ _` |/ _ \\       ",
    "  | |\\  | (_) | ||  __/ |__| (__ | | | (_| |  __/        ",
    "  |_| \\_|\\___/ \\__\\___|_____\\___||_|  \\__, |\\___|       ",
    "                                        |___/             ",
]

_TAGLINE = "~  Your Smart Note Manager  ~"

_DIVIDER = "─" * 60

_MENU_ITEMS = [
    ("1", "New Note"),
    ("2", "Update Note"),
    ("3", "Delete Note"),
    ("4", "Save Note"),
    ("5", "Backup"),
    ("6", "List"),
    ("7", "Help"),
    ("8", "Read"),
    ("9", "Restore"),
    ("10", "Search"),
    ("11", "Quit"),
]


def _clear() -> None:
    """Print enough blank lines to give the impression of a cleared screen."""
    print("\n" * 3)


def _print_menu() -> None:
    _clear()
    g, c, m, b, r = _COLOR_GOLD, _COLOR_CYAN, _COLOR_MAGENTA, _COLOR_BOLD, _COLOR_RESET
    print(f"{g}{b}{_BOX_TOP}{r}")
    print(f"{g}{b}{_BOX_EMPTY}{r}")
    for line in _BANNER_ART:
        print(f"{g}{b}║{r}{c}{line.ljust(_BOX_W)}{r}{g}{b}║{r}")
    print(f"{g}{b}{_BOX_EMPTY}{r}")
    print(f"{g}{b}║{r}{m}{b}{_TAGLINE.center(_BOX_W)}{r}{g}{b}║{r}")
    print(f"{g}{b}{_BOX_EMPTY}{r}")
    print(f"{g}{b}{_BOX_BOTTOM}{r}")
    print()
    for key, label in _MENU_ITEMS:
        print(f"  [{key}]  {label}")
    print(_DIVIDER)


def _prompt(text: str, default: str = "") -> str:
    value = input(text).strip()
    return value if value else default


def _build_backup_service() -> BackupService:
    return BackupService(
        notes_dir=ensure_notes_dir(),
        datasets_dir=ensure_datasets_dir(),
    )


# ── note picker ──────────────────────────────────────────────────────────────

def _pick_note(service: NoteService, action_label: str) -> str | None:
    """Show a numbered list of notes and return the selected note id, or None."""
    notes = service.list_notes()
    if not notes:
        print("\n  No notes found.")
        input("\n  Press Enter to return to menu…")
        return None

    print(f"\n  Select a note to {action_label}:\n")
    for i, note in enumerate(notes, 1):
        tags = ", ".join(note.tags) if note.tags else "—"
        print(
            f"  [{i}]  {note.title}  (id: {note.id})  "
            f"status: {note.status}  priority: {note.priority}  tags: {tags}"
        )
    print()

    raw = _prompt("  Enter number (or press Enter to cancel): ")
    if not raw:
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(notes):
            return notes[idx].id
    except ValueError:
        pass
    print("\n  Invalid selection.")
    input("  Press Enter to continue…")
    return None


# ── menu actions ─────────────────────────────────────────────────────────────

def _action_new_note(service: NoteService) -> None:
    print("\n" + _DIVIDER)
    print("  NEW NOTE")
    print(_DIVIDER)

    title = _prompt("  Title: ")
    if not title:
        print("  Title is required. Returning to menu.")
        input("\n  Press Enter to continue…")
        return

    print("  Content (type your note below).")
    print("  Enter a blank line followed by 'END' to finish, or just 'END' to save with no body.")
    print()

    lines: list[str] = []
    while True:
        line = input("  > ")
        if line.strip().upper() == "END":
            break
        lines.append(line)

    content = "\n".join(lines)
    tags_raw = _prompt("  Tags (comma-separated): ")
    tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip()) if tags_raw else ()
    author = _prompt("  Created by (name): ")
    status = "draft"

    priority_raw = _prompt("  Priority [1=High  2=Med-High  3=Normal  4=Med-Low  5=Low] (default: 3): ", default="3")
    try:
        priority = int(priority_raw)
    except ValueError:
        priority = 3
    if priority not in {1, 2, 3, 4, 5}:
        priority = 3

    print()
    save = _prompt("  Save this note? [Y/n]: ", default="y").lower()
    if save not in {"y", "yes"}:
        print("  Discarded.")
        input("\n  Press Enter to continue…")
        return

    result = run_create(
        service,
        title=title,
        content=content,
        tags=tags,
        author=author,
        status=status,
        priority=priority,
    )
    print(f"\n  ✓ {result} (status: draft)")
    input("\n  Press Enter to continue…")


def _action_update_note(service: NoteService) -> None:
    print("\n" + _DIVIDER)
    print("  UPDATE NOTE")
    print(_DIVIDER)

    note_id = _pick_note(service, "update")
    if note_id is None:
        return

    note = service.get_note(note_id)
    if note is None:
        print(f"\n  Note '{note_id}' not found.")
        input("\n  Press Enter to continue…")
        return

    print(f"\n  Editing: {note.title}")
    print("  (Press Enter to keep the current value.)\n")

    new_title = _prompt(f"  Title [{note.title}]: ")
    new_author = _prompt(f"  Author [{note.author or '(unknown)'}]: ")
    raw_tags = _prompt(f"  Tags [{', '.join(note.tags) or '—'}] (comma-separated): ")
    new_status = _prompt(f"  Status [{note.status}] (draft/active/complete): ")
    new_priority = _prompt(f"  Priority [{note.priority}] (1=High/2=Med-High/3=Normal/4=Med-Low/5=Low): ")

    print("  New content — type below; 'END' on its own line to finish.")
    print("  (Press Enter then END immediately to keep the existing content.)\n")
    lines: list[str] = []
    while True:
        line = input("  > ")
        if line.strip().upper() == "END":
            break
        lines.append(line)
    new_content = "\n".join(lines) if lines else None

    # Build update args only for fields the user actually provided
    update_args: list[str] = []
    if new_title:
        update_args += ["--title", new_title]
    if raw_tags:
        update_args += ["--tags", raw_tags]
    if new_author:
        update_args += ["--author", new_author]
    if new_status:
        update_args += ["--status", new_status]
    if new_priority:
        update_args += ["--priority", new_priority]
    if new_content is not None:
        update_args += ["--content", new_content]

    if not update_args:
        print("\n  Nothing to update. Returning to menu.")
        input("\n  Press Enter to continue…")
        return

    msg, ok = run_update(service, note_id=note_id, args=update_args)
    prefix = "✓" if ok else "✗"
    print(f"\n  {prefix} {msg}")
    if ok:
        service.update_note(note_id, status="complete")
        print("  ✓ Note saved.")
    input("\n  Press Enter to continue…")


def _action_delete_note(service: NoteService) -> None:
    print("\n" + _DIVIDER)
    print("  DELETE NOTE")
    print(_DIVIDER)

    note_id = _pick_note(service, "delete")
    if note_id is None:
        return

    msg, ok = run_delete(service, note_id=note_id)
    prefix = "✓" if ok else "✗"
    print(f"\n  {prefix} {msg}")
    input("\n  Press Enter to continue…")


def _action_save_note(service: NoteService) -> None:
    """Export an existing note to a file path of the user's choice."""
    print("\n" + _DIVIDER)
    print("  SAVE NOTE TO FILE")
    print(_DIVIDER)

    note_id = _pick_note(service, "save")
    if note_id is None:
        return

    note = service.get_note(note_id)
    if note is None:
        print(f"\n  Note '{note_id}' not found.")
        input("\n  Press Enter to continue…")
        return

    default_path = str(Path.home() / f"{note.id}.md")
    dest = _prompt(f"  Save to [{default_path}]: ", default=default_path)

    dest_path = Path(dest).expanduser().resolve()
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(
            f"---\n"
            f"id: {note.id}\n"
            f"title: {note.title}\n"
            f"author: {note.author}\n"
            f"created: {note.created}\n"
            f"modified: {note.modified}\n"
            f"tags: [{', '.join(note.tags)}]\n"
            f"status: {note.status}\n"
            f"priority: {note.priority}\n"
            f"---\n\n"
            f"{note.content or ''}",
            encoding="utf-8",
        )

        # Mark note complete after save/export, per lifecycle semantics.
        service.update_note(note_id=note.id, status="complete")
        print(f"\n  ✓ Saved to {dest_path}")
    except OSError as exc:
        print(f"\n  ✗ Could not save file: {exc}")

    input("\n  Press Enter to continue…")


def _action_backup() -> None:
    print("\n" + _DIVIDER)
    print("  BACKUP")
    print(_DIVIDER)

    output_dir = _prompt("  Output directory (blank = current directory): ")
    msg, ok = run_backup(_build_backup_service(), output_dir=output_dir or None)
    prefix = "✓" if ok else "✗"
    print(f"\n  {prefix} {msg}")
    input("\n  Press Enter to continue…")


def _action_list_notes(service: NoteService) -> None:
    print("\n" + _DIVIDER)
    print("  LIST NOTES")
    print(_DIVIDER)
    print()
    print(run_list(service))
    input("\n  Press Enter to continue…")


def _action_help() -> None:
    print("\n" + _DIVIDER)
    print("  HELP")
    print(_DIVIDER)
    print()
    print(render_help("python -m notes_app.cli.main"))
    input("\n  Press Enter to continue…")


def _action_read_note(service: NoteService) -> None:
    print("\n" + _DIVIDER)
    print("  READ NOTE")
    print(_DIVIDER)

    note_id = _pick_note(service, "read")
    if note_id is None:
        return

    msg, ok = run_read(service, note_id=note_id)
    prefix = "✓" if ok else "✗"
    print(f"\n  {prefix} {msg}")
    input("\n  Press Enter to continue…")


def _action_restore() -> None:
    print("\n" + _DIVIDER)
    print("  RESTORE")
    print(_DIVIDER)

    backup_path = _prompt("  Backup zip path: ")
    if not backup_path:
        print("\n  Restore cancelled (no backup path provided).")
        input("\n  Press Enter to continue…")
        return

    msg, ok = run_restore(_build_backup_service(), backup_path=backup_path)
    prefix = "✓" if ok else "✗"
    print(f"\n  {prefix} {msg}")
    input("\n  Press Enter to continue…")


def _action_search(service: NoteService) -> None:
    print("\n" + _DIVIDER)
    print("  SEARCH")
    print(_DIVIDER)

    query = _prompt("  Search query: ")
    if not query:
        print("\n  Search cancelled (empty query).")
        input("\n  Press Enter to continue…")
        return

    print()
    print(run_search(service, query=query))
    input("\n  Press Enter to continue…")


# ── main loop ─────────────────────────────────────────────────────────────────

def run_menu(service: NoteService) -> int:
    """Run the interactive NoteForge menu loop. Returns the exit code."""
    while True:
        _print_menu()
        choice = _prompt("  Choose an option: ").strip()

        if choice == "1":
            _action_new_note(service)
        elif choice == "2":
            _action_update_note(service)
        elif choice == "3":
            _action_delete_note(service)
        elif choice == "4":
            _action_save_note(service)
        elif choice == "5":
            _action_backup()
        elif choice == "6":
            _action_list_notes(service)
        elif choice == "7":
            _action_help()
        elif choice == "8":
            _action_read_note(service)
        elif choice == "9":
            _action_restore()
        elif choice == "10":
            _action_search(service)
        elif choice in {"11", "q", "quit", "exit"}:
            _clear()
            print("  Goodbye from NoteForge.\n")
            return 0
        else:
            print(f"\n  Unknown option '{choice}'. Please choose one of 1-11 or q.")
            input("  Press Enter to continue…")
