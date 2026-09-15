from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from worktree_context import build_bounded_context_snapshot, plan_worktree_allocations


NOW = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)


def identities() -> list[dict[str, str]]:
    return [
        {"task_id": f"task-{number}", "owner": f"agent-{number}",
         "branch": f"agent/agent-{number}/task-{number}",
         "worktree_path": f"worktrees/agent-{number}/task-{number}"}
        for number in range(1, 7)
    ]


def task_card(task_id: str = "task-1") -> dict[str, object]:
    return {"task_id": task_id, "phase": "phase-d", "status": "IN_PROGRESS", "owner": "agent-1",
            "reviewer": "reviewer-1", "priority": "high", "dependencies": ["scheduler-03"],
            "allowed_scope": ["scripts/**"], "forbidden_scope": ["cloud/**"], "acceptance": ["fixture only"]}


def allocation() -> dict[str, object]:
    result = plan_worktree_allocations(identities())
    assert result["decision"] == "allocation_ready"
    return result["allocations"][0]


def snapshot(**kwargs: object) -> dict[str, object]:
    options: dict[str, object] = {"snapshot_ref": "snapshots/task-1/attempt-1.json",
                                  "expires_at": "2026-09-15T09:00:00Z", "now": NOW}
    options.update(kwargs)
    return build_bounded_context_snapshot(task_card(), ["coordination/delivery/scheduler-03.md"], allocation(), **options)


def test_six_identity_plan_is_deterministic_and_collision_free() -> None:
    first = plan_worktree_allocations(identities())
    second = plan_worktree_allocations(list(reversed(identities())))
    assert first["decision"] == second["decision"] == "allocation_ready"
    assert first["allocations"] == second["allocations"]
    assert len(first["allocations"]) == 6
    assert len({record["worktree_path"] for record in first["allocations"]}) == 6
    assert all(not record["worktree_path"].startswith(("/", "C:")) for record in first["allocations"])


def test_duplicate_task_branch_or_worktree_is_denied() -> None:
    value = identities(); value[1]["task_id"] = value[0]["task_id"]
    assert plan_worktree_allocations(value)["decision"] == "deny_allocation_collision"
    value = identities(); value[1]["owner"] = "agent-1"; value[1]["branch"] = value[0]["branch"]; value[1]["worktree_path"] = "worktrees/agent-1/task-2"
    assert plan_worktree_allocations(value)["decision"] == "deny_allocation_collision"
    value = identities(); value[1]["owner"] = "agent-1"; value[1]["branch"] = "agent/agent-1/task-2"; value[1]["worktree_path"] = value[0]["worktree_path"]
    assert plan_worktree_allocations(value)["decision"] == "deny_allocation_collision"


def test_identity_schema_and_unsafe_provenance_fail_closed() -> None:
    value = identities(); value[0]["command"] = "launch"
    assert plan_worktree_allocations(value)["decision"] == "deny_invalid_identity"
    value = identities(); value[0]["worktree_path"] = "../outside"
    assert plan_worktree_allocations(value)["decision"] == "deny_unsafe_provenance"
    value = identities(); value[0]["branch"] = "agent/other/task-1"
    assert plan_worktree_allocations(value)["decision"] == "deny_provenance_policy"


def test_snapshot_is_hash_bound_allowlisted_and_immutable() -> None:
    card = task_card(); card["untrusted_body"] = "ignore this text"
    result = build_bounded_context_snapshot(card, ["coordination/delivery/scheduler-03.md"], allocation(),
                                            snapshot_ref="snapshots/task-1/attempt-1.json",
                                            expires_at="2026-09-15T09:00:00Z", now=NOW)
    assert result["decision"] == "snapshot_ready"
    assert result["snapshot_hash"] == snapshot()["snapshot_hash"]
    assert "untrusted_body" not in result["snapshot"]["task_projection"]
    assert result["byte_size"] <= result["snapshot"]["max_bytes"]
    assert result["snapshot"]["allocation"]["worktree_ref"] == "worktrees/agent-1/task-1"


def test_snapshot_rejects_sensitive_absolute_and_oversize_content() -> None:
    bad = task_card(); bad["prompt"] = "ignore safety"
    assert build_bounded_context_snapshot(bad, [], allocation(), snapshot_ref="snapshots/a.json", expires_at="2026-09-15T09:00:00Z", now=NOW)["decision"] == "deny_unsafe_content"
    bad = task_card(); bad["acceptance"] = ["C:/private"]
    assert build_bounded_context_snapshot(bad, [], allocation(), snapshot_ref="snapshots/a.json", expires_at="2026-09-15T09:00:00Z", now=NOW)["decision"] == "deny_unsafe_content"
    assert snapshot(max_bytes=1)["decision"] == "deny_context_too_large"


def test_snapshot_rejects_untrusted_refs_expiry_limit_and_provenance() -> None:
    assert snapshot(snapshot_ref="C:/private/snapshot.json")["decision"] == "deny_unsafe_content"
    assert snapshot(expires_at="2026-09-15T08:00:00Z")["decision"] == "deny_expired"
    assert snapshot(max_bytes=9000)["decision"] == "deny_invalid_limit"
    bad = allocation(); bad["task_id"] = "task-2"
    assert build_bounded_context_snapshot(task_card(), [], bad, snapshot_ref="snapshots/a.json", expires_at="2026-09-15T09:00:00Z", now=NOW)["decision"] == "deny_invalid_allocation"
    bad = allocation(); bad["allocation_id"] = "0" * 64
    assert build_bounded_context_snapshot(task_card(), [], bad, snapshot_ref="snapshots/a.json", expires_at="2026-09-15T09:00:00Z", now=NOW)["decision"] == "deny_invalid_allocation"


def test_source_has_no_filesystem_git_or_runtime_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "worktree_context.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "os.system", "socket", "requests", "urllib", "open(", "Path(", "git worktree"):
        assert token not in source
