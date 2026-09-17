from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_provision import provision_local_workers


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)


def approval():
    bindings = []
    for number in range(1, 7):
        agent = f"agent-{number:02d}"
        bindings.append({"agent_id": agent, "grant_id": f"grant-{agent}", "worktree_ref": f"worktrees/pilot/{agent}", "runtime_id": "opencode", "argv_allowlist": ["run", "restricted"], "timeout_seconds": 60, "stop_authority": "operator-01", "scheduler_ref": f"coordination/scheduler/{agent}", "lease_ref": f"coordination/leases/{agent}", "review_ref": f"coordination/reviews/{agent}", "manifest_digest": f"{number:064x}", "allocation_digest": f"{number + 6:064x}"})
    return {"approval_id": "approval-01", "action": "local_control_start", "task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-01", "one_shot": True, "enabled": True, "issued_at": "2026-09-18T07:00:00+00:00", "expires_at": "2026-09-18T09:00:00+00:00", "run_window_start": "2026-09-18T07:30:00+00:00", "run_window_end": "2026-09-18T08:30:00+00:00", "worktree_root": "worktrees/pilot", "bindings": bindings, "prohibited_actions": ["cleanup", "credential_access", "merge", "network_activation", "push"]}


def test_exact_six_binding_records_are_deterministic_best_effort_only():
    result = provision_local_workers(approval(), now=NOW)
    assert result == provision_local_workers(approval(), now=NOW)
    assert result["decision"] == "provisioned_best_effort_no_runtime"
    records = result["records"]
    assert len(records) == 6 and {record["agent_id"] for record in records} == {f"agent-{number:02d}" for number in range(1, 7)}
    assert all(record["control_level"] == "best_effort" and record["process_tree_stop_handling"] is True for record in records)
    assert not any(key in repr(records).lower() for key in ("credential", "prompt", "transcript", "source"))


def test_bad_approval_duplicate_or_unsafe_binding_fails_closed():
    bad = approval(); bad["extra"] = True
    assert provision_local_workers(bad, now=NOW) == {"decision": "deny_invalid_approval"}
    bad = approval(); bad["bindings"][1]["agent_id"] = bad["bindings"][0]["agent_id"]
    assert provision_local_workers(bad, now=NOW) == {"decision": "deny_invalid_approval"}
    bad = approval(); bad["bindings"][0]["worktree_ref"] = "worktrees/pilot/../other"
    assert provision_local_workers(bad, now=NOW) == {"decision": "deny_invalid_approval"}
    bad = approval(); bad["prohibited_actions"] = ["cleanup"]
    assert provision_local_workers(bad, now=NOW) == {"decision": "deny_invalid_approval"}


def test_expired_or_cross_root_approval_never_returns_records():
    bad = approval(); bad["run_window_end"] = "2026-09-18T08:00:00+00:00"
    assert provision_local_workers(bad, now=NOW) == {"decision": "deny_invalid_approval"}
    bad = approval(); bad["bindings"][0]["worktree_ref"] = "worktrees/other/agent-01"
    assert provision_local_workers(bad, now=NOW) == {"decision": "deny_invalid_approval"}


def test_source_is_pure_and_never_claims_l2_enforcement():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_control_provision.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "socket", "requests", "urllib", "os.system", "open(", "Path(", "sandbox", "network_egress", "restricted_writes", "process_identity"):
        assert token not in source
