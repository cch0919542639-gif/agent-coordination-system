"""L1 OpenCode boundary with an injected spawn; it never starts a runtime itself."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterable, Mapping, Protocol

from local_control_adapter import SAFE_KEYS, _bound, _request
from local_control_provision import PROJECT_CONTEXT_KEY, validate_approval


LOCAL_EXECUTABLES = {"opencode": "opencode.exe"}
SAFE_RESULT_KEYS = ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "runtime_id", "timeout_seconds")
FORBIDDEN_WORDS = ("api_key", "authorization", "bearer", "credential", "password", "secret", "token")


class Process(Protocol):
    def wait(self, timeout: int) -> int: ...
    def terminate_tree(self) -> None: ...


Spawn = Callable[..., Process]
HealthCheck = Callable[[Process], bool]


def run_opencode_once(request: object, approval: object, records: object, *, now: datetime, consumed_run_ids: set[str], spawn: Spawn, provider_environment: object = None, heartbeat_at: datetime | None = None, supervision_checks: Iterable[datetime] = (), health_check: HealthCheck | None = None) -> dict[str, object]:
    """Consume one exact L1 run before one injected, shell-free spawn."""
    if _unsafe(request) or _unsafe(records):
        return _result("deny_unsafe_request", request)
    if not _request(request):
        return _result("deny_invalid_request", request)
    assert isinstance(request, Mapping)
    if request["runtime_id"] not in LOCAL_EXECUTABLES:
        return _result("deny_runtime", request)
    if request["run_id"] in consumed_run_ids:
        return _result("deny_consumed_approval", request)
    if not validate_approval(approval, now=now) or not _bound(request, approval, records):
        return _result("deny_unbound_approval", request)
    environment = _child_environment(approval, request, provider_environment)
    if environment is None:
        return _result("deny_provider_exception", request)
    consumed_run_ids.add(str(request["run_id"]))
    try:
        process = spawn(
            LOCAL_EXECUTABLES[str(request["runtime_id"])],
            tuple(request["argv_allowlist"]),
            cwd_ref=str(request["worktree_ref"]),
            env=environment,
            shell=False,
        )
        supervised = supervise_approved_lease(process, request, approval, started_at=now, heartbeat_at=heartbeat_at or now, checks=supervision_checks, health_check=health_check or (lambda _: True))
        if supervised is not None:
            return _result(supervised, request)
        code = process.wait(timeout=int(request["timeout_seconds"]))
    except TimeoutError:
        try:
            process.terminate_tree()
        except Exception:
            return _result("stopped_safety_signal", request)
        return _result("stopped_timeout", request)
    except Exception:
        return _result("stopped_safety_signal", request)
    return _result("completed" if code == 0 else "stopped_nonzero_exit", request)


def supervise_approved_lease(process: Process, request: Mapping[str, object], approval: Mapping[str, object], *, started_at: datetime, heartbeat_at: datetime, checks: Iterable[datetime], health_check: HealthCheck) -> str | None:
    binding = _binding_for(request, approval)
    if binding is None or heartbeat_at < started_at:
        return "stopped_invalid_heartbeat"
    interval = int(binding["heartbeat_interval_seconds"])
    missed = int(binding["missed_heartbeat_threshold"])
    ceiling = int(binding["per_child_hard_ceiling_seconds"])
    for checked_at in checks:
        if checked_at.tzinfo is None or checked_at < started_at:
            return "stopped_invalid_supervision"
        if checked_at - started_at >= timedelta(seconds=ceiling):
            return _stop(process, "stopped_hard_ceiling")
        if checked_at - heartbeat_at >= timedelta(seconds=interval * missed):
            if not health_check(process):
                return _stop(process, "stopped_health_check")
            return _stop(process, "stopped_missed_heartbeat")
    return None


def _binding_for(request: Mapping[str, object], approval: object) -> Mapping[str, object] | None:
    if not isinstance(approval, Mapping) or not isinstance(approval.get("bindings"), list):
        return None
    matches = [item for item in approval["bindings"] if isinstance(item, Mapping) and all(item.get(key) == request.get(key) for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority"))]
    return matches[0] if len(matches) == 1 else None


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
