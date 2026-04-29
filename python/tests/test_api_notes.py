from pathlib import Path

from fastapi.testclient import TestClient

from notes_app.api.app import create_app


def test_notes_api_crud_end_to_end(tmp_path: Path, monkeypatch) -> None:
    notes_dir = tmp_path / "notes"
    monkeypatch.setenv("NOTES_HOME", str(notes_dir))

    app = create_app()
    client = TestClient(app)

    # POST /api/notes
    create_response = client.post(
        "/api/notes",
        json={
            "title": "API Note",
            "content": "first body",
            "tags": ["api", "phase-2"],
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    note_id = created["id"]
    assert created["title"] == "API Note"

    # GET /api/notes
    list_response = client.get("/api/notes")
    assert list_response.status_code == 200
    notes = list_response.json()
    assert len(notes) == 1
    assert notes[0]["id"] == note_id

    # GET /api/notes/:id
    get_response = client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["title"] == "API Note"
    assert fetched["content"] == "first body"

    # PUT /api/notes/:id
    put_response = client.put(
        f"/api/notes/{note_id}",
        json={
            "title": "Updated API Note",
            "content": "updated body",
            "tags": ["updated", "api"],
        },
    )
    assert put_response.status_code == 200
    updated = put_response.json()
    assert updated["title"] == "Updated API Note"
    assert updated["content"] == "updated body"
    assert updated["tags"] == ["updated", "api"]

    # DELETE /api/notes/:id
    delete_response = client.delete(f"/api/notes/{note_id}")
    assert delete_response.status_code == 204

    # Confirm deletion
    missing_response = client.get(f"/api/notes/{note_id}")
    assert missing_response.status_code == 404


def test_put_note_missing_returns_404(tmp_path: Path, monkeypatch) -> None:
    notes_dir = tmp_path / "notes"
    monkeypatch.setenv("NOTES_HOME", str(notes_dir))

    app = create_app()
    client = TestClient(app)

    response = client.put(
        "/api/notes/does-not-exist",
        json={
            "title": "Missing",
            "content": "body",
            "tags": ["none"],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Note 'does-not-exist' not found."
