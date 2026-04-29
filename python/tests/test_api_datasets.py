from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from notes_app.api.app import create_app


def test_post_api_datasets_uploads_csv_and_creates_sidecar(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)

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

    invalid_json = b'{"id": 1, "name": "Alice"'
    response = client.post(
        "/api/datasets",
        data={"title": "Broken JSON"},
        files={"file": ("broken.json", invalid_json, "application/json")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON file. Please upload valid JSON."


def test_get_api_datasets_returns_metadata_records(
    tmp_path: Path, monkeypatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)

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
