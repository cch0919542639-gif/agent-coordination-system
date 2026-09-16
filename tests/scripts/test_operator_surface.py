from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from operator_surface import CRITICAL_ACTIONS, critical_action_decision, project_operation


NOW = "2026-09-17T08:00:00+00:00"


def records() -> dict[str, dict[str, object]]:
    return {
        "plan": {"task_id": "task-07", "status": "READY", "dependency_task_ids": ["task-05", "task-06"]},
        "admit": {"task_id": "task-07", "grant_id": "grant-01", "decision": "admitted", "risk_tier": "standard"},
        "dispatch": {"task_id": "task-07", "owner": "worker-01", "worktree_ref": "worktrees/worker-01/task-07", "decision": "dispatched", "lease_epoch": 1},
        "run-status": {"task_id": "task-07", "run_id": "run-01", "state": "active", "lease_epoch": 1, "decision": "accepted_heartbeat"},
        "review-bundle": {"task_id": "task-07", "reviewer": "reviewer-01", "bundle_hash": "bundle-01", "decision": "review_queued"},
        "approval-queue": {"task_id": "task-07", "run_id": "run-01", "incident_category": "lease_retry_exhausted", "lease_epoch": 1, "decision": "operator_decision_required"},
    }


def approval(action: str = "merge") -> dict[str, object]:
    return {"approval_id": "approval-01", "action": action, "task_id": "task-07", "issued_at": "2026-09-17T07:00:00+00:00", "expires_at": "2026-09-17T09:00:00+00:00", "enabled": True}


def test_all_required_operations_have_stable_allowlisted_projections() -> None:
    for operation, record in records().items():
        first = project_operation(operation, record)
        assert first == project_operation(operation, record)
        assert first["decision"] == "operator_projection_ready"
        assert set(first["record"]) == set(record)


def test_records_fail_closed_for_private_content_unknown_fields_and_paths() -> None:
    for operation, record in records().items():
        private = dict(record); private["prompt"] = "do this"
        assert project_operation(operation, private)["decision"] == "deny_unsafe_operator_record"
    unsafe = records()["dispatch"]; unsafe["worktree_ref"] = "C:/private/worktree"
    assert project_operation("dispatch", unsafe)["decision"] == "deny_unsafe_operator_record"


def test_missing_approval_denies_every_critical_action() -> None:
    for action in CRITICAL_ACTIONS:
        assert critical_action_decision(action, "task-07", None, NOW)["decision"] == "deny_missing_approval"


def test_only_current_explicit_approval_is_recorded_and_never_executes() -> None:
    result = critical_action_decision("merge", "task-07", approval(), NOW)
    assert result["decision"] == "operator_approval_recorded"
    assert set(result) == {"decision", "action", "task_id", "approval_id"}
    expired = approval(); expired["expires_at"] = "2026-09-17T08:00:00+00:00"
    assert critical_action_decision("merge", "task-07", expired, NOW)["decision"] == "deny_expired_approval"


def test_invalid_action_and_approval_records_fail_closed() -> None:
    assert critical_action_decision("launch", "task-07", approval(), NOW)["decision"] == "deny_invalid_critical_action"
    bad = approval(); bad["enabled"] = False
    assert critical_action_decision("merge", "task-07", bad, NOW)["decision"] == "deny_invalid_approval"
    bad = approval(); bad["secret"] = "nope"
    assert critical_action_decision("merge", "task-07", bad, NOW)["decision"] == "deny_invalid_approval"


def test_source_has_no_runtime_network_or_persistence_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "operator_surface.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "os.system", "socket", "requests", "urllib", "open(", "Path(", "git worktree", "time.sleep"):
        assert token not in source
