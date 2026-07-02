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
        ("task-review", "review"),
        ("task-done", "done"),
    ]:
        conn.execute(
            "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tid, "phase-01", tid, status, "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        )
    conn.execute(
        "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at) VALUES (?, ?, ?, ?)",
        ("assign-01", "task-in-progress", "agent-01", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at) VALUES (?, ?, ?, ?)",
        ("assign-review", "task-review", "agent-01", "2026-07-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestReassignTask:
    def test_reassign_success(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Capability mismatch",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "assigned"
        assert "previous_assignment_id" in body
        assert "new_assignment_id" in body
        assert "event_id" in body

    def test_reassign_new_agent_can_claim(self) -> None:
        client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Handoff",
            },
        )
        claim_resp = client.post(
            "/tasks/task-in-progress/claim",
            json={"agent_id": "agent-02"},
        )
        assert claim_resp.status_code == 200

    def test_reassign_old_agent_cannot_claim(self) -> None:
        client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Handoff",
            },
        )
        claim_resp = client.post(
            "/tasks/task-in-progress/claim",
            json={"agent_id": "agent-01"},
        )
        assert claim_resp.status_code == 403

    def test_reassign_wrong_from_agent(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-02",
                "to_agent_id": "agent-01",
                "reason": "Nope",
            },
        )
        assert resp.status_code == 400

    def test_reassign_missing_from_agent_id(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={"to_agent_id": "agent-02", "reason": "Nope"},
        )
        assert resp.status_code == 400

    def test_reassign_missing_to_agent_id(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={"from_agent_id": "agent-01", "reason": "Nope"},
        )
        assert resp.status_code == 400

    def test_reassign_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Nope",
            },
        )
        assert resp.status_code == 404

    def test_reassign_nonexistent_target_agent(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "nonexistent",
                "reason": "Nope",
            },
        )
        assert resp.status_code == 404

    def test_reassign_done_task_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-done/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Nope",
            },
        )
        assert resp.status_code == 400

    def test_reassign_creates_event_with_history(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Capability mismatch",
            },
        )
        body = resp.json()
        assert body["event_id"] is not None
        assert body["previous_assignment_id"] == "assign-01"
        assert body["new_assignment_id"] != "assign-01"

    def test_reassign_no_active_assignment(self) -> None:
        conn = create_connection(os.environ["COORDINATION_DB_PATH"])
        conn.execute(
            "UPDATE assignments SET closed_at = '2026-07-01T00:00:00Z' WHERE task_id = ?",
            ("task-in-progress",),
        )
        conn.commit()
        conn.close()

        resp = client.post(
            "/tasks/task-in-progress/reassign",
            json={
                "from_agent_id": "agent-01",
                "to_agent_id": "agent-02",
                "reason": "Nope",
            },
        )
        assert resp.status_code == 400


class TestReviewReassign:
    def test_review_reassign_closes_old_assignment(self) -> None:
        resp = client.post(
            "/tasks/task-review/review",
            json={
                "reviewer_id": "orchestrator-01",
                "decision": "reassign",
                "summary": "Needs different skills",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"

        claim_by_old = client.post(
            "/tasks/task-review/claim",
            json={"agent_id": "agent-01"},
        )
        assert claim_by_old.status_code == 400
        assert "No active assignment" in claim_by_old.json()["detail"]


