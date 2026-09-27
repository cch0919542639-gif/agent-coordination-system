"""L1 live OpenCode seam; callers must supply the exact reviewed launcher."""

from __future__ import annotations

import ntpath
import subprocess
import hashlib
import json
import re
import shutil
import threading
from datetime import datetime
from time import monotonic, sleep
from typing import Callable, Mapping

from local_opencode_executor import Process, Spawn, run_opencode_once
from local_control_provision import validate_approval
from local_control_adapter import _bound, _request
from one_shot_consumption import consume_once, has_claim
from opencode_live_api import FORBIDDEN_CONTENT, build_task_prompt, select_pending_permission
from opencode_loopback_permission_adapter import reply_loopback_once
from local_opencode_executor import _binding_for


POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
TASKKILL = r"C:\Windows\System32\taskkill.exe"
LAUNCHER_FIELDS = frozenset({"runtime_id", "powershell_path", "wrapper_path", "launcher_id", "approval_id", "run_id"})
PINNED_LAUNCHER = {"runtime_id": "opencode", "powershell_path": POWERSHELL, "launcher_id": "opencode-powershell-wrapper-v1"}
PINNED_WRAPPER_CONTENT_DIGEST = "c16dd5bee4f723e0044f724d2a5bd8e56005175223766d81bd2395660d3667d7"
PINNED_RUNTIME_CONTENT_DIGEST = "b53b698473bfa46e09487e485a7f1ad5b4881f8a8b319d3619aa251f3be8ae10"


Popen = Callable[..., object]


