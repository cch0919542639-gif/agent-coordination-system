from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_adapter import run_local_once
from local_control_provision import materialize_launch_approval, provision_local_workers


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)


def approval():
    bindings = []
    for number in range(1, 7):
        agent = f"agent-{number:02d}"
        bindings.append({"agent_id": agent, "grant_id": f"grant-{agent}", "worktree_ref": f"worktrees/pilot/{agent}", "runtime_id": "opencode", "argv_allowlist": ["run", "restricted"], "timeout_seconds": 60, "heartbeat_interval_seconds": 5, "missed_heartbeat_threshold": 2, "per_child_hard_ceiling_seconds": 60, "stop_authority": "operator-01", "scheduler_ref": f"coordination/scheduler/{agent}", "lease_ref": f"coordination/leases/{agent}", "review_ref": f"coordination/reviews/{agent}", "manifest_digest": f"{number:064x}", "allocation_digest": f"{number + 6:064x}"})
    draft = {"action": "local_control_start", "task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-01", "one_shot": True, "enabled": True, "issued_at": "2026-09-18T07:00:00+00:00", "expires_at": "2026-09-18T09:00:00+00:00", "run_window_start": "2026-09-18T07:30:00+00:00", "run_window_end": "2026-09-18T08:30:00+00:00", "worktree_root": "worktrees/pilot", "bindings": bindings, "network_provider_exception": {"enabled": False, "network_access": "deny", "provider_configuration": "none", "environment_keys": []}, "prohibited_actions": ["cleanup", "credential_access", "merge", "network_activation", "push"]}
    return materialize_launch_approval(draft, now=NOW)["approval"]


class FakeProcess:
    def __init__(self, *, code=0, timeout=False, stop_fails=False):
        self.code, self.timeout, self.stop_fails, self.stopped = code, timeout, stop_fails, False

    def wait(self, timeout):
        if self.timeout:
            raise TimeoutError()
        return self.code

    def terminate_tree(self):
        self.stopped = True
        if self.stop_fails:
            raise RuntimeError()


def inputs():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    binding = source["bindings"][0]
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    return request, source, records


def invoke(request=None, source=None, records=None, process=None, consumed=None):
    original = inputs()
    request, source, records = request or original[0], source or original[1], records or original[2]
    calls, process = [], process or FakeProcess()
    result = run_local_once(request, source, records, now=NOW, consumed_run_ids=consumed if consumed is not None else set(), process_factory=lambda: calls.append(True) or process)
    return result, calls, process


def test_verified_request_has_one_fake_call_and_bounded_best_effort_evidence():
    result, calls, _ = invoke()
    assert result["decision"] == "completed" and calls == [True]
    assert result["control_level"] == "best_effort" and "argv_allowlist" not in result
    assert not any(key in repr(result).lower() for key in ("credential", "prompt", "transcript", "source"))


def test_consumed_expired_and_cross_wired_paths_never_call_factory():
    result, calls, _ = invoke(consumed={"run-01"})
    assert result["decision"] == "deny_consumed_approval" and not calls
    request, source, records = inputs(); source["expires_at"] = "2026-09-18T08:00:00+00:00"
    assert invoke(request, source, records)[0]["decision"] == "deny_unbound_approval"
    request, source, records = inputs(); request["argv_allowlist"] = ["other"]
    assert invoke(request, source, records)[0]["decision"] == "deny_unbound_approval"


def test_malformed_and_duplicate_records_never_call_factory():
    request, source, records = inputs(); request["worktree_ref"] = "worktrees/pilot/../agent-01"
    assert invoke(request, source, records)[0] == {"decision": "deny_invalid_request", "dry_run": True}
    request, source, records = inputs(); records[1] = deepcopy(records[0])
    result, calls, _ = invoke(request, source, records)
    assert result["decision"] == "deny_unbound_approval" and not calls


def test_cross_wired_non_selected_record_never_calls_factory_or_leaks_it():
    request, source, records = inputs()
    records[1]["grant_id"] = records[2]["grant_id"]
    result, calls, _ = invoke(request, source, records)
    assert result["decision"] == "deny_unbound_approval" and not calls
    assert records[1]["grant_id"] not in repr(result)


def test_every_non_selected_record_binding_field_denies_before_factory():
    for key, value in (("worktree_ref", "worktrees/pilot/other"), ("task_id", "other-task"), ("run_id", "other-run"), ("approval_id", "other-approval"), ("scheduler_ref", "coordination/scheduler/other")):
        request, source, records = inputs()
        records[1][key] = value
        result, calls, _ = invoke(request, source, records)
        assert result["decision"] == "deny_unbound_approval" and not calls
        assert value not in repr(result)
    request, source, records = inputs(); records[0]["extra"] = True
    result, calls, _ = invoke(request, source, records)
    assert result["decision"] == "deny_unbound_approval" and not calls


def test_timeout_stops_only_injected_process_and_consumes_approval():
    consumed = set(); result, calls, process = invoke(process=FakeProcess(timeout=True), consumed=consumed)
    assert result["decision"] == "stopped_timeout" and calls == [True] and process.stopped and consumed == {"run-01"}
    consumed = set(); result, _, _ = invoke(process=FakeProcess(timeout=True, stop_fails=True), consumed=consumed)
    assert result["decision"] == "stopped_safety_signal" and consumed == {"run-01"}


def test_source_has_no_operational_runtime_network_or_l2_claim():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_control_adapter.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "socket", "requests", "urllib", "os.system", "open(", "Path(", "sandbox", "network_egress", "restricted_writes", "process_identity"):
        assert token not in source
