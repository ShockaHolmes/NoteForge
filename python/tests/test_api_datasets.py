from pathlib import Path

import yaml
from fastapi.testclient import TestClient
import notes_app.services.dataset_service as dataset_service_module

from notes_app.api.app import create_app


def test_post_api_datasets_uploads_csv_and_creates_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    csv_bytes = b"id,name\n1,Alice\n2,Bob\n"
    response = client.post(
        "/api/datasets",
        data={"title": "Team Roster", "author": "QA", "tags": "people,csv"},
        files={"file": ("team.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == "team-roster"
    assert payload["metadata"]["title"] == "Team Roster"
    assert payload["metadata"]["format"] == "csv"
    assert payload["metadata"]["path"] == "team.csv"
    assert payload["metadata"]["rowCount"] == 2
    assert payload["metadata"]["columnCount"] == 2

    raw_path = datasets_dir / "team.csv"
    sidecar_path = datasets_dir / "team.csv.dataset.yml"

    assert raw_path.read_bytes() == csv_bytes
    assert sidecar_path.exists()

    sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["id"] == payload["id"]
    assert sidecar["path"] == "team.csv"
    assert sidecar["rowCount"] == 2
    assert sidecar["schema"][0]["name"] == "id"


def test_post_api_datasets_uploads_json_and_creates_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    json_bytes = b'[{"id": 1, "name": "Alice"}, {"id": 2, "email": "b@example.com"}]'
    response = client.post(
        "/api/datasets",
        data={"title": "Users Export", "tags": "users,json"},
        files={"file": ("users.json", json_bytes, "application/json")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == "users-export"
    assert payload["metadata"]["format"] == "json"
    assert payload["metadata"]["path"] == "users.json"
    assert payload["metadata"]["rowCount"] == 2
    assert payload["metadata"]["columnCount"] == 3

    raw_path = datasets_dir / "users.json"
    sidecar_path = datasets_dir / "users.json.dataset.yml"

    assert raw_path.read_bytes() == json_bytes
    assert sidecar_path.exists()


def test_post_api_datasets_invalid_json_returns_clear_error(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    invalid_json = b'{"id": 1, "name": "Alice"'
    response = client.post(
        "/api/datasets",
        data={"title": "Broken JSON"},
        files={"file": ("broken.json", invalid_json, "application/json")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON file. Please upload valid JSON."


def test_get_api_datasets_returns_metadata_records(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    csv_bytes = b"order_id,amount\n1,10.0\n2,20.0\n"
    upload = client.post(
        "/api/datasets",
        data={"title": "Orders", "tags": "sales,finance"},
        files={"file": ("orders.csv", csv_bytes, "text/csv")},
    )
    assert upload.status_code == 201
    created_id = upload.json()["id"]

    response = client.get("/api/datasets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1

    dataset = payload[0]
    assert dataset["id"] == created_id
    assert dataset["title"] == "Orders"
    assert dataset["format"] == "csv"
    assert dataset["rowCount"] == 2
    assert dataset["modified"] is not None
    assert dataset["tags"] == ["sales", "finance"]


def test_get_api_datasets_skips_broken_sidecars_safely(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    # Create one valid dataset via API
    valid = client.post(
        "/api/datasets",
        data={"title": "Valid Dataset"},
        files={"file": ("valid.csv", b"id\n1\n", "text/csv")},
    )
    assert valid.status_code == 201
    valid_id = valid.json()["id"]

    # Add a broken sidecar and an orphan raw file directly on disk
    datasets_dir.mkdir(parents=True, exist_ok=True)
    (datasets_dir / "broken.dataset.yml").write_text("id: broken\n: invalid\n", encoding="utf-8")
    (datasets_dir / "orphan.csv").write_bytes(b"a,b\n1,2\n")

    response = client.get("/api/datasets")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [valid_id]


def test_delete_api_datasets_removes_raw_file_and_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    csv_bytes = b"id,name\n1,Alice\n2,Bob\n"
    created = client.post(
        "/api/datasets",
        data={"title": "Delete Target"},
        files={"file": ("delete-target.csv", csv_bytes, "text/csv")},
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    raw_path = datasets_dir / "delete-target.csv"
    sidecar_path = datasets_dir / "delete-target.csv.dataset.yml"
    assert raw_path.exists()
    assert sidecar_path.exists()

    response = client.delete(f"/api/datasets/{dataset_id}")

    assert response.status_code == 204
    assert not raw_path.exists()
    assert not sidecar_path.exists()


def test_delete_api_datasets_missing_id_returns_404(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    response = client.delete("/api/datasets/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset 'does-not-exist' not found."


def test_get_api_datasets_preview_csv_respects_limit(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "Preview CSV"},
        files={
            "file": (
                "preview.csv",
                b"id,name\n1,Alice\n2,Bob\n3,Carol\n",
                "text/csv",
            )
        },
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    response = client.get(f"/api/datasets/{dataset_id}/preview?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == dataset_id
    assert payload["format"] == "csv"
    assert payload["limit"] == 2
    assert payload["headers"] == ["id", "name"]
    assert payload["rows"] == [["1", "Alice"], ["2", "Bob"]]
    assert payload["records"] is None


def test_get_api_datasets_preview_json_array_returns_sample_records(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "Preview JSON Array"},
        files={
            "file": (
                "preview-array.json",
                b'[{"id":1,"name":"A"},{"id":2,"name":"B"},{"id":3,"name":"C"}]',
                "application/json",
            )
        },
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    response = client.get(f"/api/datasets/{dataset_id}/preview?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == dataset_id
    assert payload["format"] == "json"
    assert payload["limit"] == 2
    assert payload["records"] == [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    assert payload["headers"] is None
    assert payload["rows"] is None


def test_get_api_datasets_preview_json_object_returns_single_record(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "Preview JSON Object"},
        files={
            "file": (
                "preview-object.json",
                b'{"id": 42, "name": "One"}',
                "application/json",
            )
        },
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    response = client.get(f"/api/datasets/{dataset_id}/preview?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["records"] == [{"id": 42, "name": "One"}]


def test_get_api_datasets_preview_missing_dataset_returns_404(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    response = client.get("/api/datasets/does-not-exist/preview?limit=2")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset 'does-not-exist' not found."


def test_get_api_datasets_profile_csv_returns_types_and_stats(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "CSV Profile"},
        files={
            "file": (
                "profile.csv",
                b"id,amount,name\n1,10.5,Alice\n2,,Bob\n3,7.0,\n",
                "text/csv",
            )
        },
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    response = client.get(f"/api/datasets/{dataset_id}/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == dataset_id
    assert payload["format"] == "csv"
    assert payload["source"] == "computed"
    assert payload["rowCount"] == 3

    columns = {col["name"]: col for col in payload["columns"]}
    assert columns["id"]["inferredType"] in ("integer", "number")
    assert columns["id"]["missingValues"] == 0
    assert columns["amount"]["inferredType"] == "number"
    assert columns["amount"]["missingValues"] == 1
    assert columns["name"]["inferredType"] == "string"
    assert columns["name"]["missingValues"] == 1


def test_get_api_datasets_profile_json_returns_types_and_stats(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "JSON Profile"},
        files={
            "file": (
                "profile.json",
                b'[{"id":1,"active":true,"name":"A"},{"id":2,"name":"B"},{"id":3,"active":false,"name":null}]',
                "application/json",
            )
        },
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    response = client.get(f"/api/datasets/{dataset_id}/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "json"
    assert payload["rowCount"] == 3
    columns = {col["name"]: col for col in payload["columns"]}
    assert columns["id"]["inferredType"] in ("integer", "number")
    assert columns["id"]["missingValues"] == 0
    assert columns["active"]["inferredType"] == "boolean"
    assert columns["active"]["missingValues"] == 1
    assert columns["name"]["inferredType"] == "string"
    assert columns["name"]["missingValues"] == 1


def test_get_api_datasets_profile_uses_sidecar_profile_when_available(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))
    monkeypatch.setattr(
        dataset_service_module.DatasetService,
        "_enqueue_profile_job",
        lambda self, _dataset_id: None,
    )

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "Sidecar Profile"},
        files={"file": ("sidecar.csv", b"id\n1\n", "text/csv")},
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    sidecar_path = datasets_dir / "sidecar.csv.dataset.yml"
    sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    sidecar["profile"] = {
        "source": "sidecar",
        "rowCount": 999,
        "columns": [
            {"name": "id", "inferredType": "integer", "missingValues": 123}
        ],
    }
    sidecar_path.write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")

    response = client.get(f"/api/datasets/{dataset_id}/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "sidecar"
    assert payload["rowCount"] == 999
    assert payload["columns"] == [
        {"name": "id", "inferredType": "integer", "missingValues": 123}
    ]


def test_get_api_datasets_profile_missing_dataset_returns_404(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    response = client.get("/api/datasets/does-not-exist/profile")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset 'does-not-exist' not found."


def test_viewer_role_cannot_upload_or_delete_dataset(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)

    upload = client.post(
        "/api/datasets",
        headers={"X-Role": "viewer"},
        data={"title": "Viewer Upload"},
        files={"file": ("viewer.csv", b"id\n1\n", "text/csv")},
    )
    assert upload.status_code == 403

    delete = client.delete("/api/datasets/any-id", headers={"X-Role": "viewer"})
    assert delete.status_code == 403


def test_viewer_role_can_read_and_preview_dataset(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)

    created = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Readable Dataset"},
        files={"file": ("readable.csv", b"id,name\n1,Alice\n", "text/csv")},
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    list_response = client.get("/api/datasets", headers={"X-Role": "viewer"})
    assert list_response.status_code == 200

    get_response = client.get(f"/api/datasets/{dataset_id}", headers={"X-Role": "viewer"})
    assert get_response.status_code == 200

    preview_response = client.get(
        f"/api/datasets/{dataset_id}/preview?limit=1",
        headers={"X-Role": "viewer"},
    )
    assert preview_response.status_code == 200
