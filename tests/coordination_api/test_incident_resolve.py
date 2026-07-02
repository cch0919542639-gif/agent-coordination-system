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
        "INSERT INTO tasks (task_id, phase_id, title, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("task-01", "phase-01", "Test Task", "blocked", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO incidents (incident_id, task_id, agent_id, severity, category, summary, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("incident-open", "task-01", "agent-01", "high", "scope_conflict", "Open incident", "open", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO incidents (incident_id, task_id, agent_id, severity, category, summary, status, resolved_at, resolution_summary, resolver_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("incident-resolved", "task-01", "agent-01", "medium", "spec_ambiguity", "Already resolved", "resolved", "2026-07-01T12:00:00Z", "Fixed", "orchestrator-01", "2026-07-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()


class TestResolveIncident:
    def test_resolve_success(self) -> None:
        resp = client.post(
            "/incidents/incident-open/resolve",
            json={
                "resolver_id": "orchestrator-01",
                "resolution_summary": "Split migration into prerequisite task",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["incident_id"] == "incident-open"
        assert body["task_id"] == "task-01"
        assert body["status"] == "resolved"
        assert "event_id" in body

    def test_resolve_already_resolved(self) -> None:
        resp = client.post(
            "/incidents/incident-resolved/resolve",
            json={"resolver_id": "orchestrator-01", "resolution_summary": "Again"},
        )
        assert resp.status_code == 400

    def test_resolve_nonexistent_incident(self) -> None:
        resp = client.post(
            "/incidents/nonexistent/resolve",
            json={"resolver_id": "orchestrator-01", "resolution_summary": "Nope"},
        )
        assert resp.status_code == 404

    def test_resolve_missing_resolver_id(self) -> None:
        resp = client.post(
            "/incidents/incident-open/resolve",
            json={"resolution_summary": "Nope"},
        )
        assert resp.status_code == 400

    def test_resolve_empty_resolution_summary(self) -> None:
        resp = client.post(
            "/incidents/incident-open/resolve",
            json={"resolver_id": "orchestrator-01", "resolution_summary": ""},
        )
        assert resp.status_code == 200

    def test_resolve_persists_fields(self) -> None:
        resp = client.post(
            "/incidents/incident-open/resolve",
            json={
                "resolver_id": "orchestrator-42",
                "resolution_summary": "Resolved via coordination API",
            },
        )
        assert resp.status_code == 200

        from services.coordination_api.repository import find_incident
        updated = find_incident("incident-open")
        assert updated["status"] == "resolved"
        assert updated["resolver_id"] == "orchestrator-42"
        assert updated["resolution_summary"] == "Resolved via coordination API"
        assert updated["resolved_at"] is not None

    def test_resolve_creates_incident_resolved_event(self) -> None:
        resp = client.post(
            "/incidents/incident-open/resolve",
            json={
                "resolver_id": "orchestrator-01",
                "resolution_summary": "Fixed",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["event_id"] is not None
