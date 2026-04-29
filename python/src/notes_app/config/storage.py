"""
Application storage configuration.

Directory resolution priority for each asset type:
    1. Environment variable override (NOTES_HOME / DATASETS_HOME)
    2. Default: ~/.notes/notes  and  ~/.notes/datasets

Using Path.home() keeps paths correct on macOS, Linux, and Windows.
"""

import os
from pathlib import Path

_DEFAULT_NOTES_SUBDIR = Path(".notes") / "notes"
_DEFAULT_DATASETS_SUBDIR = Path(".notes") / "datasets"


def get_notes_dir() -> Path:
    """Return the configured notes directory as an absolute Path.

    Reads the NOTES_HOME environment variable if set; otherwise falls back
    to the platform-appropriate home directory default.
    """
    env_value = os.environ.get("NOTES_HOME", "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path.home() / _DEFAULT_NOTES_SUBDIR


def ensure_notes_dir() -> Path:
    """Return the notes directory, creating it if it does not exist."""
    notes_dir = get_notes_dir()
    notes_dir.mkdir(parents=True, exist_ok=True)
    return notes_dir


def get_datasets_dir() -> Path:
    """Return the configured datasets directory as an absolute Path.

    Reads the DATASETS_HOME environment variable if set; otherwise falls back
    to ``~/.notes/datasets``.
    """
    env_value = os.environ.get("DATASETS_HOME", "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path.home() / _DEFAULT_DATASETS_SUBDIR


def ensure_datasets_dir() -> Path:
    """Return the datasets directory, creating it if it does not exist."""
    datasets_dir = get_datasets_dir()
    datasets_dir.mkdir(parents=True, exist_ok=True)
    return datasets_dir
