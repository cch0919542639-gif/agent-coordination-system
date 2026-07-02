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
        ("task-claimed", "claimed"),
        ("task-assigned", "assigned"),
        ("task-expired", "in_progress"),
        ("task-done", "done"),
    ]:
        conn.execute(
            "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tid, "phase-01", tid, status, "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        )
    for tid in ("task-in-progress", "task-claimed", "task-assigned"):
        conn.execute(
            "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at, lease_expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"assign-{tid}", tid, "agent-01", "2026-07-01T00:00:00Z", "2099-12-31T23:59:59Z"),
        )
    conn.execute(
        "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at, lease_expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("assign-task-expired", "task-expired", "agent-01", "2026-07-01T00:00:00Z", "2020-01-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestHeartbeat:
    def test_heartbeat_success(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/heartbeat",
            json={"agent_id": "agent-01", "status": "in_progress"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-in-progress"
        assert "event_id" in body

    def test_heartbeat_refreshes_lease(self) -> None:
        from datetime import datetime, timezone
        before = datetime.now(timezone.utc).isoformat()
        resp = client.post(
            "/tasks/task-in-progress/heartbeat",
            json={"agent_id": "agent-01", "status": "in_progress"},
        )
        assert resp.status_code == 200
        db_path = os.environ["COORDINATION_DB_PATH"]
        conn = create_connection(db_path)
        row = conn.execute(
            "SELECT lease_expires_at FROM assignments WHERE task_id = ? AND closed_at IS NULL",
            ("task-in-progress",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] > before

    def test_heartbeat_wrong_agent(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/heartbeat",
            json={"agent_id": "agent-02", "status": "in_progress"},
        )
        assert resp.status_code == 403

    def test_heartbeat_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/heartbeat",
            json={"agent_id": "agent-01", "status": "in_progress"},
        )
        assert resp.status_code == 404

    def test_heartbeat_missing_agent_id(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/heartbeat",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 400

    def test_heartbeat_invalid_status(self) -> None:
        resp = client.post(
            "/tasks/task-done/heartbeat",
            json={"agent_id": "agent-01", "status": "done"},
        )
        assert resp.status_code == 400

    def test_heartbeat_assigned_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-assigned/heartbeat",
            json={"agent_id": "agent-01", "status": "assigned"},
        )
        assert resp.status_code == 400

    def test_heartbeat_no_active_assignment(self) -> None:
        resp = client.post(
            "/tasks/task-done/heartbeat",
            json={"agent_id": "agent-01", "status": "done"},
        )
        assert resp.status_code == 400

    def test_heartbeat_creates_event(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/heartbeat",
            json={"agent_id": "agent-01", "status": "in_progress"},
        )
        assert resp.status_code == 200
        event_id = resp.json()["event_id"]
        db_path = os.environ["COORDINATION_DB_PATH"]
        conn = create_connection(db_path)
        row = conn.execute(
            "SELECT event_type, actor_id FROM task_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "heartbeat_received"
        assert row[1] == "agent-01"

    def test_heartbeat_claimed_status(self) -> None:
        resp = client.post(
            "/tasks/task-claimed/heartbeat",
            json={"agent_id": "agent-01", "status": "claimed"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestExpiredAssignments:
    def test_list_expired(self) -> None:
        resp = client.get("/heartbeat/expired")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        expired = body["expired_assignments"]
        assert len(expired) >= 1
        expired_ids = [a["task_id"] for a in expired]
        assert "task-expired" in expired_ids
        assert "task-in-progress" not in expired_ids

    def test_list_expired_empty_after_recovery(self) -> None:
        client.post("/tasks/task-expired/recover", json={"orchestrator_id": "orch-01"})
        resp = client.get("/heartbeat/expired")
        body = resp.json()
        expired_ids = [a["task_id"] for a in body["expired_assignments"]]
        assert "task-expired" not in expired_ids


class TestRecovery:
    def test_recover_success(self) -> None:
        resp = client.post(
            "/tasks/task-expired/recover",
            json={"orchestrator_id": "orch-01"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-expired"
        assert body["status"] == "assigned"
        assert "recovered_assignment_id" in body
        assert "event_id" in body

    def test_recover_no_expired_claim(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/recover",
            json={"orchestrator_id": "orch-01"},
        )
        assert resp.status_code == 400

    def test_recover_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/recover",
            json={"orchestrator_id": "orch-01"},
        )
        assert resp.status_code == 404

    def test_recover_creates_lease_expired_event(self) -> None:
        resp = client.post(
            "/tasks/task-expired/recover",
            json={"orchestrator_id": "orch-01"},
        )
        assert resp.status_code == 200
        event_id = resp.json()["event_id"]
        db_path = os.environ["COORDINATION_DB_PATH"]
        conn = create_connection(db_path)
        row = conn.execute(
            "SELECT event_type, actor_id FROM task_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "lease_expired"
        assert row[1] == "orch-01"

    def test_recover_closes_assignment(self) -> None:
        resp = client.post(
            "/tasks/task-expired/recover",
            json={"orchestrator_id": "orch-01"},
        )
        assert resp.status_code == 200
        assignment_id = resp.json()["recovered_assignment_id"]
        db_path = os.environ["COORDINATION_DB_PATH"]
        conn = create_connection(db_path)
        row = conn.execute(
            "SELECT closed_at FROM assignments WHERE assignment_id = ?",
            (assignment_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] is not None
