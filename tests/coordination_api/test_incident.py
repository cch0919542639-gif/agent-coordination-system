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
        ("task-claimed", "claimed"),
        ("task-assigned", "assigned"),
        ("task-done", "done"),
    ]:
        conn.execute(
            "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tid, "phase-01", tid, status, "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        )
    for tid in ("task-in-progress", "task-blocked", "task-claimed", "task-assigned"):
        conn.execute(
            "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at) VALUES (?, ?, ?, ?)",
            (f"assign-{tid}", tid, "agent-01", "2026-07-01T00:00:00Z"),
        )
    conn.commit()
    conn.close()


class TestOpenIncident:
    def test_incident_from_in_progress(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/incidents",
            json={
                "agent_id": "agent-01",
                "severity": "high",
                "category": "scope_conflict",
                "summary": "Cannot proceed",
                "details": "Migration outside scope",
                "proposed_resolution": "Split task",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-in-progress"
        assert body["status"] == "blocked"
        assert "incident_id" in body
        assert "event_id" in body

    def test_incident_from_blocked(self) -> None:
        resp = client.post(
            "/tasks/task-blocked/incidents",
            json={
                "agent_id": "agent-01",
                "severity": "medium",
                "summary": "Another issue",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "blocked"

    def test_incident_from_claimed(self) -> None:
        resp = client.post(
            "/tasks/task-claimed/incidents",
            json={
                "agent_id": "agent-01",
                "severity": "low",
                "summary": "Minor blocker",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "blocked"

    def test_incident_wrong_agent(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/incidents",
            json={"agent_id": "agent-02", "severity": "high", "summary": "Nope"},
        )
        assert resp.status_code == 403

    def test_incident_assigned_status_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-assigned/incidents",
            json={"agent_id": "agent-01", "severity": "high", "summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_incident_done_status_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-done/incidents",
            json={"agent_id": "agent-01", "severity": "high", "summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_incident_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/incidents",
            json={"agent_id": "agent-01", "severity": "high", "summary": "Nope"},
        )
        assert resp.status_code == 404

    def test_incident_missing_agent_id(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/incidents",
            json={"severity": "high", "summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_incident_invalid_severity(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/incidents",
            json={"agent_id": "agent-01", "severity": "critical", "summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_incident_transitions_task_to_blocked(self) -> None:
        client.post(
            "/tasks/task-in-progress/incidents",
            json={"agent_id": "agent-01", "severity": "high", "summary": "Blocker"},
        )
        resp = client.get("/tasks?agent_id=agent-01&status=blocked")
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        task_ids = [t["task_id"] for t in tasks]
        assert "task-in-progress" in task_ids
        assert "task-blocked" in task_ids
