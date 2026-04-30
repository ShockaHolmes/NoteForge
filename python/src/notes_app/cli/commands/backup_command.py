from datetime import datetime, timezone
from pathlib import Path

from notes_app.services.backup_service import BackupService


def run_backup(service: BackupService, output_dir: str | None = None) -> tuple[str, bool]:
    """Create a backup zip and return (output_message, ok)."""
    target_dir = Path(output_dir).expanduser().resolve() if output_dir else Path.cwd()

    timestamp = (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
        .replace(":", "-")
        .replace(".", "-")
    )
    filename = f"notes-backup-{timestamp}.zip"
    output_path = target_dir / filename

    try:
        manifest = service.create_backup(output_path)
    except OSError as exc:
        return f"Error: Could not write backup: {exc}", False

    note_count = len(manifest.notes)
    dataset_count = len(manifest.datasets)
    return (
        f"Backup created: {output_path}\n"
        f"  {note_count} note(s), {dataset_count} dataset(s)",
        True,
    )
