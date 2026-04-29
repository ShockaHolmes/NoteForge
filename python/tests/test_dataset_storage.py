"""Tests for dataset metadata, repository, and service behavior."""

from datetime import datetime, timezone
import time
from typing import Callable
import yaml
from pathlib import Path

import pytest
import notes_app.services.dataset_service as dataset_service_module

from notes_app.models.dataset import Dataset
from notes_app.models.dataset import DatasetSchemaField
from notes_app.models.dataset_metadata import DatasetMetadata
from notes_app.repositories.file_dataset_repository import FileDatasetRepository
from notes_app.services.dataset_service import DatasetService


def test_dataset_metadata_to_yaml_and_from_yaml_round_trip() -> None:
    metadata = DatasetMetadata(
        id="ds-sales",
        title="Sales Q1",
        author="Alice",
        created=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
        modified=datetime(2026, 4, 29, 11, 0, tzinfo=timezone.utc),
        tags=("finance", "quarterly"),
        format="csv",
        path="sales/q1.csv",
        row_count=15230,
        schema=(DatasetSchemaField(name="amount", type="number", nullable=False),),
    )

    text = metadata.to_yaml()
    loaded = DatasetMetadata.from_yaml(text)

    parsed = yaml.safe_load(text)
    assert parsed["id"] == "ds-sales"
    assert parsed["title"] == "Sales Q1"
    assert parsed["author"] == "Alice"
    assert parsed["format"] == "csv"
    assert parsed["path"] == "sales/q1.csv"
    assert parsed["rowCount"] == 15230
    assert parsed["schema"][0]["name"] == "amount"
    assert loaded == metadata


def test_dataset_metadata_converts_to_and_from_dataset() -> None:
    dataset = Dataset.create("ds-json", "JSON Data", author="Bob", tags=("api",))
    dataset = Dataset(
        id=dataset.id,
        title=dataset.title,
        author=dataset.author,
        created=dataset.created,
        modified=dataset.modified,
        tags=dataset.tags,
        format="json",
        path="imports/data.json",
        row_count=5,
        schema_fields=(DatasetSchemaField(name="id", type="integer", nullable=False),),
    )

    metadata = DatasetMetadata.from_dataset(dataset)
    reconstructed = metadata.to_dataset()

    assert metadata.path == "imports/data.json"
    assert reconstructed.path == "imports/data.json"
    assert reconstructed.row_count == 5
    assert reconstructed.schema_fields[0].name == "id"


def test_dataset_metadata_rejects_non_relative_path() -> None:
    with pytest.raises(ValueError, match="relative to the datasets folder"):
        DatasetMetadata.from_dict(
            {
                "id": "ds-bad",
                "title": "Bad",
                "created": "2026-04-29T10:00:00Z",
                "modified": "2026-04-29T11:00:00Z",
                "path": "../escape.csv",
            }
        )


# ---------------------------------------------------------------------------
# FileDatasetRepository — metadata-only (no data file)
# ---------------------------------------------------------------------------

