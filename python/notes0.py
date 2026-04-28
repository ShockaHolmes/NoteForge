#!/usr/bin/env python3
"""
Future Proof Notes Manager - Version Zero (CLI)
A personal notes manager using text files with YAML headers.
Command-line interface version.
"""

import sys
from pathlib import Path


def setup():
    """Initialize the notes application."""
    # Define the notes directory in HOME
    notes_dir = Path.home() / ".notes"

    # Check if notes directory exists (silent check for CLI version)
    if not notes_dir.exists():
        # For CLI version, we don't automatically display this
        # It will be shown if needed by specific commands
        pass

    return notes_dir


def get_program_name():
    """Return the executable name used to start this script."""
    return Path(sys.argv[0]).name or "notes0.py"


def show_help(program_name):
    """Display help information."""
    help_text = """
Future Proof Notes Manager v0.0

Usage: {} [command]

Available commands:
  help    - Display this help information

Notes directory: {}
    """.format(program_name, Path.home() / ".notes")
    print(help_text.strip())


def finish(exit_code=0):
    """Clean up and exit the application."""
    sys.exit(exit_code)


def main():
    """Main entry point for the notes CLI application."""
    # Setup
    setup()
    program_name = get_program_name()

    # Parse command-line arguments
    if len(sys.argv) < 2:
        # No command provided
        print("Error: Missing command.", file=sys.stderr)
        print(f"Usage: {program_name} [command]", file=sys.stderr)
        print(f"Try '{program_name} help' for more information.", file=sys.stderr)
        finish(1)

    command = sys.argv[1].lower()

    # Process command
    if command == "help":
        show_help(program_name)
        finish(0)
    else:
        print(f"Error: Unknown command '{command}'", file=sys.stderr)
        print("Supported commands: help", file=sys.stderr)
        print(f"Try '{program_name} help' for more information.", file=sys.stderr)
        finish(1)


if __name__ == "__main__":
    main()
