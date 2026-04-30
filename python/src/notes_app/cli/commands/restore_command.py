from pathlib import Path

from notes_app.services.backup_service import BackupService


def run_restore(service: BackupService, backup_path: str) -> tuple[str, bool]:
    """Restore a backup zip and return (output_message, ok)."""
    source = Path(backup_path).expanduser().resolve()

    try:
        manifest = service.restore_backup(source)
    except FileNotFoundError as exc:
        return f"Error: {exc}", False
    except (ValueError, Exception) as exc:
        return f"Error: Could not restore backup: {exc}", False

    note_count = len(manifest.notes)
    dataset_count = len(manifest.datasets)
    return (
        f"Restore complete from: {source}\n"
        f"  {note_count} note(s), {dataset_count} dataset(s) restored",
        True,
    )
