import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from services.coordination_api.database import run_migrations, create_connection
from services.coordination_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _db():
    tmp = tempfile.mktemp(suffix=".db")
    os.environ["COORDINATION_DB_PATH"] = tmp
    run_migrations(tmp)
    _seed_data(tmp)
    yield
    del os.environ["COORDINATION_DB_PATH"]
    try:
        os.remove(tmp)
    except PermissionError:
        pass


def _seed_data(db_path: str) -> None:
    conn = create_connection(db_path)
    conn.execute(
        "INSERT INTO phases (phase_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("phase-01", "test-phase", "active", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("agent-01", "Test Agent 01", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("agent-02", "Test Agent 02", "2026-07-01T00:00:00Z"),
    )
    for tid, status in [
        ("task-in-progress", "in_progress"),
        ("task-blocked", "blocked"),
        ("task-done", "done"),
    ]:
        conn.execute(
            "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tid, "phase-01", tid, status, "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        )
    for tid in ("task-in-progress", "task-blocked"):
        conn.execute(
            "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at) VALUES (?, ?, ?, ?)",
            (f"assign-{tid}", tid, "agent-01", "2026-07-01T00:00:00Z"),
        )
    conn.commit()
    conn.close()


class TestAttachArtifact:
    def test_attach_artifact_success(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/artifacts",
            json={
                "artifact_type": "repo_file",
                "path_or_url": "src/test.txt",
                "repo_ref": "main",
                "commit_hash": "abc123",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-in-progress"
        assert "artifact_id" in body
        assert "event_id" in body

    def test_attach_artifact_minimal(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/artifacts",
            json={"artifact_type": "note"},
        )
        assert resp.status_code == 200

    def test_attach_artifact_missing_type(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/artifacts",
            json={},
        )
        assert resp.status_code == 400

    def test_attach_artifact_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/artifacts",
            json={"artifact_type": "repo_file"},
        )
        assert resp.status_code == 404


class TestSubmitForReview:
    def test_submit_with_artifact_ids(self) -> None:
        art_resp = client.post(
            "/tasks/task-in-progress/artifacts",
            json={"artifact_type": "repo_file", "path_or_url": "test.txt"},
        )
        artifact_id = art_resp.json()["artifact_id"]

        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={
                "agent_id": "agent-01",
                "artifact_ids": [artifact_id],
                "summary": "Done",
                "validation_notes": ["tests pass"],
                "residual_risks": ["none"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "review"
        assert "event_id" in body

    def test_submit_with_summary_only(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={
                "agent_id": "agent-01",
                "summary": "Implementation complete",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

    def test_submit_from_blocked(self) -> None:
        resp = client.post(
            "/tasks/task-blocked/submit",
            json={
                "agent_id": "agent-01",
                "summary": "Blocked but ready for review",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

    def test_submit_no_evidence_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={"agent_id": "agent-01"},
        )
        assert resp.status_code == 400
        assert "artifact" in resp.json()["detail"].lower() or "summary" in resp.json()["detail"].lower()

    def test_submit_wrong_agent(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={"agent_id": "agent-02", "summary": "Nope"},
        )
        assert resp.status_code == 403

    def test_submit_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/submit",
            json={"agent_id": "agent-01", "summary": "Nope"},
        )
        assert resp.status_code == 404

    def test_submit_done_task_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-done/submit",
            json={"agent_id": "agent-01", "summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_submit_missing_agent_id(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={"summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_submit_artifact_not_found(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={"agent_id": "agent-01", "artifact_ids": ["nonexistent-artifact"]},
        )
        assert resp.status_code == 400

    def test_submit_artifact_wrong_task(self) -> None:
        art_resp = client.post(
            "/tasks/task-in-progress/artifacts",
            json={"artifact_type": "repo_file"},
        )
        artifact_id = art_resp.json()["artifact_id"]

        resp = client.post(
            "/tasks/task-blocked/submit",
            json={
                "agent_id": "agent-01",
                "artifact_ids": [artifact_id],
                "summary": "Done",
            },
        )
        assert resp.status_code == 400
        assert "belong" in resp.json()["detail"].lower()

    def test_submit_creates_event(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/submit",
            json={"agent_id": "agent-01", "summary": "Done"},
        )
        body = resp.json()
        assert body["status"] == "review"
        assert body["event_id"] is not None
