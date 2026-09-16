#!/usr/bin/env python3
"""Pure Phase G operator projections and explicit approval checks.

This module validates caller-provided records only.  It does not read or
write files, invoke commands, contact a network, or activate an action.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence


FORBIDDEN_KEYS = frozenset({
    "body", "command", "credential", "credentials", "env", "log", "logs",
    "output", "password", "prompt", "raw_output", "secret", "source",
    "source_body", "token", "transcript",
})
CRITICAL_ACTIONS = frozenset({
    "credential_access", "destructive_cleanup", "destructive_git",
    "external_runtime_launch", "merge", "network_transport", "push",
})
SCHEMAS = {
    "plan": frozenset({"task_id", "status", "dependency_task_ids"}),
    "admit": frozenset({"task_id", "grant_id", "decision", "risk_tier"}),
    "dispatch": frozenset({"task_id", "owner", "worktree_ref", "decision", "lease_epoch"}),
    "run-status": frozenset({"task_id", "run_id", "state", "lease_epoch", "decision"}),
    "review-bundle": frozenset({"task_id", "reviewer", "bundle_hash", "decision"}),
    "approval-queue": frozenset({"task_id", "run_id", "incident_category", "lease_epoch", "decision"}),
}


def _identifier(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 128
        and all(char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for char in value)
    )


def _relative_ref(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 256:
        return False
    if value.startswith(("/", "\\", "./", "refs/")) or ".." in value or "\\" in value or ":" in value:
        return False
    return all(part and not part.endswith(".") and all(char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ." for char in part) for part in value.split("/")) and " " not in value


def _unsafe(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(not isinstance(key, str) or key.lower() in FORBIDDEN_KEYS or _unsafe(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_unsafe(item) for item in value)
    return isinstance(value, str) and (value.startswith(("/", "\\")) or (len(value) > 1 and value[1] == ":") or "://" in value)


def _epoch(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 2**31 - 1


def _safe_record(operation: object, record: object) -> dict[str, Any] | None:
    if operation not in SCHEMAS or not isinstance(record, Mapping) or set(record) != SCHEMAS[operation] or _unsafe(record):
        return None
    value = dict(record)
    if not _identifier(value["task_id"]) or (operation != "plan" and not _identifier(value["decision"])):
        return None
    if operation == "plan":
        if not _identifier(value["status"]) or not isinstance(value["dependency_task_ids"], Sequence) or isinstance(value["dependency_task_ids"], (str, bytes)) or not all(_identifier(item) for item in value["dependency_task_ids"]):
            return None
        value["dependency_task_ids"] = sorted(value["dependency_task_ids"])
    elif operation == "admit":
        if not all(_identifier(value[key]) for key in ("grant_id", "risk_tier")):
            return None
    elif operation == "dispatch":
        if not _identifier(value["owner"]) or not _relative_ref(value["worktree_ref"]) or not _epoch(value["lease_epoch"]):
            return None
    elif operation == "run-status":
        if not _identifier(value["run_id"]) or not _identifier(value["state"]) or not _epoch(value["lease_epoch"]):
            return None
    elif operation == "review-bundle":
        if not _identifier(value["reviewer"]) or not _identifier(value["bundle_hash"]):
            return None
    elif operation == "approval-queue":
        if not _identifier(value["run_id"]) or not _identifier(value["incident_category"]) or not _epoch(value["lease_epoch"]):
            return None
    return value


def project_operation(operation: object, record: object) -> dict[str, Any]:
    """Return one stable, safe, JSON-ready operator record or deny it."""
    safe = _safe_record(operation, record)
    if safe is None:
        return {"decision": "deny_unsafe_operator_record"}
    return {"decision": "operator_projection_ready", "operation": operation, "record": safe}


def critical_action_decision(action: object, task_id: object, approval: object, now: object) -> dict[str, Any]:
    """Validate explicit approval only; this function never performs an action."""
    if action not in CRITICAL_ACTIONS or not _identifier(task_id):
        return {"decision": "deny_invalid_critical_action"}
    if approval is None:
        return {"decision": "deny_missing_approval", "action": action, "task_id": task_id}
    fields = {"approval_id", "action", "task_id", "issued_at", "expires_at", "enabled"}
    if not isinstance(approval, Mapping) or set(approval) != fields or _unsafe(approval):
        return {"decision": "deny_invalid_approval", "action": action, "task_id": task_id}
    if approval["enabled"] is not True or approval["action"] != action or approval["task_id"] != task_id or not _identifier(approval["approval_id"]):
        return {"decision": "deny_invalid_approval", "action": action, "task_id": task_id}
    try:
        issued = datetime.fromisoformat(approval["issued_at"])
        expires = datetime.fromisoformat(approval["expires_at"])
        current = datetime.fromisoformat(now) if isinstance(now, str) else None
    except (TypeError, ValueError):
        return {"decision": "deny_invalid_approval", "action": action, "task_id": task_id}
    if current is None or any(value.tzinfo is None for value in (issued, expires, current)) or issued > current or expires <= current:
        return {"decision": "deny_expired_approval", "action": action, "task_id": task_id}
    return {"decision": "operator_approval_recorded", "action": action, "task_id": task_id, "approval_id": approval["approval_id"]}
