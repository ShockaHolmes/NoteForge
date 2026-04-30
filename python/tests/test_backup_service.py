"""Tests for BackupService — create_backup and restore_backup."""

import json
import zipfile
from pathlib import Path

import pytest

from notes_app.services.backup_service import BackupManifest, BackupService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_note(notes_dir: Path, slug: str, content: str = "hello") -> Path:
    path = notes_dir / f"{slug}.md"
    path.write_text(
        f"---\nid: {slug}\ntitle: {slug.replace('-', ' ').title()}\ncreated: 2026-04-30T00:00:00Z\nmodified: 2026-04-30T00:00:00Z\n---\n{content}",
        encoding="utf-8",
    )
    return path


def _write_dataset(
    datasets_dir: Path,
    filename: str,
    raw_bytes: bytes,
    sidecar_text: str,
) -> tuple[Path, Path]:
    data_path = datasets_dir / filename
    sidecar_path = datasets_dir / f"{filename}.dataset.yml"
    data_path.write_bytes(raw_bytes)
    sidecar_path.write_text(sidecar_text, encoding="utf-8")
    return data_path, sidecar_path


def _write_sidecar_only(datasets_dir: Path, dataset_id: str) -> Path:
    sidecar_path = datasets_dir / f"{dataset_id}.dataset.yml"
    sidecar_path.write_text(
        f"id: {dataset_id}\ntitle: Meta Only\ncreated: 2026-04-30T00:00:00Z\nmodified: 2026-04-30T00:00:00Z\n",
        encoding="utf-8",
    )
    return sidecar_path


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------


