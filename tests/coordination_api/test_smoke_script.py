from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.coordination_api.database import run_migrations
from services.coordination_api.main import app


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test_coordination.py"


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
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO phases (phase_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("phase-01", "smoke-phase", "active", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("agent-smoke", "Smoke Agent", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
        ("orchestrator", "Orchestrator", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("smoke-task-01", "phase-01", "Smoke Task", "ready", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestSmokeScriptHelp:
    def test_help_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "smoke-test" in result.stdout

    def test_invocation_with_flags(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help", "--db-path", "test.db"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0


class TestSmokeScriptAgainstTestClient:
    @pytest.fixture(autouse=True)
    def _disable_auth(self):
        import services.coordination_api.main as m

        original = m.settings
        from services.coordination_api.config import Settings
        m.settings = Settings(host="127.0.0.1", port=8000, api_keys=[])
        yield
        m.settings = original

    def test_health_check_via_client(self) -> None:
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_lifecycle_endpoints_via_client(self) -> None:
        client = TestClient(app)
        task_id = "smoke-task-01"
        agent_id = "agent-smoke"

        resp = client.post(f"/tasks/{task_id}/assign", json={
            "agent_id": agent_id, "assignment_reason": "Smoke test",
        })
        assert resp.status_code == 200, f"assign failed: {resp.json()}"

        resp = client.get(f"/tasks?agent_id={agent_id}&status=assigned")
        assert resp.status_code == 200
        assert len(resp.json().get("tasks", [])) == 1

        resp = client.post(f"/tasks/{task_id}/claim", json={"agent_id": agent_id})
        assert resp.status_code == 200, f"claim failed: {resp.json()}"

        resp = client.post(f"/tasks/{task_id}/progress", json={
            "agent_id": agent_id, "current_step": "Testing", "blocker_status": "none",
        })
        assert resp.status_code == 200, f"progress failed: {resp.json()}"

        resp = client.post(f"/tasks/{task_id}/submit", json={
            "agent_id": agent_id, "summary": "Smoke complete",
        })
        assert resp.status_code == 200, f"submit failed: {resp.json()}"

        resp = client.post(f"/tasks/{task_id}/review", json={
            "reviewer_id": "orchestrator", "decision": "accepted", "summary": "Accepted",
        })
        assert resp.status_code == 200, f"review failed: {resp.json()}"

    def test_incident_path_via_client(self) -> None:
        client = TestClient(app)
        task_id = "smoke-task-01"
        agent_id = "agent-smoke"

        client.post(f"/tasks/{task_id}/assign", json={
            "agent_id": agent_id, "assignment_reason": "Test",
        })
        client.post(f"/tasks/{task_id}/claim", json={"agent_id": agent_id})

        resp = client.post(f"/tasks/{task_id}/incidents", json={
            "agent_id": agent_id, "severity": "low",
            "summary": "Test incident", "category": "environment_failure",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "blocked"

    def test_heartbeat_via_client(self) -> None:
        client = TestClient(app)
        task_id = "smoke-task-01"
        agent_id = "agent-smoke"

        client.post(f"/tasks/{task_id}/assign", json={
            "agent_id": agent_id, "assignment_reason": "Test",
        })
        client.post(f"/tasks/{task_id}/claim", json={"agent_id": agent_id})

        resp = client.post(f"/tasks/{task_id}/heartbeat", json={
            "agent_id": agent_id, "status": "in_progress",
        })
        assert resp.status_code == 200

        resp = client.get("/heartbeat/expired")
        assert resp.status_code == 200
