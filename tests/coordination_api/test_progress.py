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
        ("task-in-progress", "phase-01", "In Progress Task", "in_progress",
         "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("task-claimed", "phase-01", "Claimed Task", "claimed",
         "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("task-assigned", "phase-01", "Assigned Task", "assigned",
         "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("task-done", "phase-01", "Done Task", "done",
         "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at)
        VALUES (?, ?, ?, ?)
        """,
        ("assign-01", "task-in-progress", "agent-01", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at)
        VALUES (?, ?, ?, ?)
        """,
        ("assign-02", "task-claimed", "agent-01", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at)
        VALUES (?, ?, ?, ?)
        """,
        ("assign-03", "task-assigned", "agent-02", "2026-07-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestReportProgress:
    def test_progress_in_progress(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/progress",
            json={
                "agent_id": "agent-01",
                "current_step": "Writing tests",
                "changed_files": ["test_x.py"],
                "blocker_status": "none",
                "next_step": "Run suite",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"] == "task-in-progress"
        assert body["status"] == "in_progress"
        assert "event_id" in body
        assert "updated_at" in body

    def test_progress_claimed_transitions_to_in_progress(self) -> None:
        resp = client.post(
            "/tasks/task-claimed/progress",
            json={
                "agent_id": "agent-01",
                "current_step": "Starting work",
                "blocker_status": "none",
                "next_step": "Implement feature",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "in_progress"

        poll = client.get("/tasks?agent_id=agent-01&status=in_progress")
        task_ids = [t["task_id"] for t in poll.json()["tasks"]]
        assert "task-claimed" in task_ids

    def test_progress_wrong_agent(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/progress",
            json={"agent_id": "agent-02", "current_step": "Hacking"},
        )
        assert resp.status_code == 403

    def test_progress_not_assigned(self) -> None:
        resp = client.post(
            "/tasks/task-done/progress",
            json={"agent_id": "agent-01", "current_step": "Nope"},
        )
        assert resp.status_code == 400

    def test_progress_assigned_status_rejected(self) -> None:
        resp = client.post(
            "/tasks/task-assigned/progress",
            json={"agent_id": "agent-02", "current_step": "Nope"},
        )
        assert resp.status_code == 400

    def test_progress_nonexistent_task(self) -> None:
        resp = client.post(
            "/tasks/nonexistent/progress",
            json={"agent_id": "agent-01", "current_step": "Nope"},
        )
        assert resp.status_code == 404

    def test_progress_missing_agent_id(self) -> None:
        resp = client.post(
            "/tasks/task-in-progress/progress",
            json={"current_step": "Nope"},
        )
        assert resp.status_code == 400

    def test_progress_creates_event(self) -> None:
        client.post(
            "/tasks/task-in-progress/progress",
            json={
                "agent_id": "agent-01",
                "current_step": "Debugging",
                "changed_files": ["fix.py"],
                "blocker_status": "none",
                "next_step": "Deploy",
            },
        )
        resp = client.post(
            "/tasks/task-in-progress/progress",
            json={
                "agent_id": "agent-01",
                "current_step": "Testing",
                "changed_files": ["test_fix.py"],
                "blocker_status": "none",
                "next_step": "Submit",
            },
        )
        assert resp.status_code == 200
