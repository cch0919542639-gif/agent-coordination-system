"""Focused coverage for read-only project-aware status projection."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from event_ledger import Event
from event_routing import DeliveryRecord
from project_registry import ProjectEntry
from status_projector import build_status


def _card(root: Path, state: str, task_id: str, owner: str = "worker-a", **extra: str) -> None:
    fields = {
        "task_id": task_id, "phase": "test", "status": state.upper(),
        "owner": owner, "reviewer": "ORCHESTRATOR", "priority": "low",
        "dependencies": "[]", "allowed_scope": "[]", "forbidden_scope": "[]",
        "acceptance": "[]", "expected_artifacts": "[]", **extra,
    }
    lines = ["---", *[f"{key}: {value}" for key, value in fields.items()], "---", "secret-body-value"]
    path = root / "coordination" / "task-board" / state / f"{task_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _progress(root: Path, agent: str, task_id: str, updated: str) -> None:
    path = root / "coordination" / "progress" / f"{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"- Agent: {agent}\n- Active Task: {task_id}\n- Status: IN_PROGRESS\n- Last Updated: {updated}\n",
        encoding="utf-8",
    )


def test_detects_required_anomalies_without_leaking_local_content(tmp_path: Path) -> None:
    _card(tmp_path, "in_progress", "stale-task", execution_mode="WORKTREE", branch="agent/a/task")
    _card(tmp_path, "review", "review-task")
    _card(tmp_path, "in_progress", "claimed-task")
    _progress(tmp_path, "worker-a", "stale-task", "2026-01-01T00:00:00Z")
    project = ProjectEntry(project_id="proj-a", local_path=str(tmp_path), monitor_branches=[])
    deliveries = [
        DeliveryRecord(payload_id="review", project_id="proj-a", task_id="review-task", event_type="review_submitted", destination="orchestrator", status="pending"),
        DeliveryRecord(payload_id="ready", project_id="proj-a", task_id="claimed-task", event_type="ready_assigned", destination="registered_worker", status="acknowledged"),
    ]
    events = [Event("event-1", "proj-a", "private-repository", "main", "abc", "review-task", "review_submitted", "2026-01-01T00:00:00Z")]
    result = build_status([project], events, deliveries, now=datetime(2026, 1, 3, tzinfo=timezone.utc), stale_after_hours=24)
    codes = {alert["code"] for alert in result["alerts"]}
    assert {"pending_review_delivery", "acknowledged_ready_nonready", "worker_branch_unmonitored", "stale_in_progress"} <= codes
    encoded = json.dumps(result)
    assert str(tmp_path) not in encoded
    assert "secret-body-value" not in encoded
    assert "private-repository" not in encoded
    assert result["projects"][0]["event_count"] == 1


def test_progress_mismatch_is_deterministic(tmp_path: Path) -> None:
    _card(tmp_path, "review", "task-a", owner="worker-a")
    _progress(tmp_path, "worker-a", "task-a", "2026-01-02T00:00:00Z")
    _progress(tmp_path, "worker-b", "missing-task", "2026-01-02T00:00:00Z")
    project = ProjectEntry(project_id="proj-a", local_path=str(tmp_path))
    result = build_status([project], [], [], now=datetime(2026, 1, 2, tzinfo=timezone.utc))
    mismatches = [a["task_id"] for a in result["alerts"] if a["code"] == "task_progress_mismatch"]
    assert mismatches == ["missing-task", "task-a"]


def test_includes_incident_evidence_without_exposing_its_content(tmp_path: Path) -> None:
    incident = tmp_path / "coordination" / "incidents" / "incident.md"
    incident.parent.mkdir(parents=True)
    incident.write_text("private incident detail", encoding="utf-8")
    project = ProjectEntry(project_id="proj-a", local_path=str(tmp_path))

    result = build_status([project], [], [])

    assert result["projects"][0]["incident_count"] == 1
    assert "private incident detail" not in json.dumps(result)


def test_empty_registry_is_safe() -> None:
    assert build_status([], [], []) == {"projects": [], "alerts": [], "summary": {"projects": 0, "alerts": 0}}
