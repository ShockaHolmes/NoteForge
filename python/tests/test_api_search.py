from pathlib import Path

from fastapi.testclient import TestClient

from notes_app.api.app import create_app


def test_search_returns_matching_notes_and_datasets_with_asset_type(
    tmp_path: Path, monkeypatch
) -> None:
    notes_dir = tmp_path / "notes"
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("NOTES_HOME", str(notes_dir))
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    note_resp = client.post(
        "/api/notes",
        json={
            "title": "Forecast Planning",
            "content": "Quarterly demand forecast for finance team.",
            "tags": ["finance", "planning"],
        },
    )
    assert note_resp.status_code == 201

    dataset_resp = client.post(
        "/api/datasets",
        data={"title": "Finance Export", "tags": "finance,warehouse"},
        files={
            "file": (
                "finance.csv",
                b"account_id,revenue\n1,120.5\n2,99.9\n",
                "text/csv",
            )
        },
    )
    assert dataset_resp.status_code == 201

    search_resp = client.get("/api/search?q=finance")

    assert search_resp.status_code == 200
    payload = search_resp.json()
    asset_types = {item["assetType"] for item in payload}
    assert "note" in asset_types
    assert "dataset" in asset_types


def test_search_notes_covers_title_tags_metadata_and_body(
    tmp_path: Path, monkeypatch
) -> None:
    notes_dir = tmp_path / "notes"
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("NOTES_HOME", str(notes_dir))
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/notes",
        json={
            "title": "Roadmap Alpha",
            "content": "Body has unique-body-token for matching.",
            "tags": ["unique-tag-token"],
        },
    )
    assert create.status_code == 201
    note_id = create.json()["id"]

    by_title = client.get("/api/search?q=roadmap")
    assert by_title.status_code == 200
    assert any(item["assetType"] == "note" for item in by_title.json())

    by_tag = client.get("/api/search?q=unique-tag-token")
    assert by_tag.status_code == 200
    assert any(item["assetType"] == "note" for item in by_tag.json())

    by_body = client.get("/api/search?q=unique-body-token")
    assert by_body.status_code == 200
    assert any(item["assetType"] == "note" for item in by_body.json())

    by_metadata = client.get(f"/api/search?q={note_id}")
    assert by_metadata.status_code == 200
    assert any(item["assetType"] == "note" for item in by_metadata.json())


def test_search_datasets_covers_title_tags_schema_and_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    notes_dir = tmp_path / "notes"
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("NOTES_HOME", str(notes_dir))
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))

    app = create_app()
    client = TestClient(app)
    client.headers.update({"X-Role": "data-engineer"})

    create = client.post(
        "/api/datasets",
        data={"title": "Sales Ledger", "tags": "ops,unique-dataset-tag"},
        files={
            "file": (
                "ledger.csv",
                b"customer_ref,amount\nA1,50\nA2,75\n",
                "text/csv",
            )
        },
    )
    assert create.status_code == 201
    dataset_id = create.json()["id"]

    by_title = client.get("/api/search?q=ledger")
    assert by_title.status_code == 200
    assert any(item["assetType"] == "dataset" for item in by_title.json())

    by_tag = client.get("/api/search?q=unique-dataset-tag")
    assert by_tag.status_code == 200
    assert any(item["assetType"] == "dataset" for item in by_tag.json())

    by_schema = client.get("/api/search?q=customer_ref")
    assert by_schema.status_code == 200
    assert any(item["assetType"] == "dataset" for item in by_schema.json())

    by_metadata = client.get(f"/api/search?q={dataset_id}")
    assert by_metadata.status_code == 200
    assert any(item["assetType"] == "dataset" for item in by_metadata.json())
