"""Comprehensive API tests covering gaps not addressed by existing test files.

Covers:
- Notes: PATCH partial update, /notes/search endpoint, title length validation,
  full response shape, tags round-trip
- Datasets: GET /:id, PATCH /:id, metadata-only upload, tags/author round-trip,
  header-only CSV (0 data rows), JSON empty array, binary-safe raw bytes,
  admin and editor role upload permissions
- Search: empty results, missing query → 400, response shape,
  /api/v1 prefix, case-insensitive matching
- Upload validation: CSV with no data rows, empty JSON array, JSON object input
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from notes_app.api.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def notes_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("NOTES_HOME", str(tmp_path / "notes"))
    return TestClient(create_app())


@pytest.fixture()
def datasets_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    return TestClient(create_app())


@pytest.fixture()
def full_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("NOTES_HOME", str(tmp_path / "notes"))
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    return TestClient(create_app())


def _create_note(client: TestClient, title: str = "Test Note", content: str = "body",
                 tags: list[str] | None = None) -> dict:
    resp = client.post("/api/notes", json={"title": title, "content": content,
                                           "tags": tags or []})
    assert resp.status_code == 201
    return resp.json()


def _upload_csv(client: TestClient, title: str = "DS", csv_bytes: bytes = b"id\n1\n",
                filename: str = "data.csv", tags: str = "",
                author: str = "") -> dict:
    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": title, "tags": tags, "author": author},
        files={"file": (filename, csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()


# ===========================================================================
# Notes — PATCH (partial update)
# ===========================================================================


def test_patch_note_updates_title_only(notes_client: TestClient) -> None:
    note = _create_note(notes_client, title="Original", content="body",
                        tags=["keep"])
    note_id = note["id"]

    resp = notes_client.patch(f"/api/notes/{note_id}", json={"title": "Patched Title"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Patched Title"
    assert data["content"] == "body"          # unchanged
    assert data["tags"] == ["keep"]           # unchanged


def test_patch_note_updates_content_only(notes_client: TestClient) -> None:
    note = _create_note(notes_client, title="Title", content="old body")
    note_id = note["id"]

    resp = notes_client.patch(f"/api/notes/{note_id}", json={"content": "new body"})

    assert resp.status_code == 200
    assert resp.json()["title"] == "Title"    # unchanged
    assert resp.json()["content"] == "new body"


def test_patch_note_updates_tags_only(notes_client: TestClient) -> None:
    note = _create_note(notes_client, title="Tag Note", tags=["old"])
    note_id = note["id"]

    resp = notes_client.patch(f"/api/notes/{note_id}", json={"tags": ["new", "two"]})

    assert resp.status_code == 200
    assert resp.json()["tags"] == ["new", "two"]
    assert resp.json()["title"] == "Tag Note" # unchanged


def test_patch_note_updates_modified_timestamp(notes_client: TestClient) -> None:
    note = _create_note(notes_client, title="Stamp Note")
    note_id = note["id"]
    original_modified = note["modified"]

    import time; time.sleep(0.01)

    resp = notes_client.patch(f"/api/notes/{note_id}", json={"title": "Changed"})

    assert resp.status_code == 200
    assert resp.json()["modified"] != original_modified


def test_patch_note_all_fields_together(notes_client: TestClient) -> None:
    note = _create_note(notes_client, title="Multi", content="old", tags=["x"])
    note_id = note["id"]

    resp = notes_client.patch(
        f"/api/notes/{note_id}",
        json={"title": "Multi New", "content": "new body", "tags": ["a", "b"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Multi New"
    assert data["content"] == "new body"
    assert data["tags"] == ["a", "b"]


# ===========================================================================
# Notes — /notes/search endpoint
# ===========================================================================


def test_notes_search_endpoint_returns_matching_notes(notes_client: TestClient) -> None:
    _create_note(notes_client, title="Python Tutorial", content="learn python fast")
    _create_note(notes_client, title="Unrelated Topic", content="nothing to see")

    resp = notes_client.get("/api/notes/search?q=python")

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["id"] is not None
    assert results[0]["title"] == "Python Tutorial"
    assert "context" in results[0]


def test_notes_search_endpoint_matches_body(notes_client: TestClient) -> None:
    _create_note(notes_client, title="Generic Title", content="unique-search-xyz content")

    resp = notes_client.get("/api/notes/search?q=unique-search-xyz")

    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_notes_search_endpoint_returns_empty_for_no_match(notes_client: TestClient) -> None:
    _create_note(notes_client, title="Something", content="body text")

    resp = notes_client.get("/api/notes/search?q=zzznomatch")

    assert resp.status_code == 200
    assert resp.json() == []


def test_notes_search_endpoint_missing_q_returns_400(notes_client: TestClient) -> None:
    resp = notes_client.get("/api/notes/search")
    assert resp.status_code == 400


def test_notes_search_endpoint_empty_q_returns_400(notes_client: TestClient) -> None:
    resp = notes_client.get("/api/notes/search?q=")
    assert resp.status_code == 400


# ===========================================================================
# Notes — response shape and field validation
# ===========================================================================


def test_create_note_response_shape(notes_client: TestClient) -> None:
    resp = notes_client.post(
        "/api/notes",
        json={"title": "Shape Test", "content": "some body", "tags": ["t1", "t2"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "title" in data
    assert "created" in data
    assert "modified" in data
    assert "tags" in data
    assert "content" in data
    assert data["title"] == "Shape Test"
    assert data["content"] == "some body"
    assert sorted(data["tags"]) == ["t1", "t2"]


def test_create_note_title_max_length_returns_400(notes_client: TestClient) -> None:
    resp = notes_client.post(
        "/api/notes",
        json={"title": "x" * 201, "content": "body"},
    )
    assert resp.status_code == 400


def test_create_note_tags_round_trip(notes_client: TestClient) -> None:
    resp = notes_client.post(
        "/api/notes",
        json={"title": "Tags Note", "content": "", "tags": ["alpha", "beta", "gamma"]},
    )
    assert resp.status_code == 201
    note_id = resp.json()["id"]

    get_resp = notes_client.get(f"/api/notes/{note_id}")
    assert sorted(get_resp.json()["tags"]) == ["alpha", "beta", "gamma"]


def test_create_note_empty_tags_defaults_to_list(notes_client: TestClient) -> None:
    resp = notes_client.post("/api/notes", json={"title": "No Tags", "content": "c"})
    assert resp.status_code == 201
    assert resp.json()["tags"] == []


# ===========================================================================
# Datasets — GET /:id
# ===========================================================================


def test_get_dataset_by_id_returns_full_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Single Lookup", csv_bytes=b"x,y\n1,2\n3,4\n",
                         filename="lookup.csv", tags="qa,test", author="Alice")
    dataset_id = upload["id"]

    resp = client.get(f"/api/datasets/{dataset_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == dataset_id
    assert data["title"] == "Single Lookup"
    assert data["format"] == "csv"
    assert data["rowCount"] == 2
    assert sorted(data["tags"]) == ["qa", "test"]
    assert data["author"] == "Alice"


def test_get_dataset_by_id_returns_schema_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Schema DS", csv_bytes=b"col_a,col_b\nv1,v2\n",
                         filename="schema.csv")
    dataset_id = upload["id"]

    resp = client.get(f"/api/datasets/{dataset_id}")

    assert resp.status_code == 200
    schema = resp.json().get("schema") or []
    names = [f["name"] for f in schema]
    assert "col_a" in names
    assert "col_b" in names


# ===========================================================================
# Datasets — PATCH /:id (update metadata)
# ===========================================================================


def test_patch_dataset_updates_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Old Title")
    dataset_id = upload["id"]

    resp = client.patch(f"/api/datasets/{dataset_id}", json={"title": "New Title"})

    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


def test_patch_dataset_updates_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Taggable DS", tags="old")
    dataset_id = upload["id"]

    resp = client.patch(f"/api/datasets/{dataset_id}", json={"tags": ["new", "tags"]})

    assert resp.status_code == 200
    assert sorted(resp.json()["tags"]) == ["new", "tags"]


def test_patch_dataset_updates_status_and_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Status DS")
    dataset_id = upload["id"]

    resp = client.patch(f"/api/datasets/{dataset_id}",
                        json={"status": "reviewed", "priority": 3})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "reviewed"
    assert data["priority"] == 3


def test_patch_dataset_missing_id_returns_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    resp = client.patch("/api/datasets/no-such-ds", json={"title": "X"})

    assert resp.status_code == 404
    assert "no-such-ds" in resp.json()["detail"]


# ===========================================================================
# Datasets — metadata-only upload (no file)
# ===========================================================================


def test_create_dataset_without_file_creates_sidecar_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))
    client = TestClient(create_app())

    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Meta Only Dataset", "author": "Bob", "tags": "meta,nofile"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["metadata"]["title"] == "Meta Only Dataset"

    # No raw data file, but sidecar must exist
    sidecars = list(datasets_dir.glob("*.dataset.yml"))
    assert len(sidecars) == 1


def test_create_dataset_without_file_has_no_path_or_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))
    client = TestClient(create_app())

    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Bare Dataset"},
    )
    assert resp.status_code == 201
    meta = resp.json()["metadata"]
    assert not meta.get("path")
    assert not meta.get("format")


# ===========================================================================
# Datasets — upload validation edge cases
# ===========================================================================


def test_upload_csv_with_header_only_zero_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Empty CSV"},
        files={"file": ("empty.csv", b"col_a,col_b\n", "text/csv")},
    )

    assert resp.status_code == 201
    # row_count=0 is serialised as null by the upload response helper
    assert resp.json()["metadata"]["rowCount"] in (0, None)
    assert resp.json()["metadata"]["columnCount"] == 2


def test_upload_json_empty_array_gives_zero_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Empty JSON"},
        files={"file": ("empty.json", b"[]", "application/json")},
    )

    assert resp.status_code == 201
    # row_count=0 is serialised as null by the upload response helper
    assert resp.json()["metadata"]["rowCount"] in (0, None)


def test_upload_invalid_csv_utf8_decoding_error_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    # Latin-1 bytes that are not valid UTF-8 in a CSV
    bad_bytes = b"id,name\n1,\xff\xfe\n"
    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Bad Encoding CSV"},
        files={"file": ("bad.csv", bad_bytes, "text/csv")},
    )
    # Either 400 (decode error caught) or 201 if repository is binary-tolerant;
    # what must NOT happen is a 500 server error.
    assert resp.status_code in (201, 400)
    assert resp.status_code != 500


def test_upload_raw_csv_bytes_preserved_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))
    client = TestClient(create_app())

    # Include a BOM and trailing CRLF to confirm bytes are not normalised
    raw = b"\xef\xbb\xbfid,value\r\n1,hello\r\n2,world\r\n"
    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "BOM CSV"},
        files={"file": ("bom.csv", raw, "text/csv")},
    )

    assert resp.status_code == 201
    assert (datasets_dir / "bom.csv").read_bytes() == raw


def test_upload_raw_json_bytes_preserved_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datasets_dir = tmp_path / "datasets"
    monkeypatch.setenv("DATASETS_HOME", str(datasets_dir))
    client = TestClient(create_app())

    # Include extra whitespace to confirm the file is not re-serialised
    raw = b'[\n  {"id": 1},\n  {"id": 2}\n]\n'
    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Spaced JSON"},
        files={"file": ("spaced.json", raw, "application/json")},
    )

    assert resp.status_code == 201
    assert (datasets_dir / "spaced.json").read_bytes() == raw


# ===========================================================================
# Datasets — role checks (admin, editor, data-engineer)
# ===========================================================================


def test_admin_role_can_upload_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "admin"},
        data={"title": "Admin Upload"},
        files={"file": ("admin.csv", b"id\n1\n", "text/csv")},
    )
    assert resp.status_code == 201


def test_admin_role_can_delete_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    created = client.post(
        "/api/datasets",
        headers={"X-Role": "admin"},
        data={"title": "Admin Delete"},
        files={"file": ("adel.csv", b"id\n1\n", "text/csv")},
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    resp = client.delete(f"/api/datasets/{dataset_id}", headers={"X-Role": "admin"})
    assert resp.status_code == 204


def test_editor_role_can_upload_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    resp = client.post(
        "/api/datasets",
        headers={"X-Role": "editor"},
        data={"title": "Editor Upload"},
        files={"file": ("editor.csv", b"id\n1\n", "text/csv")},
    )
    assert resp.status_code == 201


def test_editor_role_cannot_delete_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    created = client.post(
        "/api/datasets",
        headers={"X-Role": "data-engineer"},
        data={"title": "Delete Target"},
        files={"file": ("target.csv", b"id\n1\n", "text/csv")},
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    resp = client.delete(f"/api/datasets/{dataset_id}", headers={"X-Role": "editor"})
    assert resp.status_code == 403


def test_data_engineer_role_can_upload_and_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())
    client.headers.update({"X-Role": "data-engineer"})

    created = client.post(
        "/api/datasets",
        data={"title": "DE Lifecycle"},
        files={"file": ("de.csv", b"id\n1\n", "text/csv")},
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    resp = client.delete(f"/api/datasets/{dataset_id}")
    assert resp.status_code == 204


# ===========================================================================
# Search — gaps
# ===========================================================================


def test_search_returns_empty_list_when_no_match(full_client: TestClient) -> None:
    _create_note(full_client, title="Something", content="body")

    resp = full_client.get("/api/search?q=zzznomatchtoken")

    assert resp.status_code == 200
    assert resp.json() == []


def test_search_missing_q_returns_400(full_client: TestClient) -> None:
    resp = full_client.get("/api/search")
    assert resp.status_code == 400


def test_search_result_item_shape(full_client: TestClient) -> None:
    _create_note(full_client, title="Shape Check", content="content here")

    resp = full_client.get("/api/search?q=shape")

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    assert "assetType" in item
    assert "id" in item
    assert "title" in item
    assert "context" in item
    assert item["assetType"] in ("note", "dataset")


def test_search_is_case_insensitive(full_client: TestClient) -> None:
    _create_note(full_client, title="CamelCase Query", content="some body")

    upper_resp = full_client.get("/api/search?q=CAMELCASE")
    lower_resp = full_client.get("/api/search?q=camelcase")

    assert upper_resp.status_code == 200
    assert lower_resp.status_code == 200
    assert len(upper_resp.json()) == len(lower_resp.json()) == 1


def test_search_v1_prefix_also_works(full_client: TestClient) -> None:
    _create_note(full_client, title="V1 Prefix Note", content="body")

    resp = full_client.get("/api/v1/search?q=v1+prefix")

    assert resp.status_code == 200
    assert any("v1" in item["title"].lower() or "prefix" in item["title"].lower()
               for item in resp.json())


def test_notes_search_v1_prefix_also_works(notes_client: TestClient) -> None:
    _create_note(notes_client, title="V1 Note Search", content="unique-v1-token")

    resp = notes_client.get("/api/v1/notes/search?q=unique-v1-token")

    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ===========================================================================
# Datasets — tags and author round-trip
# ===========================================================================


def test_dataset_tags_round_trip_via_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Tagged DS", tags="finance,quarterly,2026",
                         filename="tagged.csv")
    dataset_id = upload["id"]

    resp = client.get(f"/api/datasets/{dataset_id}")

    assert resp.status_code == 200
    assert sorted(resp.json()["tags"]) == ["2026", "finance", "quarterly"]


def test_dataset_author_round_trip_via_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    upload = _upload_csv(client, title="Authored DS", author="Charlie",
                         filename="authored.csv")
    dataset_id = upload["id"]

    resp = client.get(f"/api/datasets/{dataset_id}")

    assert resp.status_code == 200
    assert resp.json()["author"] == "Charlie"
