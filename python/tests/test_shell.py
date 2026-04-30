from datetime import datetime, timezone
from io import StringIO

import pytest

from notes_app.cli.shell import SUPPORTED_COMMANDS, run_shell
from notes_app.models.note import Note
from notes_app.repositories.note_repository import NoteRepository
from notes_app.services.note_service import NoteService


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class InMemoryNoteRepository(NoteRepository):
    def __init__(self, notes: list[Note] | None = None):
        self._notes: list[Note] = list(notes or [])

    def save(self, note: Note) -> None:
        self._notes = [n for n in self._notes if n.id != note.id]
        self._notes.append(note)

    def list_notes(self) -> list[Note]:
        return list(self._notes)

    def get_by_id(self, note_id: str) -> Note | None:
        return next((n for n in self._notes if n.id == note_id), None)

    def delete_by_id(self, note_id: str) -> bool:
        before = len(self._notes)
        self._notes = [n for n in self._notes if n.id != note_id]
        return len(self._notes) != before


def _make_note(note_id: str = "sample", title: str = "Sample Note") -> Note:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Note(
        id=note_id,
        title=title,
        created=now,
        modified=now,
        tags=("demo",),
        content="sample content",
    )


def _make_service(notes: list[Note] | None = None) -> NoteService:
    return NoteService(InMemoryNoteRepository(notes))


def _make_input_fn(lines: list[str]):
    """Return an input function that yields successive lines then raises EOFError."""
    iterator = iter(lines)

    def _input(_prompt: str = "") -> str:
        try:
            return next(iterator)
        except StopIteration:
            raise EOFError

    return _input


# ---------------------------------------------------------------------------
# Tests: banner and welcome output
# ---------------------------------------------------------------------------


def test_shell_prints_welcome_banner(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["quit"]))

    out = capsys.readouterr().out
    assert "Interactive Shell" in out
    assert "help" in out
    assert "quit" in out


# ---------------------------------------------------------------------------
# Tests: quit command
# ---------------------------------------------------------------------------


def test_shell_quit_exits_cleanly(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["quit"]))

    out = capsys.readouterr().out
    # No crash, no leftover error
    assert out is not None


def test_shell_eof_exits_cleanly(capsys) -> None:
    # Empty input sequence triggers EOFError immediately
    run_shell(_make_service(), input_fn=_make_input_fn([]))
    # Should complete without raising
    capsys.readouterr()


# ---------------------------------------------------------------------------
# Tests: help command
# ---------------------------------------------------------------------------


def test_shell_help_lists_all_commands(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["help", "quit"]))

    out = capsys.readouterr().out
    assert "Commands:" in out
    assert "create <title> <content>" in out
    assert "list" in out
    assert "search <query>" in out
    assert "read <id>" in out
    assert "update <id>" in out
    assert "delete <id>" in out


# ---------------------------------------------------------------------------
# Tests: list command
# ---------------------------------------------------------------------------


def test_shell_list_with_notes(capsys) -> None:
    service = _make_service([_make_note()])
    run_shell(service, input_fn=_make_input_fn(["list", "quit"]))

    out = capsys.readouterr().out
    assert "Notes:" in out
    assert "sample.md" in out


def test_shell_list_empty(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["list", "quit"]))

    out = capsys.readouterr().out
    assert "No notes found." in out


# ---------------------------------------------------------------------------
# Tests: create command
# ---------------------------------------------------------------------------


def test_shell_create_note(capsys) -> None:
    service = _make_service()
    run_shell(service, input_fn=_make_input_fn(['create "Hello World" "Some content"', "quit"]))

    out = capsys.readouterr().out
    assert "hello-world.md" in out
    assert service.get_note("hello-world") is not None


def test_shell_create_missing_args_shows_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["create Title", "quit"]))

    out = capsys.readouterr().out
    assert "Error: create requires" in out


# ---------------------------------------------------------------------------
# Tests: search command
# ---------------------------------------------------------------------------


def test_shell_search_finds_match(capsys) -> None:
    service = _make_service([_make_note()])
    run_shell(service, input_fn=_make_input_fn(["search sample", "quit"]))

    out = capsys.readouterr().out
    assert "match(es) found." in out


def test_shell_search_no_query_shows_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["search", "quit"]))

    out = capsys.readouterr().out
    assert "Error: search requires" in out


# ---------------------------------------------------------------------------
# Tests: read command
# ---------------------------------------------------------------------------


