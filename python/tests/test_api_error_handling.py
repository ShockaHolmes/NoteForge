"""Tests that verify standardized API error responses (400 / 403 / 404).

Acceptance criteria:
- 400 returned for bad requests (missing required fields, unsupported file types,
  invalid file content, empty search query).
- 404 returned for missing notes or datasets.
- 403 returned for role permission failures.
- Every error response body contains a ``detail`` key with a non-empty string.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from notes_app.api.app import create_app


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def notes_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("NOTES_HOME", str(tmp_path / "notes"))
    return TestClient(create_app())


@pytest.fixture()
def datasets_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    return TestClient(create_app())


def _assert_error(response, expected_status: int) -> dict:
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "detail" in body, "Error response must contain 'detail' key"
    assert isinstance(body["detail"], str), "'detail' must be a string"
    assert body["detail"].strip(), "'detail' must not be empty"
    return body


# ---------------------------------------------------------------------------
# 404 — Notes
# ---------------------------------------------------------------------------


def test_get_missing_note_returns_404(notes_client: TestClient) -> None:
    body = _assert_error(notes_client.get("/api/notes/does-not-exist"), 404)
    assert "does-not-exist" in body["detail"]


def test_patch_missing_note_returns_404(notes_client: TestClient) -> None:
    body = _assert_error(
        notes_client.patch("/api/notes/ghost", json={"title": "New"}),
        404,
    )
    assert "ghost" in body["detail"]


def test_put_missing_note_returns_404(notes_client: TestClient) -> None:
    body = _assert_error(
        notes_client.put(
            "/api/notes/ghost",
            json={"title": "T", "content": "c", "tags": []},
        ),
        404,
    )
    assert "ghost" in body["detail"]


def test_delete_missing_note_returns_404(notes_client: TestClient) -> None:
    _assert_error(notes_client.delete("/api/notes/ghost"), 404)


# ---------------------------------------------------------------------------
# 400 — Notes validation
# ---------------------------------------------------------------------------


def test_create_note_missing_title_returns_400(notes_client: TestClient) -> None:
    _assert_error(
        notes_client.post("/api/notes", json={"content": "no title"}),
        400,
    )


def test_create_note_empty_title_returns_400(notes_client: TestClient) -> None:
    _assert_error(
        notes_client.post("/api/notes", json={"title": "", "content": "body"}),
        400,
    )


def test_search_notes_empty_query_returns_400(notes_client: TestClient) -> None:
    # FastAPI Query min_length=1 triggers RequestValidationError → 400
    _assert_error(notes_client.get("/api/notes/search?q="), 400)


# ---------------------------------------------------------------------------
# 404 — Datasets
# ---------------------------------------------------------------------------


def test_get_missing_dataset_returns_404(datasets_client: TestClient) -> None:
    body = _assert_error(datasets_client.get("/api/datasets/no-such-dataset"), 404)
    assert "no-such-dataset" in body["detail"]


def test_patch_missing_dataset_returns_404(datasets_client: TestClient) -> None:
    datasets_client.headers.update({"X-Role": "editor"})
    body = _assert_error(
        datasets_client.patch("/api/datasets/ghost", json={"title": "X"}),
        404,
    )
    assert "ghost" in body["detail"]


def test_delete_missing_dataset_returns_404(datasets_client: TestClient) -> None:
    datasets_client.headers.update({"X-Role": "data-engineer"})
    body = _assert_error(
        datasets_client.delete(
            "/api/datasets/ghost",
            headers={"X-Role": "data-engineer"},
        ),
        404,
    )
    assert "ghost" in body["detail"]


def test_preview_missing_dataset_returns_404(datasets_client: TestClient) -> None:
    _assert_error(datasets_client.get("/api/datasets/no-such/preview"), 404)


def test_profile_missing_dataset_returns_404(datasets_client: TestClient) -> None:
    _assert_error(datasets_client.get("/api/datasets/no-such/profile"), 404)


# ---------------------------------------------------------------------------
# 400 — Dataset bad requests
# ---------------------------------------------------------------------------


def test_create_dataset_unsupported_file_type_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())
    client.headers.update({"X-Role": "data-engineer"})

    response = client.post(
        "/api/datasets",
        data={"title": "Bad Upload"},
        files={"file": ("data.xml", b"<root/>", "application/xml")},
    )
    body = _assert_error(response, 400)
    assert "xml" in body["detail"].lower() or "unsupported" in body["detail"].lower()


def test_create_dataset_invalid_json_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())
    client.headers.update({"X-Role": "data-engineer"})

    response = client.post(
        "/api/datasets",
        data={"title": "Broken JSON"},
        files={"file": ("data.json", b"{not valid json", "application/json")},
    )
    body = _assert_error(response, 400)
    assert "json" in body["detail"].lower()


def test_create_dataset_missing_title_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())
    client.headers.update({"X-Role": "data-engineer"})

    response = client.post(
        "/api/datasets",
        data={"author": "nobody"},
    )
    _assert_error(response, 400)


# ---------------------------------------------------------------------------
# 403 — Role permission failures
# ---------------------------------------------------------------------------


def test_create_dataset_viewer_role_returns_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    response = client.post(
        "/api/datasets",
        data={"title": "Blocked"},
        headers={"X-Role": "viewer"},
    )
    body = _assert_error(response, 403)
    assert body["detail"]


def test_create_dataset_editor_role_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    response = client.post(
        "/api/datasets",
        data={"title": "Allowed"},
        headers={"X-Role": "editor"},
    )
    assert response.status_code == 201


def test_delete_dataset_editor_role_returns_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    response = client.delete(
        "/api/datasets/any-id",
        headers={"X-Role": "editor"},
    )
    body = _assert_error(response, 403)
    assert body["detail"]


def test_invalid_role_header_returns_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATASETS_HOME", str(tmp_path / "datasets"))
    client = TestClient(create_app())

    response = client.post(
        "/api/datasets",
        data={"title": "Blocked"},
        headers={"X-Role": "superuser"},
    )
    body = _assert_error(response, 403)
    assert "role" in body["detail"].lower()
