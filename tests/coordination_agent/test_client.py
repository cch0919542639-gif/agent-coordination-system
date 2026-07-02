import os
import tempfile

import httpx
import pytest
from fastapi.testclient import TestClient

from services.coordination_api.database import run_migrations, create_connection
from services.coordination_api.main import app

_fastapi_client = TestClient(app)


@pytest.fixture(autouse=True)
def _db():
    tmp = tempfile.mktemp(suffix=".db")
    os.environ["COORDINATION_DB_PATH"] = tmp
    run_migrations(tmp)
    _seed(tmp)
    yield
    del os.environ["COORDINATION_DB_PATH"]
    try:
        os.remove(tmp)
    except PermissionError:
        pass


def _seed(db_path: str) -> None:
    conn = create_connection(db_path)
    conn.execute(
        "INSERT INTO phases (phase_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("phase-01", "test", "active", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("agent-01", "Test Agent", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("agent-99", "Other Agent", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("task-assigned", "phase-01", "Assigned Task", "assigned", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("task-in-progress", "phase-01", "In Progress Task", "in_progress", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at, lease_expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("assign-01", "task-assigned", "agent-01", "2026-07-01T00:00:00Z", "2099-12-31T23:59:59Z"),
    )
    conn.execute(
        "INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at, lease_expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("assign-02", "task-in-progress", "agent-01", "2026-07-01T00:00:00Z", "2099-12-31T23:59:59Z"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client():
    from clients.coordination_agent.client import CoordinationClient

    def _handle(request: httpx.Request) -> httpx.Response:
        return _fastapi_client.send(request)

    transport = httpx.MockTransport(_handle)
    c = CoordinationClient(base_url="http://test")
    c._client = httpx.Client(transport=transport, timeout=30)
    yield c
    c.close()


class TestClientPoll:
    def test_poll_returns_assigned_tasks(self, client) -> None:
        tasks = client.poll("agent-01", "assigned")
        assert len(tasks) >= 1
        task_ids = [t["task_id"] for t in tasks]
        assert "task-assigned" in task_ids

    def test_poll_empty(self, client) -> None:
        tasks = client.poll("agent-01", "done")
        assert tasks == []


class TestClientClaim:
    def test_claim_success(self, client) -> None:
        result = client.claim("task-assigned", "agent-01")
        assert result["ok"] is True
        assert result["task_id"] == "task-assigned"
        assert result["status"] == "in_progress"

    def test_claim_wrong_agent(self, client) -> None:
        with pytest.raises(RuntimeError, match="HTTP 403"):
            client.claim("task-assigned", "agent-99")


class TestClientHeartbeat:
    def test_heartbeat_success(self, client) -> None:
        result = client.heartbeat("task-in-progress", "agent-01")
        assert result["ok"] is True

    def test_heartbeat_wrong_agent(self, client) -> None:
        with pytest.raises(RuntimeError, match="HTTP 403"):
            client.heartbeat("task-in-progress", "agent-99")


class TestClientProgress:
    def test_progress_success(self, client) -> None:
        result = client.progress("task-in-progress", "agent-01", current_step="Step 1")
        assert result["ok"] is True

    def test_progress_wrong_agent(self, client) -> None:
        with pytest.raises(RuntimeError, match="HTTP 403"):
            client.progress("task-in-progress", "agent-99")


class TestClientIncident:
    def test_incident_success(self, client) -> None:
        result = client.incident("task-in-progress", "agent-01", severity="high", summary="Blocked")
        assert result["ok"] is True
        assert result["status"] == "blocked"

    def test_incident_wrong_agent(self, client) -> None:
        with pytest.raises(RuntimeError, match="HTTP 403"):
            client.incident("task-in-progress", "agent-99", severity="high", summary="Nope")


class TestClientArtifact:
    def test_artifact_success(self, client) -> None:
        result = client.artifact("task-in-progress", "repo_file", path_or_url="path/to/file")
        assert result["ok"] is True
        assert "artifact_id" in result

    def test_artifact_missing_type(self, client) -> None:
        with pytest.raises(RuntimeError, match="HTTP 400"):
            client.artifact("task-in-progress", "")


class TestClientSubmit:
    def test_submit_success(self, client) -> None:
        result = client.submit("task-in-progress", "agent-01", summary="Done")
        assert result["ok"] is True
        assert result["status"] == "review"

    def test_submit_wrong_agent(self, client) -> None:
        with pytest.raises(RuntimeError, match="HTTP 403"):
            client.submit("task-in-progress", "agent-99", summary="Done")
