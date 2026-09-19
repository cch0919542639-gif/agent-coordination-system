from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_provision import materialize_launch_approval, provision_local_workers
from local_opencode_executor import run_opencode_once


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)


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


def approval():
    bindings = []
    for number in range(1, 7):
        agent = f"agent-{number:02d}"
        bindings.append({"agent_id": agent, "grant_id": f"grant-{agent}", "worktree_ref": f"worktrees/pilot/{agent}", "runtime_id": "opencode", "argv_allowlist": ["run", "restricted"], "timeout_seconds": 60, "heartbeat_interval_seconds": 5, "missed_heartbeat_threshold": 2, "per_child_hard_ceiling_seconds": 60, "stop_authority": "operator-01", "scheduler_ref": f"coordination/scheduler/{agent}", "lease_ref": f"coordination/leases/{agent}", "review_ref": f"coordination/reviews/{agent}", "manifest_digest": f"{number:064x}", "allocation_digest": f"{number + 6:064x}"})
    draft = {"action": "local_control_start", "task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-01", "one_shot": True, "enabled": True, "issued_at": "2026-09-18T07:00:00+00:00", "expires_at": "2026-09-18T09:00:00+00:00", "run_window_start": "2026-09-18T07:30:00+00:00", "run_window_end": "2026-09-18T08:30:00+00:00", "worktree_root": "worktrees/pilot", "bindings": bindings, "network_provider_exception": {"enabled": False, "network_access": "deny", "provider_configuration": "none", "environment_keys": []}, "prohibited_actions": ["cleanup", "credential_access", "merge", "network_activation", "push"]}
    return materialize_launch_approval(draft, now=NOW)["approval"]


def inputs():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    binding = source["bindings"][0]
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    return request, source, records


