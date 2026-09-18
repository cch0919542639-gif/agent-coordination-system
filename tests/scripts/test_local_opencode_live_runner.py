from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_provision import materialize_launch_approval, provision_local_workers
import local_opencode_live_runner as runner
from local_opencode_live_runner import PINNED_LAUNCHER, _wrapper_digest, run_live_opencode_once


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)


class FakeChild:
    pid = 4321

    def __init__(self, *, code=0, timeout=False):
        self.code, self.timeout = code, timeout

    def wait(self, timeout):
        if self.timeout:
            raise TimeoutError()
        return self.code


def approval():
    bindings = []
    for number in range(1, 7):
        agent = f"agent-{number:02d}"
        bindings.append({"agent_id": agent, "grant_id": f"grant-{agent}", "worktree_ref": f"worktrees/pilot/{agent}", "runtime_id": "opencode", "argv_allowlist": ["run", "restricted"], "timeout_seconds": 60, "heartbeat_interval_seconds": 5, "missed_heartbeat_threshold": 2, "per_child_hard_ceiling_seconds": 60, "stop_authority": "operator-01", "scheduler_ref": f"coordination/scheduler/{agent}", "lease_ref": f"coordination/leases/{agent}", "review_ref": f"coordination/reviews/{agent}", "manifest_digest": f"{number:064x}", "allocation_digest": f"{number + 6:064x}"})
    draft = {"action": "local_control_start", "task_id": "phase14.5-six-agent-pilot-08", "run_id": "run-01", "one_shot": True, "enabled": True, "issued_at": "2026-09-18T07:00:00+00:00", "expires_at": "2026-09-18T09:00:00+00:00", "run_window_start": "2026-09-18T07:30:00+00:00", "run_window_end": "2026-09-18T08:30:00+00:00", "worktree_root": "worktrees/pilot", "bindings": bindings, "network_provider_exception": {"enabled": True, "network_access": "configured_model_service_only", "provider_configuration": "existing_local_opaque", "environment_keys": ["OPENCODE_PROJECT_WORKTREE"]}, "prohibited_actions": ["cleanup", "merge", "push"]}
    return materialize_launch_approval(draft, now=NOW)["approval"]


def inputs():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    binding = source["bindings"][0]
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    return request, source, records


def launcher_for(request):
    return {**PINNED_LAUNCHER, "wrapper_path": r"C:\pilot\approved\opencode.ps1", "approval_id": request["approval_id"], "run_id": request["run_id"]}


def invoke(*, child=None, request=None, source=None, records=None, launcher=None, consumed=None, environment=None, pinned_digest=None):
    request, source, records = request or inputs()[0], source or inputs()[1], records or inputs()[2]
    calls, child = [], child or FakeChild()
    def popen(command, **kwargs):
        calls.append((command, kwargs))
        return FakeChild() if command[0].endswith("taskkill.exe") else child
    original = runner.PINNED_WRAPPER_PATH_DIGEST
    runner.PINNED_WRAPPER_PATH_DIGEST = pinned_digest or _wrapper_digest(r"C:\pilot\approved\opencode.ps1")
    try:
        result = run_live_opencode_once(request, source, records, launcher or launcher_for(request), now=NOW, consumed_run_ids=consumed if consumed is not None else set(), popen=popen, provider_environment=environment or {"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]})
    finally:
        runner.PINNED_WRAPPER_PATH_DIGEST = original
    return result, calls


def test_pinned_wrapper_is_the_only_shell_free_command_and_result_is_redacted():
    result, calls = invoke()
    command, kwargs = calls[0]
    assert command[:5] == (PINNED_LAUNCHER["powershell_path"], "-NoProfile", "-NonInteractive", "-File", r"C:\pilot\approved\opencode.ps1")
    assert command[-2:] == ("run", "restricted")
    assert kwargs["cwd"] == "worktrees/pilot/agent-01" and kwargs["env"] == {"OPENCODE_PROJECT_WORKTREE": "worktrees/pilot/agent-01"}
    assert kwargs["shell"] is False and kwargs["stdout"] is kwargs["stderr"]
    assert "wrapper_path" not in result and "environment" not in result and "C:\\" not in repr(result)


def test_malformed_or_changed_launcher_never_calls_popen():
    request, _, _ = inputs()
    for mutation in ({"wrapper_path": "relative.ps1"}, {"wrapper_path": r"C:\pilot\approved\opencode.ps1\.."}, {"powershell_path": "C:\\other.exe"}, {"approval_id": "wrong"}, {"extra": "x"}):
        record = launcher_for(request); record.update(mutation)
        result, calls = invoke(launcher=record)
        assert result["decision"] == "deny_invalid_launcher" and calls == []


def test_mismatched_wrapper_digest_never_calls_popen():
    request, _, _ = inputs()
    record = launcher_for(request)
    result, calls = invoke(launcher=record, pinned_digest="0" * 64)
    assert result["decision"] == "deny_invalid_launcher" and calls == []


def test_invalid_expired_replayed_or_cross_wired_input_never_calls_popen():
    request, source, records = inputs()
    expired = deepcopy(source); expired["expires_at"] = "2026-09-18T07:59:00+00:00"
    crosswired = deepcopy(request); crosswired["grant_id"] = "grant-agent-02"
    for bad_request, bad_source, consumed in ((request, expired, set()), (crosswired, source, set()), (request, source, {"run-01"})):
        result, calls = invoke(request=bad_request, source=bad_source, records=records, consumed=consumed)
        assert result["decision"].startswith("deny_") and calls == []


def test_unsafe_environment_is_denied_without_popen_or_environment_result():
    result, calls = invoke(environment={"OPENCODE_PROJECT_WORKTREE": "worktrees/pilot/agent-02"})
    assert result["decision"] == "deny_provider_exception" and calls == []
    assert "environment" not in result


def test_timeout_stops_only_the_matching_process_tree_after_one_launch():
    result, calls = invoke(child=FakeChild(timeout=True))
    assert result["decision"] == "stopped_timeout" and len(calls) == 2
    assert calls[1][0][1:] == ("/pid", "4321", "/t", "/f")
    assert calls[1][1]["shell"] is False and calls[1][1]["env"] == {}


def test_source_has_only_the_constrained_popen_boundary():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_opencode_live_runner.py").read_text(encoding="utf-8")
    for token in ("os.environ", "getenv", "socket", "requests", "urllib", "Path(", "shell=True", "git "):
        assert token not in source
    assert "Users\\angel" not in source and "OPENCODE_WRAPPER" not in source