class StartAttestationState:
    """In-memory, caller-owned safe ordering state for one pilot attempt."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_order = 0
        self._active: set[str] = set()

    def start(self, binding_digest: str) -> tuple[dict[str, object], dict[str, object]]:
        with self._lock:
            if binding_digest in self._active:
                raise ValueError("duplicate active binding")
            self._next_order += 1
            overlaps = tuple(sorted(self._active))
            self._active.add(binding_digest)
            attestation = {"schema_version": "phase14.5-start-v1", "binding_digest": binding_digest, "launch_order": self._next_order}
            projection = {"schema_version": "phase14.5-concurrency-v1", "binding_digest": binding_digest, "launch_order": self._next_order, "overlap_count": len(overlaps), "overlaps_binding_digests": overlaps}
        return attestation, projection

    def finish(self, binding_digest: str) -> None:
        with self._lock:
            self._active.discard(binding_digest)


def run_live_opencode_once(request: object, approval: object, records: object, launcher: object, *, now: datetime, state_dir: str, popen: Popen = subprocess.Popen, provider_environment: object = None, attestation_state: StartAttestationState | None = None, heartbeat: Callable[[], bool] | None = None, health_check: Callable[[Process], bool] | None = None, monotonic_clock: Callable[[], float] | None = None, sleep_fn: Callable[[float], None] | None = None) -> dict[str, object]:
    """Start one reviewed request through the pinned PowerShell wrapper only."""
    if not _launcher(launcher, request):
        return {"decision": "deny_invalid_launcher", "dry_run": True, "control_level": "best_effort"}
    assert isinstance(launcher, Mapping)
    if not isinstance(request, Mapping):
        return {"decision": "deny_invalid_request", "dry_run": True, "control_level": "best_effort"}
    captured: list[tuple[dict[str, object], dict[str, object]]] = []
    executor_options: dict[str, object] = {"heartbeat": heartbeat}
    if health_check is not None:
        executor_options["health_check"] = health_check
    if monotonic_clock is not None:
        executor_options["monotonic_clock"] = monotonic_clock
    if sleep_fn is not None:
        executor_options["sleep_fn"] = sleep_fn
    result = run_opencode_once(request, approval, records, now=now, state_dir=state_dir, spawn=_spawn(popen, str(launcher["wrapper_path"]), request, attestation_state or StartAttestationState(), captured), provider_environment=provider_environment, **executor_options)
    if captured:
        result["safe_start_attestation"], result["concurrency_projection"] = captured[0]
    return result


TASK_CARD_FIELDS = frozenset({"task_id", "owner", "status", "objective", "context", "constraints", "allowed_scope", "forbidden_scope", "acceptance", "validation"})
CreateSession = Callable[[Mapping[str, object], str], object]
SendPrompt = Callable[[str, str], bool]
TaskLoader = Callable[[str], object]
WorktreeResolver = Callable[[Mapping[str, object]], object]
SessionState = Callable[[str], str]
SessionHeartbeat = Callable[[str], bool]
AbortSession = Callable[[str], bool]


def session_create_request(origin: object, directory: object) -> dict[str, object] | None:
    """Build the v1.18.32 POST /session request routed to one absolute worktree."""
    if not _loopback_origin(origin) or not isinstance(directory, str) or not ntpath.isabs(directory) or ntpath.normpath(directory) != directory or any(char in directory for char in "\x00\r\n"):
        return None
    return {"method": "POST", "url": f"{origin}/session?directory={_url_component(directory)}", "json": {}}


def session_prompt_request(origin: object, session_id: object, prompt: object) -> dict[str, object] | None:
    """Build the v1.18.32 async prompt request; this function performs no I/O."""
    if not _loopback_origin(origin) or not _safe_api_id(session_id, "ses") or not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > 16 * 1024 or FORBIDDEN_CONTENT.search(prompt):
        return None
    return {"method": "POST", "url": f"{origin}/session/{session_id}/prompt_async", "json": {"parts": [{"type": "text", "text": prompt}]}}


def session_status_request(origin: object) -> dict[str, object] | None:
    if not _loopback_origin(origin):
        return None
    return {"method": "GET", "url": f"{origin}/session/status"}


def session_abort_request(origin: object, session_id: object) -> dict[str, object] | None:
    if not _loopback_origin(origin) or not _safe_api_id(session_id, "ses"):
        return None
    return {"method": "POST", "url": f"{origin}/session/{session_id}/abort"}


def run_assigned_task(request: object, approval: object, records: object, *, now: datetime, state_dir: str, task_loader: TaskLoader, resolve_worktree: WorktreeResolver, create_session: CreateSession, send_prompt: SendPrompt, session_state: SessionState, heartbeat: SessionHeartbeat, abort_session: AbortSession, monotonic_clock: Callable[[], float] = monotonic, sleep_fn: Callable[[float], None] = sleep, poll_interval: float = 0.25) -> dict[str, object]:
    """Reload an assigned card, send it to one pinned session, then supervise it."""
    if not isinstance(request, Mapping) or not isinstance(approval, Mapping) or not validate_approval(approval, now=now) or _binding_for(request, approval) is None or not _request(request) or not _bound(request, approval, records):
        return _safe_stop("deny_unbound_approval", request)
    if not all(callable(value) for value in (task_loader, resolve_worktree, create_session, send_prompt, session_state, heartbeat, abort_session, monotonic_clock, sleep_fn)) or type(poll_interval) not in (int, float) or not 0 < poll_interval <= 1:
        return _safe_stop("deny_supervision_unavailable", request)
    try:
        card = task_loader(str(request["task_id"]))
    except Exception:
        return _safe_stop("deny_task_unavailable", request)
    prompt = _assigned_prompt(card, request)
    if prompt is None:
        return _safe_stop("deny_stale_or_cross_owner_task", request)
    permissions = _task_permission_policy(card)
    if permissions is None:
        return _safe_stop("deny_stale_or_cross_owner_task", request)
    try:
        resolution = resolve_worktree(request)
    except Exception:
        resolution = None
    if not isinstance(resolution, Mapping) or set(resolution) != {"agent_id", "grant_id", "worktree_ref", "directory"} or any(resolution.get(key) != request.get(key) for key in ("agent_id", "grant_id", "worktree_ref")):
        return _safe_stop("deny_unpinned_worktree", request)
    directory = resolution.get("directory")
    if not isinstance(directory, str) or not ntpath.isabs(directory) or ntpath.normpath(directory) != directory or any(char in directory for char in "\x00\r\n"):
        return _safe_stop("deny_unpinned_worktree", request)
    identity = {key: str(request[key]) for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref")}
    if not consume_once(state_dir, "binding", identity):
        return _safe_stop("deny_consumed_binding", request)
    if not consume_once(state_dir, "approval", identity):
        return _safe_stop("deny_consumed_approval", request)
    started_at = monotonic_clock()
    try:
        session = create_session(request, directory)
    except Exception:
        session = None
    if not isinstance(session, Mapping) or set(session) != {"id", "directory"} or session.get("directory") != directory or not _safe_api_id(session.get("id"), "ses"):
        return _safe_stop("stopped_session_creation", request)
    session_id = str(session["id"])
    session_identity = _session_claim_identity(request, session_id, permissions)
    if not consume_once(state_dir, "session", session_identity):
        return _stop_session_result("stopped_session_binding", request, session_id, abort_session)
    binding = _binding_for(request, approval)
    assert binding is not None
    if monotonic_clock() - started_at >= min(int(binding["timeout_seconds"]), int(binding["per_child_hard_ceiling_seconds"])):
        reason = "stopped_timeout" if int(binding["timeout_seconds"]) < int(binding["per_child_hard_ceiling_seconds"]) else "stopped_hard_ceiling"
        return _stop_session_result(reason, request, session_id, abort_session)
    try:
        delivered = send_prompt(session_id, prompt)
    except Exception:
        delivered = False
    if delivered is not True:
        return _stop_session_result("stopped_task_delivery", request, session_id, abort_session)
    return supervise_session(session_id, request, binding, started_at=started_at, session_state=session_state, heartbeat=heartbeat, abort_session=abort_session, monotonic_clock=monotonic_clock, sleep_fn=sleep_fn, poll_interval=poll_interval)


def supervise_session(session_id: str, request: Mapping[str, object], binding: Mapping[str, object], *, started_at: float, session_state: SessionState, heartbeat: SessionHeartbeat, abort_session: AbortSession, monotonic_clock: Callable[[], float], sleep_fn: Callable[[float], None], poll_interval: float = 0.25) -> dict[str, object]:
    """Supervise an asynchronous OpenCode session against monotonic lease deadlines."""
    if not _safe_api_id(session_id, "ses") or type(poll_interval) not in (int, float) or not 0 < poll_interval <= 1:
        return _stop_session_result("stopped_invalid_supervision", request, session_id, abort_session)
    interval = int(binding["heartbeat_interval_seconds"])
    missed = int(binding["missed_heartbeat_threshold"])
    timeout = int(binding["timeout_seconds"])
    ceiling = int(binding["per_child_hard_ceiling_seconds"])
    stop_after = min(timeout, ceiling)
    stop_reason = "stopped_timeout" if timeout < ceiling else "stopped_hard_ceiling"
    last_heartbeat = started_at
    next_heartbeat = started_at + interval
    while True:
        current = monotonic_clock()
        if current < started_at:
            return _stop_session_result("stopped_invalid_supervision", request, session_id, abort_session)
        if current - started_at >= stop_after:
            return _stop_session_result(stop_reason, request, session_id, abort_session)
        try:
            state = session_state(session_id)
        except Exception:
            state = "unavailable"
        if state == "completed":
            return _session_result("completed", request, session_id)
        if state == "failed":
            return _session_result("stopped_worker_failed", request, session_id)
        if state != "running":
            return _stop_session_result("stopped_session_state_unavailable", request, session_id, abort_session)
        if current >= next_heartbeat:
            try:
                if heartbeat(session_id):
                    last_heartbeat = current
            except Exception:
                pass
            next_heartbeat = current + interval
        if current - last_heartbeat >= interval * missed:
            return _stop_session_result("stopped_missed_heartbeat", request, session_id, abort_session)
        sleep_fn(min(poll_interval, max(0.0, min(next_heartbeat, started_at + stop_after) - current)))


def reply_assigned_permission(request: object, approval: object, records: object, *, now: datetime, state_dir: str, origin: object, session_binding: object, permission_binding: object, task_permission_policy: object, fetch: Callable[[str], object], send: Callable[[dict[str, object]], bool]) -> dict[str, object]:
    """Durably fence an exact current permission before its injected one-time reply."""
    if not isinstance(request, Mapping) or not isinstance(approval, Mapping) or not validate_approval(approval, now=now) or not _binding_for(request, approval) or not _request(request) or not _bound(request, approval, records):
        return _safe_stop("deny_unbound_approval", request)
    session_fields = {"task_id", "run_id", "approval_id", "agent_id", "grant_id", "session_id"}
    permission_fields = session_fields | {"permission_id", "action", "resource_digest"}
    if not isinstance(session_binding, Mapping) or set(session_binding) != session_fields or not isinstance(permission_binding, Mapping) or set(permission_binding) != permission_fields:
        return _safe_stop("deny_unbound_permission", request)
    policy_fields = {"task_id", "run_id", "approval_id", "agent_id", "grant_id", "permissions"}
    if not isinstance(task_permission_policy, Mapping) or set(task_permission_policy) != policy_fields or any(task_permission_policy.get(key) != request.get(key) for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")):
        return _safe_stop("deny_unbound_permission", request)
    permissions = task_permission_policy.get("permissions")
    if not _valid_permission_policy(permissions) or not permissions:
        return _safe_stop("deny_unbound_permission", request)
    if any(session_binding.get(key) != request.get(key) for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")) or permission_binding.get("session_id") != session_binding.get("session_id") or any(permission_binding.get(key) != session_binding.get(key) for key in session_fields):
        return _safe_stop("deny_unbound_permission", request)
    session_id, permission_id = session_binding.get("session_id"), permission_binding.get("permission_id")
    action, resource_digest = permission_binding.get("action"), permission_binding.get("resource_digest")
    if not _safe_api_id(session_id, "ses") or not _safe_api_id(permission_id, "per") or not _safe_permission_action(action) or not _safe_digest(resource_digest) or not _loopback_origin(origin) or not callable(fetch) or not callable(send):
        return _safe_stop("deny_invalid_permission", request)
    session_identity = _session_claim_identity(session_binding, str(session_id), permissions)
    if not has_claim(state_dir, "session", session_identity):
        return _safe_stop("deny_unbound_permission", request)
    if not any(item["action"] == action and item["resource_digest"] == resource_digest for item in permissions):
        return _safe_stop("deny_unapproved_permission", request)
    try:
        pending = select_pending_permission(fetch(origin), session_id, permission_id)
    except Exception:
        pending = None
    if pending is None or pending["action"] != action or pending["resource_digest"] != resource_digest:
        return _safe_stop("deny_invalid_permission", request)
    identity = {key: str(request[key]) for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")}
    identity.update({"session_id": session_id, "permission_id": permission_id})
    if not consume_once(state_dir, "permission", identity):
        return _safe_stop("deny_consumed_permission", request)
    binding = {**identity, "action": action, "resource_digest": resource_digest}
    result = reply_loopback_once(origin, binding, consumed=set(), fetch=fetch, send=send)
    safe = {"decision": result.get("decision", "stopped_safety_signal"), "task_id": request["task_id"], "run_id": request["run_id"], "agent_id": request["agent_id"], "grant_id": request["grant_id"]}
    return safe


def _assigned_prompt(card: object, request: Mapping[str, object]) -> str | None:
    if not isinstance(card, Mapping) or set(card) not in (TASK_CARD_FIELDS, TASK_CARD_FIELDS | {"permission_policy"}) or card.get("task_id") != request.get("task_id") or card.get("owner") != request.get("agent_id") or card.get("status") != "IN_PROGRESS":
        return None
    fields = {key: card[key] for key in TASK_CARD_FIELDS if key not in {"owner", "status"}}
    return build_task_prompt(fields)


def _task_permission_policy(card: object) -> list[dict[str, str]] | None:
    if not isinstance(card, Mapping):
        return None
    policy = card.get("permission_policy", [])
    if not _valid_permission_policy(policy):
        return None
    return [dict(item) for item in policy]


def _valid_permission_policy(value: object) -> bool:
    if not isinstance(value, list) or len(value) > 64 or any(not isinstance(item, Mapping) or set(item) != {"action", "resource_digest"} or not _safe_permission_action(item.get("action")) or not _safe_digest(item.get("resource_digest")) for item in value):
        return False
    pairs = [(item["action"], item["resource_digest"]) for item in value]
    return len(set(pairs)) == len(pairs)


def _session_claim_identity(binding: Mapping[str, object], session_id: str, permissions: list[dict[str, str]]) -> dict[str, str]:
    canonical = json.dumps(permissions, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    identity = {key: str(binding[key]) for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")}
    return identity | {"session_id": session_id, "permission_policy_digest": hashlib.sha256(canonical).hexdigest()}


def _safe_stop(decision: str, request: object) -> dict[str, object]:
    result: dict[str, object] = {"decision": decision, "dry_run": decision != "completed", "control_level": "best_effort"}
    if isinstance(request, Mapping):
        for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id"):
            value = request.get(key)
            if isinstance(value, str) and len(value) <= 128:
                result[key] = value
    return result


def _session_result(decision: str, request: Mapping[str, object], session_id: str) -> dict[str, object]:
    result = _safe_stop(decision, request)
    if _safe_api_id(session_id, "ses"):
        result["worker_session_id"] = session_id
        result["worker_session_binding"] = {key: request[key] for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id")} | {"session_id": session_id}
    return result


def _abort_session(abort_session: AbortSession, session_id: str) -> bool:
    try:
        return abort_session(session_id) is True
    except Exception:
        return False


def _stop_session_result(decision: str, request: Mapping[str, object], session_id: str, abort_session: AbortSession) -> dict[str, object]:
    return _session_result(decision if _abort_session(abort_session, session_id) else "stopped_safety_signal", request, session_id)


def _safe_api_id(value: object, prefix: str) -> bool:
    if not isinstance(value, str) or not value.startswith(prefix) or len(value) > 256 or re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is None:
        return False
    lowered = value.casefold()
    return not any(word in lowered for word in ("api_key", "authorization", "bearer", "credential", "password", "secret", "token"))


def _safe_digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _safe_permission_action(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 128 and re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is not None and not any(word in value.casefold() for word in ("api_key", "authorization", "bearer", "credential", "password", "secret", "token"))


def _url_component(value: str) -> str:
    safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return "".join(chr(byte) if byte in safe else f"%{byte:02X}" for byte in value.encode("utf-8"))


def _loopback_origin(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("http://127.0.0.1:") or value.count(":") != 2:
        return False
    port = value.rsplit(":", 1)[1]
    return port.isascii() and port.isdecimal() and 1 <= int(port) <= 65535


def _launcher(value: object, request: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != LAUNCHER_FIELDS:
        return False
    if not isinstance(request, Mapping) or any(value.get(key) != request.get(key) for key in ("approval_id", "run_id")):
        return False
    return all(value.get(key) == expected for key, expected in PINNED_LAUNCHER.items()) and _wrapper_path(value.get("wrapper_path")) and _wrapper_content_digest(str(value["wrapper_path"])) == PINNED_WRAPPER_CONTENT_DIGEST and bool(_runtime_path())


def _wrapper_path(value: object) -> bool:
    if not isinstance(value, str) or not (1 <= len(value) <= 512) or not ntpath.isabs(value) or ntpath.normpath(value) != value:
        return False
    drive, _ = ntpath.splitdrive(value)
    return len(drive) == 2 and drive[0].isalpha() and drive[1] == ":" and value.casefold().endswith(".ps1") and all(part not in {"", ".", ".."} for part in value.split("\\")[1:]) and not any(char in value for char in "\x00\r\n\"'`|;&")


def _wrapper_content_digest(value: str) -> str | None:
    try:
        with open(value, "rb") as wrapper:
            content = wrapper.read(1025)
    except OSError:
        return None
    return hashlib.sha256(content).hexdigest() if len(content) <= 1024 else None


def _runtime_path() -> str | None:
    """Resolve only the reviewed command identity; never expose its path."""
    value = shutil.which("opencode")
    if value is None or not _executable_path(value):
        return None
    try:
        with open(value, "rb") as runtime:
            content = runtime.read(16385)
    except OSError:
        return None
    return value if len(content) <= 16384 and hashlib.sha256(content).hexdigest() == PINNED_RUNTIME_CONTENT_DIGEST else None


def _executable_path(value: str) -> bool:
    if not (1 <= len(value) <= 512) or not ntpath.isabs(value) or ntpath.normpath(value) != value:
        return False
    drive, _ = ntpath.splitdrive(value)
    return len(drive) == 2 and drive[0].isalpha() and drive[1] == ":" and value.casefold().endswith(".cmd") and all(part not in {"", ".", ".."} for part in value.split("\\")[1:]) and not any(char in value for char in "\x00\r\n\"'`|;&")


def _spawn(popen: Popen, wrapper_path: str, request: Mapping[str, object], state: StartAttestationState, captured: list[tuple[dict[str, object], dict[str, object]]]) -> Spawn:
    def spawn(_: str, argv: tuple[str, ...], *, cwd_ref: str, env: dict[str, str], shell: bool) -> Process:
        runtime_path = _runtime_path()
        if not _wrapper_path(wrapper_path) or _wrapper_content_digest(wrapper_path) != PINNED_WRAPPER_CONTENT_DIGEST or runtime_path is None:
            raise RuntimeError("launcher changed before spawn")
        child = popen((POWERSHELL, "-NoProfile", "-NonInteractive", "-File", wrapper_path, "-RuntimePath", runtime_path, *argv), cwd=cwd_ref, env=env, shell=shell, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not _live_child_identity(child):
            raise RuntimeError("child is not live")
        tree = _ProcessTree(child, popen, state, _binding_digest(request))
        try:
            tree.register_start()
        except Exception:
            try:
                tree.terminate_tree()
            except Exception:
                pass
            raise RuntimeError("start registration failed") from None
        assert tree.start_evidence is not None
        captured.append(tree.start_evidence)
        return tree
    return spawn


def _live_child_identity(child: object) -> bool:
    """Require a live returned child while keeping its identity private."""
    pid = getattr(child, "pid", None)
    poll = getattr(child, "poll", None)
    if type(pid) is not int or pid < 1 or not callable(poll):
        return False
    try:
        return poll() is None
    except Exception:
        return False


def _binding_digest(request: Mapping[str, object]) -> str:
    values = {key: request[key] for key in ("approval_id", "agent_id", "grant_id", "worktree_ref")}
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class _ProcessTree:
    def __init__(self, child: object, popen: Popen, state: StartAttestationState, binding_digest: str) -> None:
        self._child, self._popen = child, popen
        self._state, self._binding_digest = state, binding_digest
        self._finished = False
        self.start_evidence: tuple[dict[str, object], dict[str, object]] | None = None

    def register_start(self) -> None:
        self.start_evidence = self._state.start(self._binding_digest)

    def _finish(self) -> None:
        if not self._finished:
            self._state.finish(self._binding_digest)
            self._finished = True

    def wait(self, timeout: int) -> int:
        try:
            return self._child.wait(timeout=timeout)  # type: ignore[union-attr,no-any-return]
        finally:
            self._finish()

    def poll(self) -> int | None:
        result = self._child.poll()  # type: ignore[union-attr]
        if result is not None:
            self._finish()
        return result

    def terminate_tree(self) -> None:
        try:
            self._popen((TASKKILL, "/pid", str(self._child.pid), "/t", "/f"), env={}, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=5)  # type: ignore[union-attr]
        finally:
            self._finish()
