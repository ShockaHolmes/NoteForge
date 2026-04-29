from notes_app.cli import main as cli_main


def test_help_lists_available_note_commands(capsys) -> None:
    exit_code = cli_main.main(["help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Commands:" in captured.out
    assert "create <title> <content>" in captured.out
    assert "list" in captured.out
    assert "search <query>" in captured.out
    assert "read <id>" in captured.out
    assert "update <id>" in captured.out
    assert "delete <id>" in captured.out


def test_missing_command_shows_usage_instructions(capsys) -> None:
    exit_code = cli_main.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Error: Missing command." in captured.err
    assert "Usage: python -m notes_app.cli.main <command> [args]" in captured.err
    assert "help" in captured.err


def test_unknown_command_shows_helpful_message(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_main, "build_service", lambda: object())

    exit_code = cli_main.main(["nope"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Error: Unknown command 'nope'" in captured.err
    assert "Usage: python -m notes_app.cli.main <command> [args]" in captured.err
    assert "Supported commands:" in captured.err
    assert "help" in captured.err
