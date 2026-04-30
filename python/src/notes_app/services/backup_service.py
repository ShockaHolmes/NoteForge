"""Backup and restore service for notes and datasets.

Backup zip layout
-----------------
  manifest.json
  notes/<note-id>.md
  datasets/<data-filename>            (raw, unchanged)
  datasets/<data-filename>.dataset.yml

Manifest JSON schema (version 1)
---------------------------------
  {
    "version": 1,
    "created": "<ISO-8601 UTC>",
    "notes": ["notes/my-note.md", ...],
    "datasets": [
      {"sidecar": "datasets/sales.csv.dataset.yml", "data": "datasets/sales.csv"},
      {"sidecar": "datasets/meta-only.dataset.yml", "data": null}
    ]
  }
"""

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


_MANIFEST_FILENAME = "manifest.json"
_MANIFEST_VERSION = 1
_NOTES_PREFIX = "notes/"
_DATASETS_PREFIX = "datasets/"


@dataclass
class DatasetEntry:
    sidecar: str
    data: str | None


@dataclass
class BackupManifest:
    version: int
    created: str
    notes: list[str]
    datasets: list[DatasetEntry]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "created": self.created,
            "notes": self.notes,
            "datasets": [
                {"sidecar": e.sidecar, "data": e.data} for e in self.datasets
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "BackupManifest":
        version = int(data.get("version", 1))
        created = str(data.get("created", ""))
        notes = [str(n) for n in data.get("notes", [])]
        raw_datasets = data.get("datasets", [])
        datasets = [
            DatasetEntry(
                sidecar=str(d.get("sidecar", "")),
                data=str(d["data"]) if d.get("data") else None,
            )
            for d in raw_datasets
            if isinstance(d, dict)
        ]
        return cls(version=version, created=created, notes=notes, datasets=datasets)


class BackupService:
    """Creates and restores zip-based backups of notes and datasets."""

    def __init__(self, notes_dir: Path, datasets_dir: Path) -> None:
        self._notes_dir = notes_dir
        self._datasets_dir = datasets_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_manifest(self) -> BackupManifest:
        """Scan the notes and datasets directories and return a manifest."""
        note_entries = self._collect_note_entries()
        dataset_entries = self._collect_dataset_entries()
        return BackupManifest(
            version=_MANIFEST_VERSION,
            created=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            notes=note_entries,
            datasets=dataset_entries,
        )

    def create_backup(self, output_path: Path) -> BackupManifest:
        """Write a zip backup to *output_path* and return the manifest.

        The raw dataset files are copied byte-for-byte without modification.
        """
        manifest = self.build_manifest()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write manifest first
            zf.writestr(_MANIFEST_FILENAME, json.dumps(manifest.to_dict(), indent=2))

            # Write note files
            for archive_name in manifest.notes:
                note_filename = Path(archive_name).name
                source = self._notes_dir / note_filename
                if source.exists():
                    zf.write(source, arcname=archive_name)

            # Write dataset sidecars and raw data files
            for entry in manifest.datasets:
                sidecar_filename = Path(entry.sidecar).name
                sidecar_source = self._datasets_dir / sidecar_filename
                if sidecar_source.exists():
                    zf.write(sidecar_source, arcname=entry.sidecar)

                if entry.data is not None:
                    data_filename = Path(entry.data).name
                    data_source = self._datasets_dir / data_filename
                    if data_source.exists():
                        # Write raw bytes unchanged
                        zf.write(data_source, arcname=entry.data)

        return manifest

    def restore_backup(
        self,
        backup_path: Path,
        notes_dir: Path | None = None,
        datasets_dir: Path | None = None,
    ) -> BackupManifest:
        """Extract *backup_path* into notes/datasets directories.

        Recreates the expected folder structure. Raw dataset files are
        written without modification. Existing files are overwritten.

        Args:
            backup_path: Path to the zip backup file.
            notes_dir: Override destination for notes (defaults to self._notes_dir).
            datasets_dir: Override destination for datasets (defaults to self._datasets_dir).

        Returns:
            The manifest that was stored in the backup.

        Raises:
            ValueError: If the zip has no manifest or contains unsafe paths.
            FileNotFoundError: If *backup_path* does not exist.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        target_notes = notes_dir or self._notes_dir
        target_datasets = datasets_dir or self._datasets_dir

        with zipfile.ZipFile(backup_path, "r") as zf:
            names = set(zf.namelist())

            if _MANIFEST_FILENAME not in names:
                raise ValueError(
                    f"Backup '{backup_path.name}' has no '{_MANIFEST_FILENAME}'."
                )

            manifest_text = zf.read(_MANIFEST_FILENAME).decode("utf-8")
            manifest = BackupManifest.from_dict(json.loads(manifest_text))

            self._validate_manifest_paths(manifest)

            target_notes.mkdir(parents=True, exist_ok=True)
            target_datasets.mkdir(parents=True, exist_ok=True)

            # Restore note files
            for archive_name in manifest.notes:
                if archive_name not in names:
                    continue
                dest = target_notes / Path(archive_name).name
                dest.write_bytes(zf.read(archive_name))

            # Restore dataset sidecars and raw data files
            for entry in manifest.datasets:
                if entry.sidecar in names:
                    dest = target_datasets / Path(entry.sidecar).name
                    dest.write_bytes(zf.read(entry.sidecar))

                if entry.data is not None and entry.data in names:
                    dest = target_datasets / Path(entry.data).name
                    # Write raw bytes unchanged — never rewrite the source
                    dest.write_bytes(zf.read(entry.data))

        return manifest

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_note_entries(self) -> list[str]:
        if not self._notes_dir.exists():
            return []
        return [
            f"{_NOTES_PREFIX}{p.name}"
            for p in sorted(self._notes_dir.glob("*.md"))
        ]

    def _collect_dataset_entries(self) -> list[DatasetEntry]:
        if not self._datasets_dir.exists():
            return []

        entries: list[DatasetEntry] = []
        for sidecar in sorted(self._datasets_dir.glob("*.dataset.yml")):
            archive_sidecar = f"{_DATASETS_PREFIX}{sidecar.name}"

            # The data filename is everything before ".dataset.yml"
            # e.g.  sales.csv.dataset.yml → sales.csv
            #        meta-only.dataset.yml → no data file expected
            stem = sidecar.name[: -len(".dataset.yml")]  # strip ".dataset.yml"
            data_path = self._datasets_dir / stem
            if data_path.exists() and data_path.suffix.lower() in (".csv", ".json"):
                archive_data: str | None = f"{_DATASETS_PREFIX}{data_path.name}"
            else:
                archive_data = None

            entries.append(DatasetEntry(sidecar=archive_sidecar, data=archive_data))

        return entries

    @staticmethod
    def _validate_manifest_paths(manifest: BackupManifest) -> None:
        """Raise ValueError if any path looks like a traversal attempt."""
        all_paths: list[str] = list(manifest.notes)
        for entry in manifest.datasets:
            all_paths.append(entry.sidecar)
            if entry.data is not None:
                all_paths.append(entry.data)

        for path_str in all_paths:
            p = PurePosixPath(path_str)
            if p.is_absolute():
                raise ValueError(
                    f"Unsafe path in backup manifest (absolute): '{path_str}'"
                )
            if any(part == ".." for part in p.parts):
                raise ValueError(
                    f"Unsafe path in backup manifest (traversal): '{path_str}'"
                )