def test_build_manifest_empty_dirs(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    datasets_dir = tmp_path / "datasets"
    notes_dir.mkdir()
    datasets_dir.mkdir()

    service = BackupService(notes_dir, datasets_dir)
    manifest = service.build_manifest()

    assert manifest.version == 1
    assert manifest.notes == []
    assert manifest.datasets == []


def test_build_manifest_missing_dirs(tmp_path: Path) -> None:
    service = BackupService(tmp_path / "notes", tmp_path / "datasets")
    manifest = service.build_manifest()

    assert manifest.notes == []
    assert manifest.datasets == []


def test_build_manifest_lists_note_files(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    _write_note(notes_dir, "my-note")
    _write_note(notes_dir, "another-note")

    service = BackupService(notes_dir, tmp_path / "datasets")
    manifest = service.build_manifest()

    assert "notes/my-note.md" in manifest.notes
    assert "notes/another-note.md" in manifest.notes
    assert len(manifest.notes) == 2


def test_build_manifest_lists_dataset_with_data_file(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()

    csv_bytes = b"col1,col2\nval1,val2\n"
    sidecar_text = "id: sales\ntitle: Sales\ncreated: 2026-04-30T00:00:00Z\nmodified: 2026-04-30T00:00:00Z\nformat: csv\npath: sales.csv\n"
    _write_dataset(datasets_dir, "sales.csv", csv_bytes, sidecar_text)

    service = BackupService(notes_dir, datasets_dir)
    manifest = service.build_manifest()

    assert len(manifest.datasets) == 1
    entry = manifest.datasets[0]
    assert entry.sidecar == "datasets/sales.csv.dataset.yml"
    assert entry.data == "datasets/sales.csv"


def test_build_manifest_lists_sidecar_only_dataset(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()

    _write_sidecar_only(datasets_dir, "meta-only")

    service = BackupService(notes_dir, datasets_dir)
    manifest = service.build_manifest()

    assert len(manifest.datasets) == 1
    entry = manifest.datasets[0]
    assert entry.sidecar == "datasets/meta-only.dataset.yml"
    assert entry.data is None


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------


def test_create_backup_produces_zip(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    _write_note(notes_dir, "my-note")

    output = tmp_path / "out" / "backup.zip"
    service = BackupService(notes_dir, tmp_path / "datasets")
    service.create_backup(output)

    assert output.exists()
    assert zipfile.is_zipfile(output)


def test_create_backup_zip_contains_manifest(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    _write_note(notes_dir, "my-note")

    output = tmp_path / "backup.zip"
    service = BackupService(notes_dir, tmp_path / "datasets")
    service.create_backup(output)

    with zipfile.ZipFile(output) as zf:
        assert "manifest.json" in zf.namelist()
        data = json.loads(zf.read("manifest.json"))
    assert data["version"] == 1
    assert "notes/my-note.md" in data["notes"]


def test_create_backup_includes_note_file_content(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    _write_note(notes_dir, "my-note", content="unique content 42")

    output = tmp_path / "backup.zip"
    service = BackupService(notes_dir, tmp_path / "datasets")
    service.create_backup(output)

    with zipfile.ZipFile(output) as zf:
        text = zf.read("notes/my-note.md").decode("utf-8")
    assert "unique content 42" in text


def test_create_backup_raw_dataset_bytes_unchanged(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()

    raw = b"col1,col2\n\x00\xff\nspecial bytes"
    sidecar = "id: ds\ntitle: DS\ncreated: 2026-04-30T00:00:00Z\nmodified: 2026-04-30T00:00:00Z\nformat: csv\npath: data.csv\n"
    _write_dataset(datasets_dir, "data.csv", raw, sidecar)

    output = tmp_path / "backup.zip"
    service = BackupService(notes_dir, datasets_dir)
    service.create_backup(output)

    with zipfile.ZipFile(output) as zf:
        extracted = zf.read("datasets/data.csv")
    assert extracted == raw


def test_create_backup_returns_manifest(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    _write_note(notes_dir, "note-a")

    output = tmp_path / "backup.zip"
    service = BackupService(notes_dir, tmp_path / "datasets")
    manifest = service.create_backup(output)

    assert isinstance(manifest, BackupManifest)
    assert manifest.version == 1
    assert "notes/note-a.md" in manifest.notes


# ---------------------------------------------------------------------------
# restore_backup
# ---------------------------------------------------------------------------


def _make_backup(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Helper: build a real zip with one note and one CSV dataset."""
    notes_dir = tmp_path / "src_notes"
    datasets_dir = tmp_path / "src_datasets"
    notes_dir.mkdir()
    datasets_dir.mkdir()

    _write_note(notes_dir, "restore-me", content="restored content")
    csv_bytes = b"a,b\n1,2\n"
    sidecar = "id: ds-restore\ntitle: Restore DS\ncreated: 2026-04-30T00:00:00Z\nmodified: 2026-04-30T00:00:00Z\nformat: csv\npath: restore.csv\n"
    _write_dataset(datasets_dir, "restore.csv", csv_bytes, sidecar)

    backup_zip = tmp_path / "backup.zip"
    BackupService(notes_dir, datasets_dir).create_backup(backup_zip)
    return backup_zip, notes_dir, datasets_dir


def test_restore_recreates_note_files(tmp_path: Path) -> None:
    backup_zip, _, _ = _make_backup(tmp_path)

    dest_notes = tmp_path / "dest_notes"
    dest_datasets = tmp_path / "dest_datasets"

    service = BackupService(dest_notes, dest_datasets)
    service.restore_backup(backup_zip, notes_dir=dest_notes, datasets_dir=dest_datasets)

    assert (dest_notes / "restore-me.md").exists()
    text = (dest_notes / "restore-me.md").read_text(encoding="utf-8")
    assert "restored content" in text


def test_restore_recreates_dataset_sidecar(tmp_path: Path) -> None:
    backup_zip, _, _ = _make_backup(tmp_path)

    dest_notes = tmp_path / "dest_notes"
    dest_datasets = tmp_path / "dest_datasets"

    service = BackupService(dest_notes, dest_datasets)
    service.restore_backup(backup_zip, notes_dir=dest_notes, datasets_dir=dest_datasets)

    assert (dest_datasets / "restore.csv.dataset.yml").exists()


def test_restore_raw_dataset_unchanged(tmp_path: Path) -> None:
    backup_zip, _, _ = _make_backup(tmp_path)

    dest_notes = tmp_path / "dest_notes"
    dest_datasets = tmp_path / "dest_datasets"

    service = BackupService(dest_notes, dest_datasets)
    service.restore_backup(backup_zip, notes_dir=dest_notes, datasets_dir=dest_datasets)

    restored_bytes = (dest_datasets / "restore.csv").read_bytes()
    assert restored_bytes == b"a,b\n1,2\n"


def test_restore_creates_dirs_if_missing(tmp_path: Path) -> None:
    backup_zip, _, _ = _make_backup(tmp_path)

    new_notes = tmp_path / "brand" / "new" / "notes"
    new_datasets = tmp_path / "brand" / "new" / "datasets"

    service = BackupService(new_notes, new_datasets)
    service.restore_backup(backup_zip, notes_dir=new_notes, datasets_dir=new_datasets)

    assert new_notes.is_dir()
    assert new_datasets.is_dir()


def test_restore_returns_manifest(tmp_path: Path) -> None:
    backup_zip, _, _ = _make_backup(tmp_path)

    dest_notes = tmp_path / "dest_notes"
    dest_datasets = tmp_path / "dest_datasets"

    service = BackupService(dest_notes, dest_datasets)
    manifest = service.restore_backup(backup_zip, notes_dir=dest_notes, datasets_dir=dest_datasets)

    assert isinstance(manifest, BackupManifest)
    assert "notes/restore-me.md" in manifest.notes


def test_restore_raises_if_backup_not_found(tmp_path: Path) -> None:
    service = BackupService(tmp_path / "notes", tmp_path / "datasets")
    with pytest.raises(FileNotFoundError):
        service.restore_backup(tmp_path / "missing.zip")


def test_restore_raises_if_no_manifest(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("notes/some-note.md", "content")

    service = BackupService(tmp_path / "notes", tmp_path / "datasets")
    with pytest.raises(ValueError, match="manifest.json"):
        service.restore_backup(bad_zip)


def test_restore_raises_on_path_traversal(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    manifest = {
        "version": 1,
        "created": "2026-04-30T00:00:00Z",
        "notes": ["../evil.md"],
        "datasets": [],
    }
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("../evil.md", "pwned")

    service = BackupService(tmp_path / "notes", tmp_path / "datasets")
    with pytest.raises(ValueError, match="traversal"):
        service.restore_backup(bad_zip)