def enabled_inputs():
    request, source, _ = inputs()
    source["network_provider_exception"] = {"enabled": True, "network_access": "configured_model_service_only", "provider_configuration": "existing_local_opaque", "environment_keys": ["OPENCODE_PROJECT_WORKTREE"]}
    source["prohibited_actions"] = ["cleanup", "merge", "push"]
    draft = {key: value for key, value in source.items() if key not in {"approval_id", "launch_time"}}
    source = materialize_launch_approval(draft, now=NOW)["approval"]
    request["approval_id"] = source["approval_id"]
    return request, source, provision_local_workers(source, now=NOW)["records"], {"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]}


def invoke(request=None, source=None, records=None, process=None, consumed=None, provider_environment=None, supervision_checks=(), health_check=None):
    request, source, records = request or inputs()[0], source or inputs()[1], records or inputs()[2]
    calls, process = [], process or FakeProcess()
    def spawn(executable, argv, *, cwd_ref, env, shell):
        calls.append((executable, argv, cwd_ref, env, shell))
        return process
    result = run_opencode_once(request, source, records, now=NOW, consumed_run_ids=consumed if consumed is not None else set(), spawn=spawn, provider_environment=provider_environment, supervision_checks=supervision_checks, health_check=health_check)
    return result, calls, process


def test_exact_l1_record_spawns_pinned_opencode_once_with_empty_env_and_no_shell():
    result, calls, _ = invoke()
    assert result["decision"] == "completed"
    assert calls == [("opencode", ("run", "restricted"), "worktrees/pilot/agent-01", {}, False)]
    assert set(result) == {"decision", "dry_run", "control_level", "task_id", "run_id", "approval_id", "agent_id", "grant_id", "runtime_id", "timeout_seconds"}


def test_invalid_runtime_cross_wiring_and_expiry_never_spawn():
    request, source, records = inputs(); request["runtime_id"] = "other"
    assert invoke(request, source, records)[0]["decision"] == "deny_runtime"
    request, source, records = inputs(); records[1]["grant_id"] = records[2]["grant_id"]
    assert invoke(request, source, records)[0]["decision"] == "deny_unbound_approval"
    request, source, records = inputs(); source["expires_at"] = "2026-09-18T08:00:00+00:00"
    assert invoke(request, source, records)[0]["decision"] == "deny_unbound_approval"


def test_credential_or_network_bearing_requests_deny_before_spawn_and_stay_redacted():
    for field, value in (("agent_id", "agent-token"), ("argv_allowlist", ["network_activation"])):
        request, source, records = inputs(); request[field] = value
        result, calls, _ = invoke(request, source, records)
        assert result["decision"].startswith("deny_") and not calls
        assert (value if isinstance(value, str) else value[0]) not in repr(result)
    request, source, records = inputs(); request["network_activation"] = True
    result, calls, _ = invoke(request, source, records)
    assert result["decision"] == "deny_invalid_request" and not calls


def test_exact_provider_exception_passes_only_opaque_allowlisted_environment():
    request, source, records, environment = enabled_inputs()
    result, calls, _ = invoke(request, source, records, provider_environment=environment)
    assert result["decision"] == "completed" and calls[0][3] == environment
    assert "OPENCODE_PROJECT_WORKTREE" not in repr(result)


def test_provider_exception_denies_default_unknown_or_credential_environment_before_spawn():
    request, source, records = inputs()
    result, calls, _ = invoke(request, source, records, provider_environment={"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]})
    assert result["decision"] == "deny_provider_exception" and not calls
    request, source, records, _ = enabled_inputs()
    for environment in ({"OTHER": request["worktree_ref"]}, {"OPENCODE_PROJECT_WORKTREE": "worktrees/pilot/agent-02"}):
        result, calls, _ = invoke(request, source, records, provider_environment=environment)
        assert result["decision"] == "deny_provider_exception" and not calls
        assert "secret" not in repr(result)


def test_enabled_exception_stale_replayed_and_cross_wired_records_never_spawn_or_leak_environment():
    request, source, records, environment = enabled_inputs()
    source["expires_at"] = "2026-09-18T08:00:00+00:00"
    result, calls, _ = invoke(request, source, records, provider_environment=environment)
    assert result["decision"] == "deny_unbound_approval" and not calls and environment["OPENCODE_PROJECT_WORKTREE"] not in repr(result)
    request, source, records, environment = enabled_inputs()
    consumed = set()
    invoke(request, source, records, consumed=consumed, provider_environment=environment)
    result, calls, _ = invoke(request, source, records, consumed=consumed, provider_environment=environment)
    assert result["decision"] == "deny_consumed_binding" and not calls and environment["OPENCODE_PROJECT_WORKTREE"] not in repr(result)
    request, source, records, environment = enabled_inputs()
    records[1]["grant_id"] = records[2]["grant_id"]
    result, calls, _ = invoke(request, source, records, provider_environment=environment)
    assert result["decision"] == "deny_unbound_approval" and not calls and environment["OPENCODE_PROJECT_WORKTREE"] not in repr(result)


def test_provider_exception_denies_credential_like_environment_key_without_leak():
    request, source, records, _ = enabled_inputs()
    environment = {"API_KEY": "private-provider-value"}
    result, calls, _ = invoke(request, source, records, provider_environment=environment)
    assert result["decision"] == "deny_provider_exception" and not calls
    assert "API_KEY" not in repr(result) and "private-provider-value" not in repr(result)


def test_timeout_stops_only_the_matching_fake_tree_after_pre_spawn_consumption():
    consumed = set()
    result, calls, process = invoke(process=FakeProcess(timeout=True), consumed=consumed)
    assert result["decision"] == "stopped_timeout" and calls and process.stopped and consumed
    consumed = set()
    result, _, _ = invoke(process=FakeProcess(timeout=True, stop_fails=True), consumed=consumed)
    assert result["decision"] == "stopped_safety_signal" and consumed


def test_renewable_lease_supervision_stops_only_missed_or_unhealthy_fake_child():
    request, source, records = inputs()
    missed = NOW.replace(second=11)
    result, calls, process = invoke(request, source, records, supervision_checks=(missed,))
    assert result["decision"] == "stopped_missed_heartbeat" and calls and process.stopped
    request, source, records = inputs()
    result, calls, process = invoke(request, source, records, supervision_checks=(missed,), health_check=lambda _: False)
    assert result["decision"] == "stopped_health_check" and calls and process.stopped
    request, source, records = inputs()
    result, calls, process = invoke(request, source, records, supervision_checks=(NOW.replace(second=9),), health_check=lambda _: True)
    assert result["decision"] == "completed" and calls and not process.stopped


def test_hard_ceiling_stops_one_fake_child_without_retry_after_consumption():
    consumed = set()
    request, source, records = inputs()
    result, calls, process = invoke(request, source, records, consumed=consumed, supervision_checks=(NOW.replace(minute=1),))
    assert result["decision"] == "stopped_hard_ceiling" and calls and process.stopped
    assert consumed and len(calls) == 1


def test_one_pilot_admission_fences_all_six_bindings_once_and_denies_replays_before_spawn():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    consumed, calls = set(), []
    for binding in source["bindings"]:
        request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
        result, spawned, _ = invoke(request, source, records, consumed=consumed)
        assert result["decision"] == "completed"
        calls.extend(spawned)
    assert len(consumed) == len(calls) + 1 == 7
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: source["bindings"][0][key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    result, spawned, _ = invoke(request, source, records, consumed=consumed)
    assert result["decision"] == "deny_consumed_binding" and spawned == []
    foreign = deepcopy(request); foreign["agent_id"] = "agent-07"
    result, spawned, _ = invoke(foreign, source, records, consumed=consumed)
    assert result["decision"] == "deny_unbound_approval" and spawned == []
    second = deepcopy(source); second["run_id"] = "run-02"
    draft = {key: value for key, value in second.items() if key not in {"approval_id", "launch_time"}}
    second = materialize_launch_approval(draft, now=NOW)["approval"]
    second_records = provision_local_workers(second, now=NOW)["records"]
    second_request = {"task_id": second["task_id"], "run_id": second["run_id"], "approval_id": second["approval_id"], **{key: second["bindings"][0][key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    result, spawned, _ = invoke(second_request, second, second_records, consumed=consumed)
    assert result["decision"] == "deny_consumed_approval" and spawned == []
    restarted_state = consumed
    result, spawned, _ = invoke(request, source, records, consumed=restarted_state)
    assert result["decision"] == "deny_consumed_binding" and spawned == []


def test_source_has_no_runtime_network_filesystem_or_environment_read_apis():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_opencode_executor.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "socket", "requests", "urllib", "os.system", "open(", "Path(", "os.environ", "getenv", "shell=True"):
        assert token not in source