def test_shell_read_existing_note(capsys) -> None:
    service = _make_service([_make_note()])
    run_shell(service, input_fn=_make_input_fn(["read sample", "quit"]))

    out = capsys.readouterr().out
    assert "title:    Sample Note" in out
    assert "sample content" in out


def test_shell_read_missing_note_shows_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["read nonexistent", "quit"]))

    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_shell_read_missing_id_shows_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["read", "quit"]))

    out = capsys.readouterr().out
    assert "Error: read requires" in out


# ---------------------------------------------------------------------------
# Tests: update command
# ---------------------------------------------------------------------------


def test_shell_update_note_title(capsys) -> None:
    service = _make_service([_make_note()])
    run_shell(
        service,
        input_fn=_make_input_fn(['update sample --title "New Title"', "quit"]),
    )

    out = capsys.readouterr().out
    assert "Updated note 'sample.md'" in out
    updated = service.get_note("sample")
    assert updated is not None
    assert updated.title == "New Title"


def test_shell_update_missing_args_shows_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["update sample", "quit"]))

    out = capsys.readouterr().out
    assert "Error: update requires" in out


# ---------------------------------------------------------------------------
# Tests: delete command
# ---------------------------------------------------------------------------


def test_shell_delete_note_after_confirmation(capsys) -> None:
    service = _make_service([_make_note()])

    # The delete command calls input() internally for confirmation.
    # We need to supply 'y' for the inner confirmation prompt via confirm_fn.
    # Since run_shell uses our input_fn for the shell prompt but run_delete
    # uses its own confirm_fn (defaulting to built-in input), we monkeypatch
    # delete_command in shell to pass confirm_fn.
    import notes_app.cli.shell as shell_module
    import notes_app.cli.commands.delete_command as delete_mod

    original_run_delete = shell_module.run_delete

    def patched_run_delete(svc, note_id):  # type: ignore[misc]
        return delete_mod.run_delete(svc, note_id=note_id, confirm_fn=lambda _p: "y")

    shell_module.run_delete = patched_run_delete  # type: ignore[assignment]
    try:
        run_shell(service, input_fn=_make_input_fn(["delete sample", "quit"]))
    finally:
        shell_module.run_delete = original_run_delete

    out = capsys.readouterr().out
    assert "Deleted note 'sample.md'" in out
    assert service.get_note("sample") is None


def test_shell_delete_missing_id_shows_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["delete", "quit"]))

    out = capsys.readouterr().out
    assert "Error: delete requires" in out


# ---------------------------------------------------------------------------
# Tests: unknown command
# ---------------------------------------------------------------------------


def test_shell_unknown_command_shows_hint(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["frobnicate", "quit"]))

    out = capsys.readouterr().out
    assert "Unknown command: 'frobnicate'" in out
    assert "help" in out


# ---------------------------------------------------------------------------
# Tests: empty input is ignored
# ---------------------------------------------------------------------------


def test_shell_empty_input_is_ignored(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(["", "   ", "quit"]))
    # Should complete without errors
    capsys.readouterr()


# ---------------------------------------------------------------------------
# Tests: unmatched quotes produce error not crash
# ---------------------------------------------------------------------------


def test_shell_unmatched_quotes_gives_error(capsys) -> None:
    run_shell(_make_service(), input_fn=_make_input_fn(['create "bad quote', "quit"]))

    out = capsys.readouterr().out
    assert "could not parse input" in out


# ---------------------------------------------------------------------------
# Tests: keyboard interrupt
# ---------------------------------------------------------------------------


def test_shell_keyboard_interrupt_continues(capsys) -> None:
    call_count = 0

    def _input_raising(_prompt: str = "") -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise KeyboardInterrupt
        return "quit"

    run_shell(_make_service(), input_fn=_input_raising)

    out = capsys.readouterr().out
    assert "quit" in out.lower()


# ---------------------------------------------------------------------------
# Tests: SUPPORTED_COMMANDS includes all expected commands
# ---------------------------------------------------------------------------


def test_supported_commands_include_all_note_operations() -> None:
    for cmd in ("help", "list", "create", "search", "read", "update", "delete", "quit"):
        assert cmd in SUPPORTED_COMMANDS


def test_supported_commands_include_backup_and_restore() -> None:
    assert "backup" in SUPPORTED_COMMANDS
    assert "restore" in SUPPORTED_COMMANDS
