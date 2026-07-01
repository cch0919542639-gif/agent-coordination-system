import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from services.coordination_api.database import get_db_path, run_migrations, create_connection
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
    conn.execute(
        """
        INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("task-ready-01", "phase-01", "Ready Task", "ready", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("task-done-01", "phase-01", "Done Task", "done", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestAssignTask:
    def test_assign_success(self) -> None:
        resp = client.post(
            "/tasks/task-ready-01/assign",
            json={"agent_id": "agent-01", "assignment_reason": "Best fit"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-ready-01"
        assert body["status"] == "assigned"
        assert "assignment_id" in body
        assert "event_id" in body

    def test_assign_missing_agent_id(self) -> None:
        resp = client.post("/tasks/task-ready-01/assign", json={})
        assert resp.status_code == 400

    def test_assign_nonexistent_task(self) -> None:
        resp = client.post("/tasks/nonexistent/assign", json={"agent_id": "agent-01"})
        assert resp.status_code == 404

    def test_assign_nonexistent_agent(self) -> None:
        resp = client.post(
            "/tasks/task-ready-01/assign",
            json={"agent_id": "unknown-agent"},
        )
        assert resp.status_code == 404

    def test_assign_already_done_task(self) -> None:
        resp = client.post(
            "/tasks/task-done-01/assign",
            json={"agent_id": "agent-01"},
        )
        assert resp.status_code == 400

    def test_assign_twice_fails(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        resp = client.post(
            "/tasks/task-ready-01/assign",
            json={"agent_id": "agent-02"},
        )
        assert resp.status_code == 400


class TestPollAssignedWork:
    def test_poll_empty(self) -> None:
        resp = client.get("/tasks?agent_id=agent-01&status=assigned")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["tasks"] == []

    def test_poll_after_assign(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        resp = client.get("/tasks?agent_id=agent-01&status=assigned")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["tasks"]) == 1
        assert body["tasks"][0]["task_id"] == "task-ready-01"

    def test_poll_other_agent(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        resp = client.get("/tasks?agent_id=agent-02&status=assigned")
        assert resp.status_code == 200
        assert resp.json()["tasks"] == []

    def test_poll_missing_agent_id(self) -> None:
        resp = client.get("/tasks?status=assigned")
        assert resp.status_code == 400

    def test_poll_missing_status(self) -> None:
        resp = client.get("/tasks?agent_id=agent-01")
        assert resp.status_code == 400


class TestClaimTask:
    def test_claim_success(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        resp = client.post(
            "/tasks/task-ready-01/claim",
            json={"agent_id": "agent-01"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-ready-01"
        assert body["status"] == "in_progress"
        assert "event_id" in body

    def test_claim_not_assigned(self) -> None:
        resp = client.post(
            "/tasks/task-ready-01/claim",
            json={"agent_id": "agent-01"},
        )
        assert resp.status_code == 400

    def test_claim_wrong_agent(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        resp = client.post(
            "/tasks/task-ready-01/claim",
            json={"agent_id": "agent-02"},
        )
        assert resp.status_code == 403

    def test_claim_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/claim",
            json={"agent_id": "agent-01"},
        )
        assert resp.status_code == 404

    def test_claim_twice_fails(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        client.post("/tasks/task-ready-01/claim", json={"agent_id": "agent-01"})
        resp = client.post(
            "/tasks/task-ready-01/claim",
            json={"agent_id": "agent-01"},
        )
        assert resp.status_code == 400

    def test_claim_status_transition_task_state(self) -> None:
        client.post("/tasks/task-ready-01/assign", json={"agent_id": "agent-01"})
        client.post("/tasks/task-ready-01/claim", json={"agent_id": "agent-01"})
        resp = client.get("/tasks?agent_id=agent-01&status=in_progress")
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 1
