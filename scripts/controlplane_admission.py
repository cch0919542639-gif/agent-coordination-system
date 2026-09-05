#!/usr/bin/env python3
"""Pure, fail-closed connector-grant validation and task admission planning."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from typing import Any, Mapping


GRANT_FIELDS = (
    "grant_id", "agent_id", "project_id", "adapter_id", "adapter_version",
    "allowed_task_classes", "max_concurrent_runs", "worktree_root",
    "network_policy", "expires_at", "revoked", "enabled",
)


def grant_digest(grant: Mapping[str, Any]) -> str:
    """Return the canonical digest without the supplied digest field."""
    body = {key: value for key, value in grant.items() if key != "grant_digest"}
    return sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value.startswith("/") or any(token in value for token in ("..", "\\", ":")):
        return False
    return all(part and part != "." for part in value.split("/"))


def _safe_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and all(char.isalnum() or char in "-_." for char in value)
        and ".." not in value
    )


def _safe_branch(value: object) -> bool:
    return _safe_relative(value) and not str(value).startswith("refs/") and "@{" not in str(value)


def validate_grant(grant: object, *, now: datetime) -> str | None:
    """Return a terminal denial category, or ``None`` for a valid live grant."""
    if not isinstance(grant, Mapping):
        return "deny_invalid_grant"
    if any(not grant.get(field) and field not in {"revoked", "enabled"} for field in GRANT_FIELDS):
        return "deny_invalid_grant"
    if any(not _safe_identifier(grant.get(field)) for field in ("grant_id", "agent_id", "project_id", "adapter_id", "adapter_version")):
        return "deny_invalid_grant"
    digest = grant.get("grant_digest")
    if not isinstance(digest, str) or not compare_digest(digest, grant_digest(grant)):
        return "deny_invalid_grant"
    if type(grant.get("enabled")) is not bool or type(grant.get("revoked")) is not bool:
        return "deny_invalid_grant"
    if grant.get("enabled") is not True:
        return "deny_disabled_grant"
    if grant.get("revoked") is True:
        return "deny_revoked_grant"
    expiry = _time(grant.get("expires_at"))
    if expiry is None or now.tzinfo is None or now >= expiry:
        return "deny_expired_grant"
    if not isinstance(grant.get("allowed_task_classes"), list) or not grant["allowed_task_classes"] or any(not _safe_identifier(value) for value in grant["allowed_task_classes"]):
        return "deny_invalid_grant"
    if type(grant.get("max_concurrent_runs")) is not int or grant["max_concurrent_runs"] < 1:
        return "deny_invalid_grant"
    if grant.get("network_policy") != "deny" or not _safe_relative(grant.get("worktree_root")):
        return "deny_invalid_grant"
    if any(key in grant for key in ("credential", "token", "secret", "password")):
        return "deny_invalid_grant"
    return None


def admit(
    grant: object,
    task: object,
    *,
    done_task_ids: set[str],
    active_agent_ids: set[str],
    existing_owners: Mapping[str, str],
    now: datetime,
) -> dict[str, Any]:
    """Produce a safe admission projection or a terminal no-launch denial."""
    denial = validate_grant(grant, now=now)
    if denial:
        return {"decision": denial}
    if not isinstance(task, Mapping):
        return {"decision": "deny_invalid_task"}
    assert isinstance(grant, Mapping)
    needed = ("task_id", "project_id", "owner", "task_class", "branch", "worktree_path", "dependencies")
    if any(not task.get(field) for field in needed):
        return {"decision": "deny_invalid_task"}
    if any(not _safe_identifier(task.get(field)) for field in ("task_id", "project_id", "owner", "task_class")):
        return {"decision": "deny_invalid_task"}
    if task["project_id"] != grant["project_id"] or task["owner"] != grant["agent_id"]:
        return {"decision": "deny_identity_mismatch"}
    if task["task_class"] not in grant["allowed_task_classes"]:
        return {"decision": "deny_capability"}
    if not _safe_branch(task["branch"]) or not _safe_relative(task["worktree_path"]):
        return {"decision": "deny_unsafe_provenance"}
    root = str(grant["worktree_root"])
    if not str(task["worktree_path"]).startswith(root + "/"):
        return {"decision": "deny_worktree_provenance"}
    if not isinstance(task["dependencies"], list) or any(not _safe_identifier(dep) or dep not in done_task_ids for dep in task["dependencies"]):
        return {"decision": "deny_dependency"}
    if str(task["task_id"]) in existing_owners:
        return {"decision": "deny_duplicate_owner"}
    if len(active_agent_ids) >= int(grant["max_concurrent_runs"]):
        return {"decision": "deny_capacity"}
    raw = f"{grant['grant_id']}|{task['task_id']}|{task['owner']}"
    return {
        "decision": "admitted_no_launch",
        "grant_id": grant["grant_id"],
        "agent_id": grant["agent_id"],
        "project_id": task["project_id"],
        "task_id": task["task_id"],
        "task_class": task["task_class"],
        "worktree_path": task["worktree_path"],
        "idempotency_key": sha256(raw.encode()).hexdigest(),
    }
