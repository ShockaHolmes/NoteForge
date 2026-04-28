import os
from pathlib import Path

import pytest

from notes_app.config.storage import ensure_notes_dir, get_notes_dir


def test_get_notes_dir_default_is_home_based() -> None:
    os.environ.pop("NOTES_HOME", None)
    result = get_notes_dir()
    assert result == Path.home() / ".notes" / "notes"


def test_get_notes_dir_reads_notes_home_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "custom_notes"
    monkeypatch.setenv("NOTES_HOME", str(custom))
    result = get_notes_dir()
    assert result == custom.resolve()


def test_ensure_notes_dir_creates_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "new_notes_dir"
    assert not target.exists()
    monkeypatch.setenv("NOTES_HOME", str(target))
    created = ensure_notes_dir()
    assert created.exists()
    assert created.is_dir()


def test_ensure_notes_dir_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "existing_notes_dir"
    target.mkdir()
    monkeypatch.setenv("NOTES_HOME", str(target))
    ensure_notes_dir()
    ensure_notes_dir()
    assert target.exists()
