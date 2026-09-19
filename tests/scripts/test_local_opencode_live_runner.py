from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from threading import Event, Thread


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_provision import materialize_launch_approval, provision_local_workers
import local_opencode_live_runner as runner
from local_opencode_live_runner import PINNED_LAUNCHER, StartAttestationState, _binding_digest, _wrapper_content_digest, run_live_opencode_once


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
WRAPPER_PATH = str(Path(__file__).resolve().parents[2] / "scripts" / "opencode_pilot_wrapper.ps1")


class FakeChild:
    pid = 4321

    def __init__(self, *, code=0, timeout=False, live=True, waiting=None, release=None):
        self.code, self.timeout, self.live = code, timeout, live
        self.waiting, self.release = waiting, release

    def poll(self):
        return None if self.live else self.code

    def wait(self, timeout):
        if self.waiting is not None:
            self.waiting.set()
        if self.release is not None:
            assert self.release.wait(timeout=1)
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


def launcher_for(request, wrapper_path=WRAPPER_PATH):
    return {**PINNED_LAUNCHER, "wrapper_path": wrapper_path, "approval_id": request["approval_id"], "run_id": request["run_id"]}


def invoke(*, child=None, request=None, source=None, records=None, launcher=None, consumed=None, environment=None, pinned_digest=None, state=None, popen_failure=False, stop_marks_child=False, runtime_path=lambda: r"C:\\runtime\\opencode.cmd"):
    request, source, records = request or inputs()[0], source or inputs()[1], records or inputs()[2]
    calls, child = [], child or FakeChild()
    def popen(command, **kwargs):
        calls.append((command, kwargs))
        if popen_failure and not command[0].endswith("taskkill.exe"):
            raise RuntimeError("fake Popen failure")
        if command[0].endswith("taskkill.exe"):
            if stop_marks_child:
                child.live = False
            return FakeChild()
        return child
    original, original_runtime_path = runner.PINNED_WRAPPER_CONTENT_DIGEST, runner._runtime_path
    runner.PINNED_WRAPPER_CONTENT_DIGEST = pinned_digest or _wrapper_content_digest(WRAPPER_PATH)
    runner._runtime_path = runtime_path
    try:
        result = run_live_opencode_once(request, source, records, launcher or launcher_for(request), now=NOW, consumed_run_ids=consumed if consumed is not None else set(), popen=popen, provider_environment=environment or {"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]}, attestation_state=state)
    finally:
        runner.PINNED_WRAPPER_CONTENT_DIGEST, runner._runtime_path = original, original_runtime_path
    return result, calls


def test_pinned_wrapper_receives_internal_runtime_path_with_context_only_environment():
    result, calls = invoke()
    command, kwargs = calls[0]
    assert command[:5] == (PINNED_LAUNCHER["powershell_path"], "-NoProfile", "-NonInteractive", "-File", WRAPPER_PATH)
    assert command[5] == "-RuntimePath" and command[6].endswith(".cmd")
    assert command[-2:] == ("run", "restricted")
    assert kwargs["cwd"] == "worktrees/pilot/agent-01" and kwargs["env"] == {"OPENCODE_PROJECT_WORKTREE": "worktrees/pilot/agent-01"}
    assert kwargs["shell"] is False and kwargs["stdout"] is kwargs["stderr"]
    assert "wrapper_path" not in result and "environment" not in result and "C:\\" not in repr(result)
    assert result["safe_start_attestation"]["binding_digest"] == result["concurrency_projection"]["binding_digest"]
    assert "4321" not in repr(result) and "worktrees/" not in repr(result)


def test_reviewed_wrapper_content_matches_the_fixed_pin():
    assert _wrapper_content_digest(WRAPPER_PATH) == runner.PINNED_WRAPPER_CONTENT_DIGEST


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


def test_missing_or_changed_runtime_binding_denies_before_popen():
    for runtime_path in (lambda: None, lambda: ""):
        result, calls = invoke(runtime_path=runtime_path)
        assert result["decision"] == "deny_invalid_launcher" and calls == []


def test_runtime_binding_requires_the_exact_content_digest(monkeypatch, tmp_path):
    candidate = tmp_path / "opencode.cmd"
    candidate.write_bytes(b"reviewed-runtime")
    monkeypatch.setattr(runner.shutil, "which", lambda _: str(candidate))
    monkeypatch.setattr(runner, "PINNED_RUNTIME_CONTENT_DIGEST", __import__("hashlib").sha256(candidate.read_bytes()).hexdigest())
    assert runner._runtime_path() is not None
    candidate.write_bytes(b"changed-runtime")
    assert runner._runtime_path() is None


def test_changed_missing_or_unsafe_wrapper_denies_before_popen(tmp_path):
    request, _, _ = inputs()
    changed = tmp_path / "opencode_pilot_wrapper.ps1"
    changed.write_text("& opencode.exe changed\n", encoding="utf-8")
    for path in (changed, tmp_path / "missing.ps1"):
        result, calls = invoke(launcher=launcher_for(request, str(path)))
        assert result["decision"] == "deny_invalid_launcher" and calls == []
    changed.write_text("Invoke-WebRequest bad\n", encoding="utf-8")
    result, calls = invoke(launcher=launcher_for(request, str(changed)))
    assert result["decision"] == "deny_invalid_launcher" and calls == []


def test_wrapper_replaced_after_admission_denies_at_spawn_before_popen(tmp_path):
    request, source, records = inputs()
    wrapper = tmp_path / "opencode_pilot_wrapper.ps1"
    wrapper.write_bytes(Path(WRAPPER_PATH).read_bytes())
    original = runner.run_opencode_once

    def replace_then_run(*args, **kwargs):
        wrapper.write_text("Invoke-WebRequest bad\n", encoding="utf-8")
        return original(*args, **kwargs)

    runner.run_opencode_once = replace_then_run
    try:
        result, calls = invoke(request=request, source=source, records=records, launcher=launcher_for(request, str(wrapper)))
    finally:
        runner.run_opencode_once = original
    assert result["decision"] == "stopped_safety_signal" and calls == []
    assert "safe_start_attestation" not in result and "concurrency_projection" not in result


def test_runtime_replaced_after_admission_denies_at_spawn_before_popen():
    original = runner.run_opencode_once

    def remove_then_run(*args, **kwargs):
        runner._runtime_path = lambda: None
        return original(*args, **kwargs)

    runner.run_opencode_once = remove_then_run
    try:
        result, calls = invoke()
    finally:
        runner.run_opencode_once = original
    assert result["decision"] == "stopped_safety_signal" and calls == []
    assert "safe_start_attestation" not in result and "concurrency_projection" not in result


def test_invalid_expired_replayed_or_cross_wired_input_never_calls_popen():
    request, source, records = inputs()
    expired = deepcopy(source); expired["expires_at"] = "2026-09-18T07:59:00+00:00"
    crosswired = deepcopy(request); crosswired["grant_id"] = "grant-agent-02"
    for bad_request, bad_source in ((request, expired), (crosswired, source)):
        result, calls = invoke(request=bad_request, source=bad_source, records=records)
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


def test_prespawn_denial_popen_failure_or_nonlive_child_emit_no_start_attestation():
    request, _, _ = inputs()
    bad_launcher = launcher_for(request); bad_launcher["approval_id"] = "wrong"
    denied, denied_calls = invoke(launcher=bad_launcher)
    popen_failed, failed_calls = invoke(popen_failure=True)
    nonlive, nonlive_calls = invoke(child=FakeChild(live=False))
    for result in (denied, popen_failed, nonlive):
        assert "safe_start_attestation" not in result and "concurrency_projection" not in result
        assert result["decision"].startswith("deny_") or result["decision"] == "stopped_safety_signal"
    assert denied_calls == [] and len(failed_calls) == len(nonlive_calls) == 1


def test_start_registration_collision_stops_the_matching_live_child_without_attestation():
    request, _, _ = inputs()
    state, child = StartAttestationState(), FakeChild()
    state.start(_binding_digest(request))
    result, calls = invoke(state=state, child=child, stop_marks_child=True)
    assert result["decision"] == "stopped_safety_signal"
    assert "safe_start_attestation" not in result and "concurrency_projection" not in result
    assert len(calls) == 2 and calls[1][0][1:] == ("/pid", "4321", "/t", "/f")
    assert child.live is False


def test_shared_state_projects_monotonic_overlapping_live_starts_without_child_identity_leakage():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    state, consumed, release = StartAttestationState(), set(), Event()
    entered_one, entered_two = Event(), Event()
    results = []

    def launch(number, entered):
        binding = source["bindings"][number]
        request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
        results.append(invoke(request=request, source=source, records=records, consumed=consumed, state=state, child=FakeChild(waiting=entered, release=release), environment={"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]})[0])

    first = Thread(target=launch, args=(0, entered_one)); first.start()
    assert entered_one.wait(timeout=1)
    second = Thread(target=launch, args=(1, entered_two)); second.start()
    assert entered_two.wait(timeout=1)
    release.set(); first.join(timeout=1); second.join(timeout=1)
    assert not first.is_alive() and not second.is_alive()
    projected = sorted(results, key=lambda item: item["concurrency_projection"]["launch_order"])
    first_projection, second_projection = (item["concurrency_projection"] for item in projected)
    assert first_projection["launch_order"] == 1 and first_projection["overlap_count"] == 0
    assert second_projection["launch_order"] == 2 and second_projection["overlap_count"] == 1
    assert second_projection["overlaps_binding_digests"] == (first_projection["binding_digest"],)
    assert all("4321" not in repr(item) and "worktrees/" not in repr(item) for item in results)


def test_live_seam_allows_each_exact_binding_once_then_denies_duplicate_or_second_pilot_without_popen():
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    consumed, calls = set(), []
    for binding in source["bindings"]:
        request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
        result, spawned = invoke(request=request, source=source, records=records, consumed=consumed, environment={"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]})
        assert result["decision"] == "completed"
        calls.extend(spawned)
    assert len(consumed) == len(calls) + 1 == 7
    binding = source["bindings"][0]
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    result, spawned = invoke(request=request, source=source, records=records, consumed=consumed)
    assert result["decision"] == "deny_consumed_binding" and spawned == []
    second = deepcopy(source); second["run_id"] = "run-02"
    draft = {key: value for key, value in second.items() if key not in {"approval_id", "launch_time"}}
    second = materialize_launch_approval(draft, now=NOW)["approval"]
    second_records = provision_local_workers(second, now=NOW)["records"]
    binding = second["bindings"][0]
    second_request = {"task_id": second["task_id"], "run_id": second["run_id"], "approval_id": second["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    result, spawned = invoke(request=second_request, source=second, records=second_records, consumed=consumed, environment={"OPENCODE_PROJECT_WORKTREE": second_request["worktree_ref"]})
    assert result["decision"] == "deny_consumed_approval" and spawned == []
    result, spawned = invoke(request=request, source=source, records=records, consumed=consumed)
    assert result["decision"] == "deny_consumed_binding" and spawned == []


def test_source_has_only_the_constrained_popen_boundary():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_opencode_live_runner.py").read_text(encoding="utf-8")
    for token in ("os.environ", "getenv", "socket", "requests", "urllib", "Path(", "shell=True", "git "):
        assert token not in source
    assert "Users\\angel" not in source and "OPENCODE_WRAPPER" not in source
