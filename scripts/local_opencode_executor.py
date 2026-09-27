"""L1 OpenCode boundary with an injected spawn; it never starts a runtime itself."""

from __future__ import annotations

from datetime import datetime
from time import monotonic, sleep
from typing import Callable, Mapping, Protocol

from local_control_adapter import RECORD_FIELDS, SAFE_KEYS, _bound, _request
from local_control_provision import PROJECT_CONTEXT_KEY, validate_approval
from one_shot_consumption import consume_once


LOCAL_EXECUTABLES = {"opencode": "opencode"}
SAFE_RESULT_KEYS = ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "runtime_id", "timeout_seconds")
FORBIDDEN_WORDS = ("api_key", "authorization", "bearer", "credential", "password", "secret", "token")


class Process(Protocol):
    def poll(self) -> int | None: ...
    def terminate_tree(self) -> None: ...


Spawn = Callable[..., Process]
HealthCheck = Callable[[Process], bool]
Heartbeat = Callable[[], bool]
Monotonic = Callable[[], float]
Sleep = Callable[[float], None]


def run_opencode_once(request: object, approval: object, records: object, *, now: datetime, state_dir: str, spawn: Spawn, provider_environment: object = None, heartbeat: Heartbeat | None = None, health_check: HealthCheck | None = None, monotonic_clock: Monotonic = monotonic, sleep_fn: Sleep = sleep, poll_interval: float = 0.25) -> dict[str, object]:
    """Admit one pilot once, then fence each exact injected child launch."""
    if _unsafe(request) or _unsafe(records):
        return _result("deny_unsafe_request", request)
    if not _request(request):
        return _result("deny_invalid_request", request)
    assert isinstance(request, Mapping)
    if request["runtime_id"] not in LOCAL_EXECUTABLES:
        return _result("deny_runtime", request)
    if not validate_approval(approval, now=now) or not _bound(request, approval, _base_records(records)):
        return _result("deny_unbound_approval", request)
    environment = _child_environment(approval, request, provider_environment)
    if environment is None:
        return _result("deny_provider_exception", request)
    if heartbeat is None or type(poll_interval) not in (int, float) or not 0 < poll_interval <= 1:
        return _result("deny_supervision_unavailable", request)
    binding_identity = {key: str(request[key]) for key in ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref")}
    if not consume_once(state_dir, "binding", binding_identity):
        return _result("deny_consumed_binding", request)
    if not consume_once(state_dir, "approval", binding_identity):
        return _result("deny_consumed_approval", request)
    try:
        process = spawn(
            LOCAL_EXECUTABLES[str(request["runtime_id"])],
            tuple(request["argv_allowlist"]),
            cwd_ref=str(request["worktree_ref"]),
            env=environment,
            shell=False,
        )
        supervised = supervise_approved_lease(process, request, approval, started_at=monotonic_clock(), heartbeat=heartbeat, health_check=health_check or (lambda _: True), monotonic_clock=monotonic_clock, sleep_fn=sleep_fn, poll_interval=float(poll_interval))
        if supervised is not None:
            return _result(supervised, request)
        code = process.poll()
        if code is None:
            return _result("stopped_supervision_lost", request)
    except TimeoutError:
        try:
            process.terminate_tree()
        except Exception:
            return _result("stopped_safety_signal", request)
        return _result("stopped_timeout", request)
    except Exception:
        return _result("stopped_safety_signal", request)
    return _result("completed" if code == 0 else "stopped_nonzero_exit", request)


def supervise_approved_lease(process: Process, request: Mapping[str, object], approval: Mapping[str, object], *, started_at: float, heartbeat: Heartbeat, health_check: HealthCheck, monotonic_clock: Monotonic = monotonic, sleep_fn: Sleep = sleep, poll_interval: float = 0.25) -> str | None:
    binding = _binding_for(request, approval)
    if binding is None or not callable(heartbeat) or not 0 < poll_interval <= 1:
        return "stopped_invalid_heartbeat"
    interval = int(binding["heartbeat_interval_seconds"])
    missed = int(binding["missed_heartbeat_threshold"])
    ceiling = int(binding["per_child_hard_ceiling_seconds"])
    timeout = int(request["timeout_seconds"])
    stop_after = min(timeout, ceiling)
    stop_reason = "stopped_timeout" if timeout < ceiling else "stopped_hard_ceiling"
    last_heartbeat = started_at
    next_heartbeat = started_at + interval
    while True:
        current = monotonic_clock()
        if current < started_at:
            return _stop(process, "stopped_invalid_supervision")
        if current - started_at >= stop_after:
            return _stop(process, stop_reason)
        if process.poll() is not None:
            return None
        if current >= next_heartbeat:
            try:
                if heartbeat():
                    last_heartbeat = current
            except Exception:
                pass
            next_heartbeat = current + interval
        if current - last_heartbeat >= interval * missed:
            try:
                healthy = health_check(process)
            except Exception:
                healthy = False
            return _stop(process, "stopped_missed_heartbeat" if healthy else "stopped_health_check")
        sleep_fn(min(poll_interval, max(0.0, min(next_heartbeat, started_at + stop_after) - current)))


def _binding_for(request: Mapping[str, object], approval: object) -> Mapping[str, object] | None:
    if not isinstance(approval, Mapping) or not isinstance(approval.get("bindings"), list):
        return None
    matches = [item for item in approval["bindings"] if isinstance(item, Mapping) and all(item.get(key) == request.get(key) for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority"))]
    return matches[0] if len(matches) == 1 else None


def _base_records(records: object) -> object:
    """Keep the adapter's prior exact projection while records carry leases."""
    if not isinstance(records, list):
        return records
    return [{key: item[key] for key in RECORD_FIELDS} if isinstance(item, Mapping) and set(RECORD_FIELDS) <= set(item) else item for item in records]


def _stop(process: Process, decision: str) -> str:
    try:
        process.terminate_tree()
    except Exception:
        return "stopped_safety_signal"
    return decision


def _child_environment(approval: object, request: Mapping[str, object], supplied: object) -> dict[str, str] | None:
    if not isinstance(approval, Mapping):
        return None
    exception = approval.get("network_provider_exception")
    if exception is None:
        return {} if supplied is None else None
    if not isinstance(exception, Mapping) or exception.get("enabled") is not True:
        return {} if supplied is None else None
    if not isinstance(supplied, Mapping) or supplied != {PROJECT_CONTEXT_KEY: request["worktree_ref"]}:
        return None
    return {PROJECT_CONTEXT_KEY: str(request["worktree_ref"])}


def _unsafe(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_unsafe(key) or _unsafe(item) for key, item in value.items())
    if isinstance(value, list) or isinstance(value, tuple):
        return any(_unsafe(item) for item in value)
    return isinstance(value, str) and any(word in value.casefold() for word in FORBIDDEN_WORDS)


def _result(decision: str, request: object) -> dict[str, object]:
    result: dict[str, object] = {"decision": decision, "dry_run": decision != "completed", "control_level": "best_effort"}
    if isinstance(request, Mapping) and _request(request) and not _unsafe(request):
        result.update({key: request[key] for key in SAFE_RESULT_KEYS})
    return result
