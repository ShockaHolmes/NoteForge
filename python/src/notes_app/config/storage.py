"""
Application storage configuration.

The notes directory is resolved in this priority order:
  1. NOTES_HOME environment variable (set a custom absolute path)
  2. Default: ~/.notes/notes

Using Path.home() keeps paths correct on macOS, Linux, and Windows.
"""

import os
from pathlib import Path

_DEFAULT_NOTES_SUBDIR = Path(".notes") / "notes"


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
