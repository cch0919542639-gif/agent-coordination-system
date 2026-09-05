from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from controlplane_admission import admit, grant_digest, validate_grant


NOW = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


def grant() -> dict[str, object]:
    value: dict[str, object] = {
        "grant_id": "grant-01", "agent_id": "agent-01", "project_id": "project-01",
        "adapter_id": "opencode", "adapter_version": "1", "allowed_task_classes": ["platform"],
        "max_concurrent_runs": 1, "worktree_root": "worktrees/agents", "network_policy": "deny",
        "expires_at": "2026-09-06T09:00:00Z", "revoked": False, "enabled": True,
    }
    value["grant_digest"] = grant_digest(value)
    return value


def task() -> dict[str, object]:
    return {"task_id": "task-01", "project_id": "project-01", "owner": "agent-01",
            "task_class": "platform", "branch": "agent/agent-01/task-01",
            "worktree_path": "worktrees/agents/task-01", "dependencies": ["dep-01"]}


def plan(**kwargs: object) -> dict[str, object]:
    options: dict[str, object] = {
        "done_task_ids": {"dep-01"}, "active_agent_ids": set(),
        "existing_owners": {}, "now": NOW,
    }
    options.update(kwargs)
    return admit(grant(), task(), **options)


def test_valid_grant_and_task_admit_without_launch() -> None:
    result = plan()
    assert result["decision"] == "admitted_no_launch"
    assert len(str(result["idempotency_key"])) == 64
    assert "branch" not in result and "credential" not in result


def test_altered_grant_digest_denies() -> None:
    value = grant(); value["grant_digest"] = "0" * 64
    assert validate_grant(value, now=NOW) == "deny_invalid_grant"


def test_revoked_and_expired_grants_deny() -> None:
    value = grant(); value["revoked"] = True; value["grant_digest"] = grant_digest(value)
    assert validate_grant(value, now=NOW) == "deny_revoked_grant"
    assert validate_grant(grant(), now=datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)) == "deny_expired_grant"


def test_grant_boolean_and_capacity_types_are_strict() -> None:
    value = grant(); value["revoked"] = "false"; value["grant_digest"] = grant_digest(value)
    assert validate_grant(value, now=NOW) == "deny_invalid_grant"
    value = grant(); value["max_concurrent_runs"] = True; value["grant_digest"] = grant_digest(value)
    assert validate_grant(value, now=NOW) == "deny_invalid_grant"


def test_capacity_dependency_and_duplicate_owner_deny() -> None:
    assert plan(active_agent_ids={"agent-01"})["decision"] == "deny_capacity"
    assert plan(done_task_ids=set())["decision"] == "deny_dependency"
    assert plan(existing_owners={"task-01": "agent-01"})["decision"] == "deny_duplicate_owner"


def test_identity_capability_and_worktree_provenance_deny() -> None:
    bad = task(); bad["owner"] = "other"
    assert admit(grant(), bad, done_task_ids={"dep-01"}, active_agent_ids=set(), existing_owners={}, now=NOW)["decision"] == "deny_identity_mismatch"
    bad = task(); bad["worktree_path"] = "worktrees/outside/task-01"
    assert admit(grant(), bad, done_task_ids={"dep-01"}, active_agent_ids=set(), existing_owners={}, now=NOW)["decision"] == "deny_worktree_provenance"


def test_unsafe_branch_and_task_class_deny() -> None:
    bad = task(); bad["branch"] = "agent\\unsafe"
    assert admit(grant(), bad, done_task_ids={"dep-01"}, active_agent_ids=set(), existing_owners={}, now=NOW)["decision"] == "deny_unsafe_provenance"
    bad = task(); bad["task_class"] = "cloud"
    assert admit(grant(), bad, done_task_ids={"dep-01"}, active_agent_ids=set(), existing_owners={}, now=NOW)["decision"] == "deny_capability"


def test_unsafe_identifiers_never_enter_success_projection() -> None:
    value = grant(); value["grant_id"] = "C:/leak"; value["grant_digest"] = grant_digest(value)
    assert validate_grant(value, now=NOW) == "deny_invalid_grant"
    bad = task(); bad["task_id"] = "../../sensitive"
    assert admit(grant(), bad, done_task_ids={"dep-01"}, active_agent_ids=set(), existing_owners={}, now=NOW)["decision"] == "deny_invalid_task"


def test_source_has_no_launch_or_io_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "controlplane_admission.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "os.system", "socket", "requests", "urllib", "open(", "Path(", "git "):
        assert token not in source
