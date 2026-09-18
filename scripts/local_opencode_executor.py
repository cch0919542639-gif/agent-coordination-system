"""L1 OpenCode boundary with an injected spawn; it never starts a runtime itself."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping, Protocol

from local_control_adapter import SAFE_KEYS, _bound, _request
from local_control_provision import validate_approval


LOCAL_EXECUTABLES = {"opencode": "opencode.exe"}
SAFE_RESULT_KEYS = ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "runtime_id", "timeout_seconds")
FORBIDDEN_WORDS = ("api_key", "authorization", "bearer", "credential", "password", "secret", "token")


class Process(Protocol):
    def wait(self, timeout: int) -> int: ...
    def terminate_tree(self) -> None: ...


Spawn = Callable[..., Process]


def run_opencode_once(request: object, approval: object, records: object, *, now: datetime, consumed_run_ids: set[str], spawn: Spawn, provider_environment: object = None) -> dict[str, object]:
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
    environment = _child_environment(approval, provider_environment)
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


def _child_environment(approval: object, supplied: object) -> dict[str, str] | None:
    if not isinstance(approval, Mapping):
        return None
    exception = approval.get("network_provider_exception")
    if exception is None:
        return {} if supplied is None else None
    if not isinstance(exception, Mapping) or exception.get("enabled") is not True:
        return {} if supplied is None else None
    keys = exception.get("environment_keys")
    if not isinstance(keys, list) or not isinstance(supplied, Mapping) or set(supplied) != set(keys):
        return None
    if not all(isinstance(key, str) and isinstance(value, str) and 1 <= len(value) <= 1024 and not _unsafe(value) and "\x00" not in value and "\n" not in value and "\r" not in value for key, value in supplied.items()):
        return None
    return dict(supplied)


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
