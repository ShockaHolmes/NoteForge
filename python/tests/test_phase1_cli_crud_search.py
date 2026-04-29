from pathlib import Path
from typing import Any

import pytest
import yaml

from notes_app.cli import main as cli_main
from notes_app.cli.commands.delete_command import run_delete


def _parse_frontmatter_yaml(note_path: Path) -> dict[str, Any]:
    text = note_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines and lines[0] == "---", "File must start with YAML front-matter '---'"

    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    assert end is not None, "Closing '---' not found in front-matter"

    raw_yaml = "\n".join(lines[1:end])
    metadata = yaml.safe_load(raw_yaml)
    assert isinstance(metadata, dict), "Front-matter must parse to a YAML mapping"
    return metadata


def _assert_frontmatter_yaml_is_valid(note_path: Path) -> None:
    metadata = _parse_frontmatter_yaml(note_path)

    for required_key in ("id", "title", "created", "modified", "tags"):
        assert required_key in metadata, f"Front-matter missing key: {required_key}"

    # Timestamps must parse cleanly from YAML (PyYAML yields datetime objects or strings).
    for ts_key in ("created", "modified"):
        value = metadata[ts_key]
        assert value is not None, f"{ts_key} must not be null"

    # Tags must be a YAML sequence.
    assert isinstance(metadata["tags"], list), "tags must be a YAML sequence"


def test_cli_crud_search_flow_uses_temp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    notes_dir = tmp_path / "notes-store"
    monkeypatch.setenv("NOTES_HOME", str(notes_dir))

    create_exit = cli_main.main(["create", "Phase One Note", "body has kiwi term"])
    create_out = capsys.readouterr().out
    assert create_exit == 0
    assert "phase-one-note.md" in create_out

    note_path = notes_dir / "phase-one-note.md"
    assert note_path.exists()
    _assert_frontmatter_yaml_is_valid(note_path)

    search_exit = cli_main.main(["search", "kiwi"])
    search_out = capsys.readouterr().out
    assert search_exit == 0
    assert "id: phase-one-note" in search_out
    assert "title: Phase One Note" in search_out
    assert "context:" in search_out

    read_exit = cli_main.main(["read", "phase-one-note"])
    read_out = capsys.readouterr().out
    assert read_exit == 0
    assert "title:    Phase One Note" in read_out
    assert "body has kiwi term" in read_out

    update_exit = cli_main.main(
        [
            "update",
            "phase-one-note",
            "--title",
            "Phase One Updated",
            "--tags",
            "phase1,cli",
            "--content",
            "updated body content",
        ]
    )
    update_out = capsys.readouterr().out
    assert update_exit == 0
    assert "Updated note 'phase-one-note.md'" in update_out

    reread_exit = cli_main.main(["read", "phase-one-note"])
    reread_out = capsys.readouterr().out
    assert reread_exit == 0
    assert "title:    Phase One Updated" in reread_out
    assert "tags:     phase1, cli" in reread_out
    assert "updated body content" in reread_out

    monkeypatch.setattr(
        cli_main,
        "run_delete",
        lambda service, note_id: run_delete(service, note_id, confirm_fn=lambda _p: "y"),
    )
    delete_exit = cli_main.main(["delete", "phase-one-note.md"])
    delete_out = capsys.readouterr().out
    assert delete_exit == 0
    assert "Deleted note 'phase-one-note.md'" in delete_out
    assert not note_path.exists()

    missing_exit = cli_main.main(["read", "phase-one-note"])
    missing_err = capsys.readouterr().err
    assert missing_exit == 1
    assert "not found" in missing_err.lower()


def test_search_no_results_with_temp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("NOTES_HOME", str(tmp_path / "notes-empty"))

    create_exit = cli_main.main(["create", "Alpha", "This is unrelated"])
    _ = capsys.readouterr()
    assert create_exit == 0

    search_exit = cli_main.main(["search", "zzz-no-match"])
    search_out = capsys.readouterr().out
    assert search_exit == 0
    assert "No notes matched 'zzz-no-match'." in search_out
