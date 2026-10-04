import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import services.coordination_api.main as api_main
from services.coordination_api.config import Settings
from services.coordination_api.database import run_migrations, create_connection
from services.coordination_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _db(monkeypatch):
    tmp = tempfile.mktemp(suffix=".db")
    previous_settings = api_main.settings
    os.environ["COORDINATION_DB_PATH"] = tmp
    monkeypatch.setenv("COORDINATION_ORCHESTRATOR_REVIEW_KEY", "test-review-key")
    client.headers.update({"X-API-Key": "test-review-key"})
    api_main.settings = Settings(api_keys=[], db_path=tmp)
    run_migrations(tmp)
    _seed_data(tmp)
    yield
    client.headers.pop("X-API-Key", None)
    api_main.settings = previous_settings
    del os.environ["COORDINATION_DB_PATH"]
    try:
        os.remove(tmp)
    except PermissionError:
        pass


def _post_review(task_id: str, body: dict, *, headers: dict[str, str] | None = None, include_triage: bool = True):
    payload = dict(body)
    if include_triage and payload.get("decision"):
        payload.setdefault("human_decision", "not-needed")
        payload.setdefault("risk", "none")
    return client.post(f"/tasks/{task_id}/review", json=payload, headers=headers)


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
    def test_review_fails_closed_when_controller_key_is_unconfigured(self, monkeypatch) -> None:
        monkeypatch.delenv("COORDINATION_ORCHESTRATOR_REVIEW_KEY")
        resp = _post_review(
            "task-review",
            {"reviewer_id": "ORCHESTRATOR", "decision": "accepted"},
        )
        assert resp.status_code == 503

    def test_review_requires_dedicated_controller_key(self) -> None:
        saved_key = client.headers.pop("X-API-Key")
        try:
            resp = _post_review(
                "task-review",
                {"reviewer_id": "ORCHESTRATOR", "decision": "accepted"},
            )
        finally:
            client.headers["X-API-Key"] = saved_key
        assert resp.status_code == 403

    def test_valid_worker_key_cannot_claim_controller_identity(self) -> None:
        resp = _post_review(
            "task-review",
            {"reviewer_id": "agent-01", "decision": "accepted"},
            headers={"X-API-Key": "worker-key"},
        )
        assert resp.status_code == 403

    def test_review_requires_explicit_triage_and_pauses_on_escalation(self) -> None:
        missing = _post_review(
            "task-review",
            {"reviewer_id": "ORCHESTRATOR", "decision": "accepted"},
            include_triage=False,
        )
        assert missing.status_code == 400

        unsafe_accept = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "accepted",
                "human_decision": "not-needed",
                "risk": "identified",
            },
        )
        assert unsafe_accept.status_code == 400

        paused = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "paused",
                "human_decision": "required",
                "risk": "none",
            },
        )
        assert paused.status_code == 200
        assert paused.json()["status"] == "review"

    def test_review_accepted(self) -> None:
        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
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
        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "needs_fix",
                "summary": "Fix retry logic",
                "findings": [{"severity": "medium", "title": "Retry missing", "detail": "Add retry"}],
                "required_changes": ["Add idempotency test"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_review_reassign(self) -> None:
        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "reassign",
                "summary": "Capability mismatch",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"

    def test_review_rejected(self) -> None:
        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "rejected",
                "summary": "Does not meet requirements",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_review_wrong_status(self) -> None:
        resp = _post_review(
            "task-in-progress",
            {"reviewer_id": "ORCHESTRATOR", "decision": "accepted"},
        )
        assert resp.status_code == 400

    def test_review_nonexistent_task(self) -> None:
        resp = _post_review(
            "nonexistent",
            {"reviewer_id": "ORCHESTRATOR", "decision": "accepted"},
        )
        assert resp.status_code == 404

    def test_review_missing_reviewer_id(self) -> None:
        resp = _post_review(
            "task-review",
            {"decision": "accepted"},
        )
        assert resp.status_code == 400

    def test_review_missing_decision(self) -> None:
        resp = _post_review(
            "task-review",
            {"reviewer_id": "ORCHESTRATOR"},
        )
        assert resp.status_code == 400

    def test_review_invalid_decision(self) -> None:
        resp = _post_review(
            "task-review",
            {"reviewer_id": "ORCHESTRATOR", "decision": "invalid_decision"},
        )
        assert resp.status_code == 400

    def test_review_with_accepted_artifacts(self) -> None:
        art_resp = client.post(
            "/tasks/task-review/artifacts",
            json={"artifact_type": "repo_file", "path_or_url": "test.txt"},
        )
        artifact_id = art_resp.json()["artifact_id"]

        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "accepted",
                "accepted_artifact_ids": [artifact_id],
            },
        )
        assert resp.status_code == 200

    def test_review_artifact_not_found(self) -> None:
        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
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

        resp = _post_review(
            "task-review",
            {
                "reviewer_id": "ORCHESTRATOR",
                "decision": "accepted",
                "accepted_artifact_ids": [artifact_id],
            },
        )
        assert resp.status_code == 400

    def test_review_creates_event(self) -> None:
        resp = _post_review(
            "task-review",
            {"reviewer_id": "ORCHESTRATOR", "decision": "accepted"},
        )
        body = resp.json()
        assert body["event_id"] is not None
        assert body["review_id"] is not None
        with create_connection(os.environ["COORDINATION_DB_PATH"]) as conn:
            row = conn.execute(
                "SELECT payload FROM task_events WHERE event_id = ?",
                (body["event_id"],),
            ).fetchone()
        event = json.loads(row["payload"])
        assert event["human_decision"] == "not-needed"
        assert event["risk"] == "none"
