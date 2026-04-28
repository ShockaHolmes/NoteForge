#!/usr/bin/env python3
"""Smoke tests for notes0.py CLI acceptance criteria."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
NOTES0 = SCRIPT_DIR / "notes0.py"


class CheckResult:
    def __init__(self, name: str, ok: bool, detail: str):
        self.name = name
        self.ok = ok
        self.detail = detail


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(NOTES0), *args],
        cwd=str(SCRIPT_DIR),
        text=True,
        capture_output=True,
        check=False,
    )


def check_help() -> CheckResult:
    result = run_command("help")
    ok = (
        result.returncode == 0
        and "Future Proof Notes Manager v0.0" in result.stdout
        and "Usage:" in result.stdout
        and "Available commands:" in result.stdout
    )
    detail = (
        f"exit={result.returncode}; stdout={result.stdout.strip()!r}; stderr={result.stderr.strip()!r}"
    )
    return CheckResult("help output", ok, detail)


def check_missing_command() -> CheckResult:
    result = run_command()
    ok = (
        result.returncode == 1
        and "Error: Missing command." in result.stderr
        and "Try 'notes0.py help' for more information." in result.stderr
    )
    detail = (
        f"exit={result.returncode}; stdout={result.stdout.strip()!r}; stderr={result.stderr.strip()!r}"
    )
    return CheckResult("missing command", ok, detail)


def check_unknown_command() -> CheckResult:
    result = run_command("frobnicate")
    ok = (
        result.returncode == 1
        and "Error: Unknown command 'frobnicate'" in result.stderr
        and "Supported commands: help" in result.stderr
    )
    detail = (
        f"exit={result.returncode}; stdout={result.stdout.strip()!r}; stderr={result.stderr.strip()!r}"
    )
    return CheckResult("unknown command", ok, detail)


def main() -> int:
    checks = [check_help(), check_missing_command(), check_unknown_command()]
    failed = [check for check in checks if not check.ok]

    if not failed:
        print("PASS: notes0 acceptance smoke tests")
        return 0

    print("FAIL: notes0 acceptance smoke tests")
    for check in failed:
        print(f"- {check.name}: {check.detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
