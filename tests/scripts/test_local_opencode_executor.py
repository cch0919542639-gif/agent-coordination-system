from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_provision import provision_local_workers
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
        bindings.append({"agent_id": agent, "grant_id": f"grant-{agent}", "worktree_ref": f"worktrees/pilot/{agent}", "runtime_id": "opencode", "argv_allowlist": ["run", "restricted"], "timeout_seconds": 60, "stop_authority": "operator-01", "scheduler_ref": f"coordination/scheduler/{agent}", "lease_ref": f"coordination/leases/{agent}", "review_ref": f"coordination/reviews/{agent}", "manifest_digest": f"{number:064x}", "allocation_digest": f"{number + 6:064x}"})
    return {"approval_id": "approval-01", "action": "local_control_start", "task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-01", "one_shot": True, "enabled": True, "issued_at": "2026-09-18T07:00:00+00:00", "expires_at": "2026-09-18T09:00:00+00:00", "run_window_start": "2026-09-18T07:30:00+00:00", "run_window_end": "2026-09-18T08:30:00+00:00", "worktree_root": "worktrees/pilot", "bindings": bindings, "network_provider_exception": {"enabled": False, "network_access": "deny", "provider_configuration": "none", "environment_keys": []}, "prohibited_actions": ["cleanup", "credential_access", "merge", "network_activation", "push"]}


def inputs():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    binding = source["bindings"][0]
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    return request, source, records


def invoke(request=None, source=None, records=None, process=None, consumed=None, provider_environment=None):
    request, source, records = request or inputs()[0], source or inputs()[1], records or inputs()[2]
    calls, process = [], process or FakeProcess()
    def spawn(executable, argv, *, cwd_ref, env, shell):
        calls.append((executable, argv, cwd_ref, env, shell))
        return process
    result = run_opencode_once(request, source, records, now=NOW, consumed_run_ids=consumed if consumed is not None else set(), spawn=spawn, provider_environment=provider_environment)
    return result, calls, process


def test_exact_l1_record_spawns_fixed_opencode_once_with_empty_env_and_no_shell():
    result, calls, _ = invoke()
    assert result["decision"] == "completed"
    assert calls == [("opencode.exe", ("run", "restricted"), "worktrees/pilot/agent-01", {}, False)]
    assert set(result) == {"decision", "dry_run", "control_level", "task_id", "run_id", "approval_id", "agent_id", "grant_id", "runtime_id", "timeout_seconds"}


def test_invalid_runtime_cross_wiring_expiry_and_consumption_never_spawn():
    request, source, records = inputs(); request["runtime_id"] = "other"
    assert invoke(request, source, records)[0]["decision"] == "deny_runtime"
    request, source, records = inputs(); records[1]["grant_id"] = records[2]["grant_id"]
    assert invoke(request, source, records)[0]["decision"] == "deny_unbound_approval"
    request, source, records = inputs(); source["expires_at"] = "2026-09-18T08:00:00+00:00"
    assert invoke(request, source, records)[0]["decision"] == "deny_unbound_approval"
    result, calls, _ = invoke(consumed={"run-01"})
    assert result["decision"] == "deny_consumed_approval" and not calls


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
    request, source, _ = inputs()
    source["network_provider_exception"] = {"enabled": True, "network_access": "configured_model_service_only", "provider_configuration": "existing_local_only", "environment_keys": ["APPDATA", "LOCALAPPDATA", "PATH", "SYSTEMROOT", "USERPROFILE", "WINDIR"]}
    source["prohibited_actions"] = ["cleanup", "merge", "push"]
    records = provision_local_workers(source, now=NOW)["records"]
    environment = {"APPDATA": "C:\\Users\\pilot\\AppData\\Roaming", "LOCALAPPDATA": "C:\\Users\\pilot\\AppData\\Local", "PATH": "C:\\Windows\\System32", "SYSTEMROOT": "C:\\Windows", "USERPROFILE": "C:\\Users\\pilot", "WINDIR": "C:\\Windows"}
    result, calls, _ = invoke(request, source, records, provider_environment=environment)
    assert result["decision"] == "completed" and calls[0][3] == environment
    assert "C:\\Users\\pilot" not in repr(result)


def test_provider_exception_denies_default_unknown_or_credential_environment_before_spawn():
    request, source, records = inputs()
    result, calls, _ = invoke(request, source, records, provider_environment={"APPDATA": "C:\\Users\\pilot"})
    assert result["decision"] == "deny_provider_exception" and not calls
    source["network_provider_exception"] = {"enabled": True, "network_access": "configured_model_service_only", "provider_configuration": "existing_local_only", "environment_keys": ["APPDATA"]}
    source["prohibited_actions"] = ["cleanup", "merge", "push"]
    records = provision_local_workers(source, now=NOW)["records"]
    for environment in ({"OTHER": "C:\\Users\\pilot"}, {"APPDATA": "C:\\Users\\secret\\pilot"}):
        result, calls, _ = invoke(request, source, records, provider_environment=environment)
        assert result["decision"] == "deny_provider_exception" and not calls
        assert "secret" not in repr(result)


def test_timeout_stops_only_the_matching_fake_tree_after_pre_spawn_consumption():
    consumed = set()
    result, calls, process = invoke(process=FakeProcess(timeout=True), consumed=consumed)
    assert result["decision"] == "stopped_timeout" and calls and process.stopped and consumed == {"run-01"}
    consumed = set()
    result, _, _ = invoke(process=FakeProcess(timeout=True, stop_fails=True), consumed=consumed)
    assert result["decision"] == "stopped_safety_signal" and consumed == {"run-01"}


def test_source_has_no_runtime_network_filesystem_or_environment_read_apis():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_opencode_executor.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "socket", "requests", "urllib", "os.system", "open(", "Path(", "os.environ", "getenv", "shell=True"):
        assert token not in source
