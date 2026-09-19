"""L1 fake-process boundary; it makes no real runtime or connector call itself."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping, Protocol

from local_control_provision import TASK_ID, validate_approval


REQUEST_FIELDS = frozenset({"task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "stop_authority"})
SAFE_KEYS = ("task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref", "runtime_id", "timeout_seconds", "stop_authority")
RECORD_FIELDS = frozenset({"task_id", "run_id", "approval_id", "agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds", "stop_authority", "scheduler_ref", "lease_ref", "review_ref", "manifest_digest", "allocation_digest", "control_level", "process_tree_stop_handling"})
RECORD_BINDING_KEYS = ("agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds", "stop_authority", "scheduler_ref", "lease_ref", "review_ref", "manifest_digest", "allocation_digest")


class Process(Protocol):
    def wait(self, timeout: int) -> int: ...
    def terminate_tree(self) -> None: ...


ProcessFactory = Callable[[], Process]


def run_local_once(request: object, approval: object, records: object, *, now: datetime, consumed_run_ids: set[str], process_factory: ProcessFactory) -> dict[str, object]:
    """Consume a verified L1 run before exactly one injected process-factory call."""
    if not _request(request):
        return {"decision": "deny_invalid_request", "dry_run": True}
    assert isinstance(request, Mapping)
    if request["run_id"] in consumed_run_ids:
        return _result("deny_consumed_approval", request)
    if not validate_approval(approval, now=now) or not _bound(request, approval, records):
        return _result("deny_unbound_approval", request)
    consumed_run_ids.add(str(request["run_id"]))
    try:
        process = process_factory()
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


def _request(value: object) -> bool:
    return isinstance(value, Mapping) and set(value) == REQUEST_FIELDS and value.get("task_id") == TASK_ID and all(_identifier(value.get(key)) for key in ("run_id", "approval_id", "agent_id", "grant_id", "runtime_id", "stop_authority")) and _ref(value.get("worktree_ref")) and _argv(value.get("argv_allowlist")) and type(value.get("timeout_seconds")) is int and 1 <= value["timeout_seconds"] <= 900


def _bound(request: Mapping[str, object], approval: object, records: object) -> bool:
    if not isinstance(approval, Mapping) or request.get("approval_id") != approval.get("approval_id") or request.get("run_id") != approval.get("run_id"):
        return False
    if not isinstance(records, list) or len(records) != 6:
        return False
    bound_keys = SAFE_KEYS + ("argv_allowlist",)
    bindings = approval.get("bindings")
    if not isinstance(bindings, list) or len([binding for binding in bindings if isinstance(binding, Mapping) and all(binding.get(key) == request.get(key) for key in bound_keys[3:])]) != 1:
        return False
    if not all(isinstance(record, Mapping) and set(record) == RECORD_FIELDS for record in records):
        return False
    expected = {binding.get("agent_id"): binding for binding in bindings if isinstance(binding, Mapping)}
    if len(expected) != 6 or any(not _record_matches(record, approval, expected.get(record.get("agent_id"))) for record in records):
        return False
    matches = [record for record in records if isinstance(record, Mapping) and all(record.get(key) == request.get(key) for key in bound_keys)]
    return len(matches) == 1 and {record.get("agent_id") for record in records} == set(expected)


def _record_matches(record: Mapping[str, object], approval: Mapping[str, object], binding: object) -> bool:
    return isinstance(binding, Mapping) and record.get("task_id") == TASK_ID and record.get("run_id") == approval.get("run_id") and record.get("approval_id") == approval.get("approval_id") and all(record.get(key) == binding.get(key) for key in RECORD_BINDING_KEYS) and record.get("control_level") == "best_effort" and record.get("process_tree_stop_handling") is True


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 128 and ".." not in value and all(char.isascii() and (char.isalnum() or char in "-_.") for char in value)


def _ref(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 256 and not value.startswith(("/", "\\", "./", "refs/")) and all(part not in {"", ".", ".."} and _identifier(part) for part in value.split("/"))


def _argv(value: object) -> bool:
    return isinstance(value, list) and 1 <= len(value) <= 16 and all(_identifier(item) for item in value)


def _result(decision: str, request: Mapping[str, object]) -> dict[str, object]:
    result = {"decision": decision, "dry_run": decision != "completed", "control_level": "best_effort"}
    result.update({key: request[key] for key in SAFE_KEYS})
    return result
