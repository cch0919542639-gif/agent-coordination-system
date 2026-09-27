from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from threading import Event, Thread
from tempfile import TemporaryDirectory
from time import sleep


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from local_control_provision import materialize_launch_approval, provision_local_workers
import local_opencode_live_runner as runner
from opencode_live_api import normalize_permission_request
from local_opencode_live_runner import PINNED_LAUNCHER, StartAttestationState, _binding_digest, _wrapper_content_digest, reply_assigned_permission, run_assigned_task, run_live_opencode_once, session_abort_request, session_create_request, session_prompt_request, session_status_request, supervise_session


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)
WRAPPER_PATH = str(Path(__file__).resolve().parents[2] / "scripts" / "opencode_pilot_wrapper.ps1")


class FakeChild:
    pid = 4321

    def __init__(self, *, code=0, timeout=False, live=True, waiting=None, release=None):
        self.code, self.timeout, self.live = code, timeout, live
        self.waiting, self.release = waiting, release
        self.poll_count = 0

    def poll(self):
        self.poll_count += 1
        if self.waiting is not None:
            self.waiting.set()
            if self.release is not None and not self.release.is_set():
                return None
        if not self.live or (not self.timeout and self.poll_count > 1):
            self.live = False
            return self.code
        return None

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


class FakeClock:
    def __init__(self): self.value = 0.0
    def now(self): return self.value
    def sleep(self, seconds): self.value += seconds; sleep(0.001)