def test_repository_creates_datasets_dir_automatically(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "datasets"
    FileDatasetRepository(nested)
    assert nested.is_dir()


def test_repository_save_writes_sidecar(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-sales", "Sales Q1", author="Alice", tags=("finance",))
    repo.save(dataset)

    sidecars = list(tmp_path.glob("*.dataset.yml"))
    assert len(sidecars) == 1

    raw = sidecars[0].read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    assert data["id"] == "ds-sales"
    assert data["assetType"] == "dataset"
    assert data["title"] == "Sales Q1"
    assert data["author"] == "Alice"
    assert "finance" in data["tags"]


def test_repository_list_all_returns_saved_datasets(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    repo.save(Dataset.create("ds-a", "Alpha"))
    repo.save(Dataset.create("ds-b", "Beta"))

    results = list(repo.list_all())
    assert len(results) == 2
    assert {d.id for d in results} == {"ds-a", "ds-b"}


def test_repository_get_by_id_returns_correct_dataset(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    repo.save(Dataset.create("ds-a", "Alpha"))
    repo.save(Dataset.create("ds-b", "Beta"))

    found = repo.get_by_id("ds-b")
    assert found is not None
    assert found.title == "Beta"


def test_repository_get_by_id_returns_none_for_missing(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    assert repo.get_by_id("nope") is None


def test_repository_delete_removes_sidecar(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    repo.save(Dataset.create("ds-a", "Alpha"))

    deleted = repo.delete_by_id("ds-a")
    assert deleted is True
    assert list(tmp_path.glob("*.dataset.yml")) == []


def test_repository_delete_returns_false_for_missing(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    assert repo.delete_by_id("ghost") is False


# ---------------------------------------------------------------------------
# FileDatasetRepository.save_with_file
# ---------------------------------------------------------------------------

def test_save_with_file_stores_csv_unchanged(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-csv", "CSV Dataset")
    csv_bytes = b"id,name\n1,Alice\n2,Bob\n"

    updated = repo.save_with_file(dataset, csv_bytes, "data.csv")

    # Data file written unchanged
    assert (tmp_path / "data.csv").read_bytes() == csv_bytes

    # Sidecar exists
    sidecar_path = tmp_path / "data.csv.dataset.yml"
    assert sidecar_path.exists()

    data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
    assert data["path"] == "data.csv"
    assert data["sizeBytes"] == len(csv_bytes)
    assert data["format"] == "csv"

    # Returned dataset has updated fields
    assert updated.path == "data.csv"
    assert updated.size_bytes == len(csv_bytes)
    assert updated.format == "csv"
    assert updated.row_count == 2
    assert updated.column_count == 2
    assert [field.name for field in updated.schema_fields] == ["id", "name"]


def test_save_with_file_stores_relative_path_only(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-nested", "Nested Upload")

    updated = repo.save_with_file(dataset, b"a,b\n1,2\n", "nested/source.csv")

    assert updated.path == "source.csv"
    sidecar = yaml.safe_load((tmp_path / "source.csv.dataset.yml").read_text(encoding="utf-8"))
    assert sidecar["path"] == "source.csv"


def test_save_with_file_stores_json_unchanged(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-json", "JSON Dataset")
    json_bytes = b'[{"id": 1, "name": "Alice"}]'

    updated = repo.save_with_file(dataset, json_bytes, "records.json")

    assert (tmp_path / "records.json").read_bytes() == json_bytes
    assert updated.format == "json"
    assert updated.row_count == 1
    assert updated.column_count == 2
    assert [field.name for field in updated.schema_fields] == ["id", "name"]


def test_save_with_file_inspects_json_array_fields(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-json-array", "JSON Array Dataset")
    json_bytes = b'[{"id": 1, "name": "Alice"}, {"id": 2, "email": "b@example.com"}]'

    updated = repo.save_with_file(dataset, json_bytes, "users.json")

    assert updated.row_count == 2
    assert updated.column_count == 3
    assert [field.name for field in updated.schema_fields] == ["id", "name", "email"]

    sidecar = yaml.safe_load((tmp_path / "users.json.dataset.yml").read_text(encoding="utf-8"))
    assert sidecar["rowCount"] == 2
    assert sidecar["columnCount"] == 3
    assert [field["name"] for field in sidecar["schema"]] == ["id", "name", "email"]


def test_save_with_file_inspects_json_object_fields(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-json-object", "JSON Object Dataset")
    json_bytes = b'{"dataset": "sales", "year": 2026, "active": true}'

    updated = repo.save_with_file(dataset, json_bytes, "summary.json")

    assert updated.row_count == 1
    assert updated.column_count == 3
    assert [field.name for field in updated.schema_fields] == ["dataset", "year", "active"]


def test_save_with_file_invalid_json_returns_clear_error(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-invalid-json", "Invalid JSON")
    invalid_json = b'{"id": 1, "name": "Alice"'

    with pytest.raises(ValueError, match="Invalid JSON file"):
        repo.save_with_file(dataset, invalid_json, "broken.json")


def test_save_with_file_inspects_csv_columns_and_row_count(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-report", "Report")
    csv_bytes = b"order_id,amount,order_date\n1,5.0,2026-01-01\n2,9.1,2026-01-02\n"

    updated = repo.save_with_file(dataset, csv_bytes, "report.csv")

    assert updated.row_count == 2
    assert updated.column_count == 3
    assert [field.name for field in updated.schema_fields] == [
        "order_id",
        "amount",
        "order_date",
    ]

    sidecar = yaml.safe_load((tmp_path / "report.csv.dataset.yml").read_text(encoding="utf-8"))
    assert sidecar["rowCount"] == 2
    assert sidecar["columnCount"] == 3
    assert [field["name"] for field in sidecar["schema"]] == [
        "order_id",
        "amount",
        "order_date",
    ]


def test_save_with_file_csv_decode_error_is_clear(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-bad-encoding", "Bad Encoding")
    invalid_utf8_csv = b"id,name\n1,\xff\n"

    with pytest.raises(ValueError, match="not valid UTF-8"):
        repo.save_with_file(dataset, invalid_utf8_csv, "bad.csv")


def test_save_with_file_rejects_unsupported_extension(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-x", "Bad File")

    with pytest.raises(ValueError, match="Unsupported file type"):
        repo.save_with_file(dataset, b"data", "file.parquet")


def test_delete_removes_data_file_and_sidecar(tmp_path: Path) -> None:
    repo = FileDatasetRepository(tmp_path)
    dataset = Dataset.create("ds-del", "Delete Me")
    repo.save_with_file(dataset, b"a,b\n1,2\n", "removeme.csv")

    deleted = repo.delete_by_id("ds-del")
    assert deleted is True
    assert not (tmp_path / "removeme.csv").exists()
    assert not (tmp_path / "removeme.csv.dataset.yml").exists()


# ---------------------------------------------------------------------------
# DatasetService
# ---------------------------------------------------------------------------

def test_service_create_metadata_only(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    dataset = service.create_dataset("Sales Report", author="Bob", tags=("finance",))

    assert dataset.id == "sales-report"
    assert dataset.title == "Sales Report"
    assert dataset.author == "Bob"
    assert "finance" in dataset.tags
    assert dataset.path == ""  # no file uploaded


def test_service_create_with_file(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    csv_bytes = b"x,y\n1,2\n"
    dataset = service.create_dataset(
        "My Data", file_bytes=csv_bytes, original_filename="mydata.csv"
    )

    assert dataset.path == "mydata.csv"
    assert dataset.size_bytes == len(csv_bytes)
    assert (tmp_path / "mydata.csv").read_bytes() == csv_bytes


def test_service_list_datasets(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    service.create_dataset("First")
    service.create_dataset("Second")

    all_datasets = service.list_datasets()
    assert len(all_datasets) == 2
    assert {d.title for d in all_datasets} == {"First", "Second"}


def test_service_get_dataset(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    created = service.create_dataset("Find Me")

    found = service.get_dataset(created.id)
    assert found is not None
    assert found.title == "Find Me"


def test_service_get_dataset_missing(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    assert service.get_dataset("does-not-exist") is None


def test_service_update_dataset(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    created = service.create_dataset("Original", tags=("old",))

    updated = service.update_dataset(
        created.id, title="Updated Title", tags=("new", "tag")
    )
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.tags == ("new", "tag")
    assert updated.created == created.created
    assert updated.modified > created.modified


def test_service_update_dataset_missing(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    assert service.update_dataset("ghost", title="X") is None


def test_service_delete_dataset(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    created = service.create_dataset("To Delete")

    deleted = service.delete_dataset(created.id)
    assert deleted is not None
    assert deleted.id == created.id
    assert service.get_dataset(created.id) is None


def test_service_delete_dataset_missing(tmp_path: Path) -> None:
    service = DatasetService(FileDatasetRepository(tmp_path))
    assert service.delete_dataset("nope") is None


def test_sidecar_yaml_is_valid_and_round_trips(tmp_path: Path) -> None:
    """Sidecar YAML must be parseable and survive a round-trip."""
    service = DatasetService(FileDatasetRepository(tmp_path))
    csv_bytes = b"col1,col2\nval1,val2\n"
    dataset = service.create_dataset(
        "Round Trip",
        author="Tester",
        tags=("a", "b"),
        file_bytes=csv_bytes,
        original_filename="roundtrip.csv",
    )

    sidecar_path = tmp_path / "roundtrip.csv.dataset.yml"
    raw = sidecar_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    required_keys = {"id", "assetType", "title", "author", "created", "modified", "tags"}
    assert required_keys.issubset(data.keys())
    assert data["assetType"] == "dataset"
    assert data["id"] == dataset.id
    assert isinstance(data["tags"], list)
    assert data["created"] is not None
    assert data["modified"] is not None


class _FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[
            tuple[Callable[..., object], tuple[object, ...], dict[str, object]]
        ] = []

    def submit(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))
        return object()


def test_service_create_with_file_enqueues_async_profile_without_blocking(
    tmp_path: Path, monkeypatch
) -> None:
    repo = FileDatasetRepository(tmp_path)
    service = DatasetService(repo)
    fake_executor = _FakeExecutor()
    monkeypatch.setattr(dataset_service_module, "_PROFILE_EXECUTOR", fake_executor)

    started = time.perf_counter()
    dataset = service.create_dataset(
        "Async Profile",
        file_bytes=b"id,name\n1,Alice\n2,Bob\n",
        original_filename="async.csv",
    )
    elapsed = time.perf_counter() - started

    assert dataset.path == "async.csv"
    assert elapsed < 0.5
    assert len(fake_executor.calls) == 1
    _, args, _ = fake_executor.calls[0]
    assert args == (dataset.id,)


def test_async_profile_job_persists_profile_into_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    repo = FileDatasetRepository(tmp_path)
    service = DatasetService(repo)
    fake_executor = _FakeExecutor()
    monkeypatch.setattr(dataset_service_module, "_PROFILE_EXECUTOR", fake_executor)

    dataset = service.create_dataset(
        "Profile Save",
        file_bytes=b"id,amount\n1,10.5\n2,20.0\n",
        original_filename="profile-save.csv",
    )
    assert len(fake_executor.calls) == 1

    fn, args, kwargs = fake_executor.calls[0]
    fn(*args, **kwargs)

    sidecar_path = tmp_path / "profile-save.csv.dataset.yml"
    sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar.get("profile") is not None
    assert sidecar["profile"]["rowCount"] == 2
    assert sidecar["profile"]["source"] in ("computed", "sidecar")

    # Original raw file remains intact
    assert (tmp_path / "profile-save.csv").read_bytes() == b"id,amount\n1,10.5\n2,20.0\n"
    assert dataset.id == "profile-save"


def test_failed_async_profile_job_does_not_delete_dataset_files(
    tmp_path: Path, monkeypatch
) -> None:
    repo = FileDatasetRepository(tmp_path)
    service = DatasetService(repo)
    fake_executor = _FakeExecutor()
    monkeypatch.setattr(dataset_service_module, "_PROFILE_EXECUTOR", fake_executor)

    dataset = service.create_dataset(
        "Profile Failure",
        file_bytes=b"id\n1\n",
        original_filename="profile-failure.csv",
    )

    raw_path = tmp_path / "profile-failure.csv"
    sidecar_path = tmp_path / "profile-failure.csv.dataset.yml"
    assert raw_path.exists()
    assert sidecar_path.exists()

    def _boom(_dataset):
        raise RuntimeError("profiling exploded")

    monkeypatch.setattr(repo, "profile", _boom)

    fn, args, kwargs = fake_executor.calls[0]
    fn(*args, **kwargs)

    assert raw_path.exists()
    assert sidecar_path.exists()
    assert dataset.id == "profile-failure"
