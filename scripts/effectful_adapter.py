#!/usr/bin/env python3
"""Fail-closed, injected one-shot process boundary; never a runtime launcher."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping, Protocol

from controlplane_admission import validate_grant


REQUEST_FIELDS = frozenset({"task_id", "run_id", "approval_id", "grant_id", "agent_id", "project_id", "worktree_ref", "timeout_seconds"})
APPROVAL_FIELDS = frozenset({"approval_id", "action", "task_id", "run_id", "grant_id", "agent_id", "worktree_ref", "issued_at", "expires_at", "enabled"})
ATTESTATION_FIELDS = frozenset({"attestation_id", "task_id", "run_id", "grant_id", "agent_id", "worktree_ref", "restricted_writes", "process_identity", "network_egress", "issued_at", "expires_at", "enabled"})
SAFE_RESULT_FIELDS = ("task_id", "run_id", "approval_id", "grant_id", "agent_id", "timeout_seconds")


class Process(Protocol):
    def wait(self, timeout: int) -> int: ...
    def terminate(self) -> None: ...


ProcessFactory = Callable[[], Process]


def run_once(request: object, approval: object, grant: object, attestation: object, *, now: datetime, consumed_run_ids: set[str], process_factory: ProcessFactory) -> dict[str, object]:
    """Consume one bound run before invoking the injected factory at most once."""
    safe_request = request if _request(request) else None
    denial = _validate(safe_request, approval, grant, attestation, now, consumed_run_ids)
    if denial:
        return _result(denial, safe_request)
    assert isinstance(request, Mapping)
    consumed_run_ids.add(str(request["run_id"]))
    try:
        process = process_factory()
        code = process.wait(timeout=int(request["timeout_seconds"]))
    except TimeoutError:
        try:
            process.terminate()
        except Exception:
            return _result("stopped_safety_signal", request)
        return _result("stopped_timeout", request)
    except Exception:
        return _result("stopped_safety_signal", request)
    return _result("completed" if code == 0 else "stopped_nonzero_exit", request)


def _validate(request: object, approval: object, grant: object, attestation: object, now: datetime, consumed: set[str]) -> str | None:
    if not isinstance(request, Mapping):
        return "deny_invalid_request"
    if request["run_id"] in consumed:
        return "deny_duplicate_run"
    if validate_grant(grant, now=now) is not None or not isinstance(grant, Mapping):
        return "deny_invalid_grant"
    if any(request[key] != grant.get(key) for key in ("grant_id", "agent_id", "project_id")) or not str(request["worktree_ref"]).startswith(str(grant["worktree_root"]) + "/"):
        return "deny_grant_binding"
    if not _approval(approval, request, now):
        return "deny_approval"
    if not _attestation(attestation, request, now):
        return "deny_enforcement_attestation"
    return None


def _request(value: object) -> bool:
    return isinstance(value, Mapping) and set(value) == REQUEST_FIELDS and all(_identifier(value.get(key)) for key in REQUEST_FIELDS - {"timeout_seconds", "worktree_ref"}) and type(value.get("timeout_seconds")) is int and 1 <= value["timeout_seconds"] <= 900 and _relative(value["worktree_ref"])


def _approval(value: object, request: Mapping[str, Any], now: datetime) -> bool:
    return isinstance(value, Mapping) and set(value) == APPROVAL_FIELDS and value.get("enabled") is True and value.get("action") == "external_runtime_launch" and all(value.get(key) == request.get(key) for key in ("approval_id", "task_id", "run_id", "grant_id", "agent_id", "worktree_ref")) and _current(value, now)


def _attestation(value: object, request: Mapping[str, Any], now: datetime) -> bool:
    return isinstance(value, Mapping) and set(value) == ATTESTATION_FIELDS and value.get("enabled") is True and all(value.get(key) == request.get(key) for key in ("task_id", "run_id", "grant_id", "agent_id", "worktree_ref")) and value.get("restricted_writes") is True and value.get("process_identity") is True and value.get("network_egress") == "deny" and _identifier(value.get("attestation_id")) and _current(value, now)


def _current(value: Mapping[str, Any], now: datetime) -> bool:
    try:
        issued = datetime.fromisoformat(str(value["issued_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(value["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False
    return now.tzinfo is not None and issued.tzinfo is not None and expires.tzinfo is not None and issued <= now < expires


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 128 and all(char.isalnum() or char in "-_." for char in value) and ".." not in value


def _relative(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and not value.startswith(("/", "\\")) and ":" not in value and "\\" not in value and all(part not in {"", ".", ".."} for part in value.split("/"))


def _result(decision: str, request: object) -> dict[str, object]:
    result: dict[str, object] = {"decision": decision, "dry_run": decision != "completed"}
    if isinstance(request, Mapping):
        for key in SAFE_RESULT_FIELDS:
            if isinstance(request.get(key), (str, int)) and not isinstance(request.get(key), bool):
                result[key] = request[key]
    return result
