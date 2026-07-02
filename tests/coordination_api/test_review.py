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
        ("agent-01", "Test Agent", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("orchestrator-01", "Orchestrator", "2026-07-01T00:00:00Z"),
    )
    for tid, status in [
        ("task-review", "review"),
        ("task-in-progress", "in_progress"),
        ("other-task", "in_progress"),
    ]:
        conn.execute(
            "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tid, "phase-01", tid, status, "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        )
    conn.execute(
        "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at) VALUES (?, ?, ?, ?)",
        ("assign-review", "task-review", "agent-01", "2026-07-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestReviewTask:
    def test_review_accepted(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "accepted",
                "summary": "Good work",
                "findings": [{"severity": "low", "title": "Minor nit", "detail": "Fix later"}],
                "required_changes": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "accepted"
        assert "review_id" in body
        assert "event_id" in body

    def test_review_needs_fix(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "needs_fix",
                "summary": "Fix retry logic",
                "findings": [{"severity": "medium", "title": "Retry missing", "detail": "Add retry"}],
                "required_changes": ["Add idempotency test"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_review_reassign(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "reassign",
                "summary": "Capability mismatch",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"

    def test_review_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "rejected",
                "summary": "Does not meet requirements",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_review_wrong_status(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/review",
            json={"reviewer_id": "orchestrator-01", "decision": "accepted"},
        )
        assert resp.status_code == 400

    def test_review_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/review",
            json={"reviewer_id": "orchestrator-01", "decision": "accepted"},
        )
        assert resp.status_code == 404

    def test_review_missing_reviewer_id(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={"decision": "accepted"},
        )
        assert resp.status_code == 400

    def test_review_missing_decision(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={"reviewer_id": "orchestrator-01"},
        )
        assert resp.status_code == 400

    def test_review_invalid_decision(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={"reviewer_id": "orchestrator-01", "decision": "invalid_decision"},
        )
        assert resp.status_code == 400

    def test_review_with_accepted_artifacts(self) -> None:
        art_resp = client.post(
            "/tasks/task-review/artifacts",
            json={"artifact_type": "repo_file", "path_or_url": "test.txt"},
        )
        artifact_id = art_resp.json()["artifact_id"]

        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "accepted",
                "accepted_artifact_ids": [artifact_id],
            },
        )
        assert resp.status_code == 200

    def test_review_artifact_not_found(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "accepted",
                "accepted_artifact_ids": ["nonexistent"],
            },
        )
        assert resp.status_code == 400

    def test_review_artifact_wrong_task(self) -> None:
        art_resp = client.post(
            "/tasks/other-task/artifacts",
            json={"artifact_type": "repo_file"},
        )
        artifact_id = art_resp.json()["artifact_id"]

        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "accepted",
                "accepted_artifact_ids": [artifact_id],
            },
        )
        assert resp.status_code == 400

    def test_review_creates_event(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={"reviewer_id": "orchestrator-01", "decision": "accepted"},
        )
        body = resp.json()
        assert body["event_id"] is not None
        assert body["review_id"] is not None