def invoke(*, child=None, request=None, source=None, records=None, launcher=None, state_dir=None, environment=None, pinned_digest=None, state=None, popen_failure=False, stop_marks_child=False, runtime_path=lambda: r"C:\\runtime\\opencode.cmd"):
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
        clock = FakeClock()
        def execute(path):
            return run_live_opencode_once(request, source, records, launcher or launcher_for(request), now=NOW, state_dir=path, popen=popen, provider_environment=environment or {"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]}, attestation_state=state, heartbeat=lambda: True, monotonic_clock=clock.now, sleep_fn=clock.sleep)
        if state_dir is None:
            with TemporaryDirectory() as temporary:
                result = execute(temporary)
        else:
            result = execute(str(state_dir))
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
    assert result["decision"] == "stopped_hard_ceiling" and len(calls) == 2
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
    state, release = StartAttestationState(), Event()
    entered_one, entered_two = Event(), Event()
    results = []

    def launch(number, entered):
        binding = source["bindings"][number]
        request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
        results.append(invoke(request=request, source=source, records=records, state=state, child=FakeChild(waiting=entered, release=release), environment={"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]})[0])

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


def test_live_seam_allows_each_exact_binding_once_then_denies_duplicate_or_allows_fresh_approval(tmp_path):
    source = approval()
    records = provision_local_workers(source, now=NOW)["records"]
    calls = []
    for binding in source["bindings"]:
        request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
        result, spawned = invoke(request=request, source=source, records=records, state_dir=tmp_path, environment={"OPENCODE_PROJECT_WORKTREE": request["worktree_ref"]})
        assert result["decision"] == "completed"
        calls.extend(spawned)
    assert len(list(tmp_path.glob("*.json"))) == 12
    binding = source["bindings"][0]
    request = {"task_id": source["task_id"], "run_id": source["run_id"], "approval_id": source["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    result, spawned = invoke(request=request, source=source, records=records, state_dir=tmp_path)
    assert result["decision"] == "deny_consumed_binding" and spawned == []
    second = deepcopy(source); second["run_id"] = "run-02"
    draft = {key: value for key, value in second.items() if key not in {"approval_id", "launch_time"}}
    second = materialize_launch_approval(draft, now=NOW)["approval"]
    second_records = provision_local_workers(second, now=NOW)["records"]
    binding = second["bindings"][0]
    second_request = {"task_id": second["task_id"], "run_id": second["run_id"], "approval_id": second["approval_id"], **{key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority")}}
    result, spawned = invoke(request=second_request, source=second, records=second_records, state_dir=tmp_path, environment={"OPENCODE_PROJECT_WORKTREE": second_request["worktree_ref"]})
    assert result["decision"] == "completed" and spawned
    result, spawned = invoke(request=request, source=source, records=records, state_dir=tmp_path)
    assert result["decision"] == "deny_consumed_binding" and spawned == []


def test_source_has_only_the_constrained_popen_boundary():
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "local_opencode_live_runner.py").read_text(encoding="utf-8")
    for token in ("os.environ", "getenv", "socket", "requests", "urllib", "Path(", "shell=True", "git "):
        assert token not in source
    assert "Users\\angel" not in source and "OPENCODE_WRAPPER" not in source


def assigned_card(request):
    return {"task_id": request["task_id"], "owner": request["agent_id"], "status": "IN_PROGRESS", "objective": "Implement the assigned task", "context": "Use only the approved worktree", "constraints": ["Keep scope bounded"], "allowed_scope": ["scripts/example.py"], "forbidden_scope": ["credentials"], "acceptance": ["Focused validation passes"], "validation": ["Run focused tests"]}


def test_assigned_task_is_reloaded_owner_checked_and_delivered_after_durable_claim(tmp_path):
    request, source, records = inputs()
    events = []
    def create_session(bound_request, directory):
        events.append("session")
        assert bound_request["agent_id"] == request["agent_id"]
        assert list(tmp_path.glob("*.json"))
        return {"id": "ses_task49", "directory": directory}
    def send_prompt(session_id, prompt):
        events.append("prompt")
        assert session_id == "ses_task49"
        assert "Implement the assigned task" in prompt and "worktrees/pilot/" not in prompt
        return True
    clock = FakeClock()
    resolve = lambda bound: {key: bound[key] for key in ("agent_id", "grant_id", "worktree_ref")} | {"directory": r"C:\worktrees\agent-01"}
    result = run_assigned_task(request, source, records, now=NOW, state_dir=str(tmp_path), task_loader=lambda task_id: assigned_card(request), resolve_worktree=resolve, create_session=create_session, send_prompt=send_prompt, session_state=lambda _: "completed", heartbeat=lambda _: True, abort_session=lambda _: True, monotonic_clock=clock.now, sleep_fn=clock.sleep)
    assert result["decision"] == "completed" and result["worker_session_id"] == "ses_task49"
    assert events == ["session", "prompt"]
    assert len(list(tmp_path.glob("*.json"))) == 3
    replay = run_assigned_task(request, source, records, now=NOW, state_dir=str(tmp_path), task_loader=lambda task_id: assigned_card(request), resolve_worktree=resolve, create_session=create_session, send_prompt=send_prompt, session_state=lambda _: "completed", heartbeat=lambda _: True, abort_session=lambda _: True, monotonic_clock=clock.now, sleep_fn=clock.sleep)
    assert replay["decision"] == "deny_consumed_binding" and events == ["session", "prompt"]


def test_assigned_task_denies_stale_owner_or_oversized_card_before_side_effect(tmp_path):
    request, source, records = inputs()
    calls = []
    for mutate in (lambda card: card.update(owner="agent-other"), lambda card: card.update(status="READY"), lambda card: card.update(objective="x" * 17000)):
        def loader(_):
            card = assigned_card(request); mutate(card); return card
        result = run_assigned_task(request, source, records, now=NOW, state_dir=str(tmp_path / str(len(calls))), task_loader=loader, resolve_worktree=lambda bound: {key: bound[key] for key in ("agent_id", "grant_id", "worktree_ref")} | {"directory": r"C:\worktrees\agent-01"}, create_session=lambda _bound, directory: calls.append("session") or {"id": "ses_task49", "directory": directory}, send_prompt=lambda *_: calls.append("prompt") or True, session_state=lambda _: "completed", heartbeat=lambda _: True, abort_session=lambda _: True)
        assert result["decision"] == "deny_stale_or_cross_owner_task"
    assert calls == []


def test_permission_reply_is_bound_to_current_run_and_durable_before_send(tmp_path):
    request, source, records = inputs()
    raw = {"id": "per_task49", "sessionID": "ses_task49", "permission": "bash", "patterns": ["git status"], "metadata": {}, "always": []}
    pending = normalize_permission_request(raw)
    missing_policy_state = tmp_path / "missing-policy"
    missing_clock = FakeClock()
    missing_policy_session = run_assigned_task(request, source, records, now=NOW, state_dir=str(missing_policy_state), task_loader=lambda _: assigned_card(request), resolve_worktree=lambda bound: {key: bound[key] for key in ("agent_id", "grant_id", "worktree_ref")} | {"directory": r"C:\worktrees\agent-01"}, create_session=lambda _bound, directory: {"id": "ses_task49", "directory": directory}, send_prompt=lambda *_: True, session_state=lambda _: "completed", heartbeat=lambda _: True, abort_session=lambda _: True, monotonic_clock=missing_clock.now, sleep_fn=missing_clock.sleep)
    missing_binding = missing_policy_session["worker_session_binding"]
    missing_policy = {key: request[key] for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")} | {"permissions": [{"action": pending["action"], "resource_digest": pending["resource_digest"]}]}
    missing_calls = []
    missing_result = reply_assigned_permission(request, source, records, now=NOW, state_dir=str(missing_policy_state), origin="http://127.0.0.1:4096", session_binding=missing_binding, permission_binding={**missing_binding, **pending}, task_permission_policy=missing_policy, fetch=lambda _: missing_calls.append("fetch") or [raw], send=lambda _: missing_calls.append("send") or True)
    assert missing_result["decision"] == "deny_unbound_permission" and missing_calls == []
    card = assigned_card(request)
    card["permission_policy"] = [{"action": pending["action"], "resource_digest": pending["resource_digest"]}]
    clock = FakeClock()
    session = run_assigned_task(request, source, records, now=NOW, state_dir=str(tmp_path), task_loader=lambda _: card, resolve_worktree=lambda bound: {key: bound[key] for key in ("agent_id", "grant_id", "worktree_ref")} | {"directory": r"C:\worktrees\agent-01"}, create_session=lambda _bound, directory: {"id": "ses_task49", "directory": directory}, send_prompt=lambda *_: True, session_state=lambda _: "completed", heartbeat=lambda _: True, abort_session=lambda _: True, monotonic_clock=clock.now, sleep_fn=clock.sleep)
    session_binding = session["worker_session_binding"]
    policy = {key: request[key] for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")} | {"permissions": card["permission_policy"]}
    permission_binding = {**session_binding, **pending}
    sent, fetches = [], []
    fetch = lambda origin: fetches.append(origin) or [raw]
    send = lambda payload: sent.append(payload) or True
    kwargs = {"now": NOW, "state_dir": str(tmp_path), "origin": "http://127.0.0.1:4096", "session_binding": session_binding, "permission_binding": permission_binding, "task_permission_policy": policy, "fetch": fetch, "send": send}
    foreign_binding = {**session_binding, "session_id": "ses_foreign"}
    foreign_permission = {**permission_binding, "session_id": "ses_foreign"}
    foreign = reply_assigned_permission(request, source, records, **{**kwargs, "session_binding": foreign_binding, "permission_binding": foreign_permission})
    assert foreign["decision"] == "deny_unbound_permission" and fetches == [] and sent == []
    mismatched_policy = {**policy, "permissions": [{"action": "bash", "resource_digest": "0" * 64}]}
    mismatch = reply_assigned_permission(request, source, records, **{**kwargs, "task_permission_policy": mismatched_policy})
    assert mismatch["decision"] == "deny_unbound_permission" and fetches == [] and sent == []
    outside = reply_assigned_permission(request, source, records, **{**kwargs, "origin": "http://localhost:4096"})
    assert outside["decision"] == "deny_invalid_permission" and fetches == [] and sent == []
    unapproved = {**pending, "resource_digest": "0" * 64}
    denied = reply_assigned_permission(request, source, records, **{**kwargs, "permission_binding": {**session_binding, **unapproved}})
    assert denied["decision"] == "deny_unapproved_permission" and fetches == [] and sent == []
    result = reply_assigned_permission(request, source, records, **kwargs)
    assert result["decision"] == "approved_once" and len(sent) == 1
    assert list(tmp_path.glob("*.json"))
    replay = reply_assigned_permission(request, source, records, **kwargs)
    assert replay["decision"] == "deny_consumed_permission" and len(sent) == 1


def test_v11832_session_routes_are_built_for_loopback_and_exact_directory():
    origin = "http://127.0.0.1:4096"
    created = session_create_request(origin, r"C:\worktrees\agent-01")
    assert created == {"method": "POST", "url": f"{origin}/session?directory=C%3A%5Cworktrees%5Cagent-01", "json": {}}
    prompt = session_prompt_request(origin, "ses_task49", "bounded assigned task")
    assert prompt == {"method": "POST", "url": f"{origin}/session/ses_task49/prompt_async", "json": {"parts": [{"type": "text", "text": "bounded assigned task"}]}}
    assert session_status_request(origin) == {"method": "GET", "url": f"{origin}/session/status"}
    assert session_abort_request(origin, "ses_task49") == {"method": "POST", "url": f"{origin}/session/ses_task49/abort"}
    assert session_create_request("http://localhost:4096", r"C:\worktrees\agent-01") is None
    assert session_create_request(origin, "relative/worktree") is None
    assert session_prompt_request(origin, "ses/other", "prompt") is None
    assert session_prompt_request(origin, "ses_task49", "x" * (16 * 1024 + 1)) is None
    assert session_prompt_request(origin, "ses_task49", "authorization: Bearer private-value") is None


def test_session_supervisor_uses_elapsed_heartbeat_and_aborts_only_its_session():
    request, source, _ = inputs()
    binding = source["bindings"][0]
    clock, aborted, heartbeats = FakeClock(), [], []
    result = supervise_session("ses_task49", request, binding, started_at=0.0, session_state=lambda _: "running", heartbeat=lambda session: heartbeats.append(session) or False, abort_session=lambda session: aborted.append(session) or True, monotonic_clock=clock.now, sleep_fn=clock.sleep)
    assert result["decision"] == "stopped_missed_heartbeat"
    assert aborted == ["ses_task49"] and set(heartbeats) == {"ses_task49"}
    clock, aborted = FakeClock(), []
    result = supervise_session("ses_task49", request, binding, started_at=0.0, session_state=lambda _: "running", heartbeat=lambda _: True, abort_session=lambda session: aborted.append(session) or True, monotonic_clock=clock.now, sleep_fn=clock.sleep)
    assert result["decision"] == "stopped_hard_ceiling" and aborted == ["ses_task49"]
