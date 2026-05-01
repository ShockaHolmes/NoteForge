from notes_app.cli import main as cli_main


def test_help_lists_available_note_commands(capsys) -> None:
    exit_code = cli_main.main(["help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Commands:" in captured.out
    assert "create <title> <content>" in captured.out
    assert "list" in captured.out
    assert "search <query>" in captured.out
    assert "read <id|number>" in captured.out
    assert "update <id>" in captured.out
    assert "delete <id>" in captured.out


def test_no_args_launches_noteforge_menu(monkeypatch, capsys) -> None:
    # Simulate the user immediately choosing "11" (Quit) at the menu prompt.
    monkeypatch.setattr("builtins.input", lambda _prompt="": "11")

    exit_code = cli_main.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "NoteForge" in captured.out or "Goodbye" in captured.out


def test_unknown_command_shows_helpful_message(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_main, "build_service", lambda: object())

    exit_code = cli_main.main(["nope"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Error: Unknown command 'nope'" in captured.err
    assert "Usage: python -m notes_app.cli.main <command> [args]" in captured.err
    assert "Supported commands:" in captured.err
    assert "help" in captured.err
