#!/usr/bin/env python3
"""Fixture-only Phase D allocation and immutable context projections.

The module plans where an approved worker *would* operate.  It never creates
a worktree, reads a task card from disk, invokes Git, launches a runtime, or
persists context.  Callers supply plain mappings and receive safe, relative
references suitable for a later scheduler envelope.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "1.0"
SENSITIVITY_LABEL = "internal"
MAX_CONTEXT_BYTES = 8192
TASK_CARD_ALLOWLIST = (
    "task_id", "phase", "status", "owner", "reviewer", "priority",
    "dependencies", "allowed_scope", "forbidden_scope", "acceptance",
)
IDENTITY_FIELDS = frozenset({"task_id", "owner", "branch", "worktree_path"})
ALLOCATION_FIELDS = IDENTITY_FIELDS | {"allocation_id"}
FORBIDDEN_KEYS = frozenset({
    "credential", "credentials", "secret", "password", "token", "prompt",
    "transcript", "source", "source_body", "body", "output", "raw_output",
    "log", "logs", "argv", "command", "env", "environment",
})


def _identifier(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value) and value == value.strip()
        and len(value) <= 128 and ".." not in value
        and all(char.isalnum() or char in "-_." for char in value)
    )


def _relative_ref(value: object) -> bool:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 256:
        return False
    if value.startswith(("/", "\\", "./", "refs/")) or ".." in value or "\\" in value:
        return False
    if ":" in value or "://" in value or "@{" in value:
        return False
    return all(part and part != "." and not part.endswith((".", " ")) for part in value.split("/"))


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _unsafe_content(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN_KEYS or _unsafe_content(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_unsafe_content(item) for item in value)
    elif isinstance(value, str):
        stripped = value.strip()
        return stripped.startswith(("/", "\\")) or (len(stripped) > 1 and stripped[1] == ":") or "://" in stripped
    return False


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def plan_worktree_allocations(
    identities: Sequence[Mapping[str, object]], *, branch_prefix: str = "agent/",
    worktree_prefix: str = "worktrees/",
) -> dict[str, Any]:
    """Return a deterministic, collision-free plan without provisioning it.

    Each identity is intentionally an exact four-field mapping.  The approved
    prefixes and owner-derived subdirectories make a task card unable to point
    at another worker's branch or worktree.  Six identities are a normal input
    for this phase; the function also safely supports smaller fixture sets.
    """
    if not _relative_ref(branch_prefix.rstrip("/")) or not _relative_ref(worktree_prefix.rstrip("/")):
        return {"decision": "deny_unsafe_policy"}
    if not isinstance(identities, Sequence) or isinstance(identities, (str, bytes)) or not identities:
        return {"decision": "deny_invalid_identity"}
    planned: list[dict[str, str]] = []
    task_ids: set[str] = set()
    branches: set[str] = set()
    worktrees: set[str] = set()
    for identity in identities:
        if not isinstance(identity, Mapping) or set(identity) != IDENTITY_FIELDS or _unsafe_content(identity):
            return {"decision": "deny_invalid_identity"}
        task_id, owner = identity["task_id"], identity["owner"]
        branch, worktree = identity["branch"], identity["worktree_path"]
        if not _identifier(task_id) or not _identifier(owner) or not _relative_ref(branch) or not _relative_ref(worktree):
            return {"decision": "deny_unsafe_provenance"}
        owner_ref = str(owner).lower()
        if not str(branch).startswith(f"{branch_prefix}{owner_ref}/") or not str(worktree).startswith(f"{worktree_prefix}{owner_ref}/"):
            return {"decision": "deny_provenance_policy"}
        if task_id in task_ids or branch in branches or worktree in worktrees:
            return {"decision": "deny_allocation_collision"}
        task_ids.add(str(task_id)); branches.add(str(branch)); worktrees.add(str(worktree))
        planned.append({"task_id": str(task_id), "owner": str(owner), "branch": str(branch), "worktree_path": str(worktree)})
    allocations = []
    for item in sorted(planned, key=lambda value: value["task_id"]):
        allocation_id = hashlib.sha256(_canonical_bytes(item)).hexdigest()
        allocations.append({**item, "allocation_id": allocation_id})
    return {"decision": "allocation_ready", "schema_version": SCHEMA_VERSION, "allocations": allocations}


def build_bounded_context_snapshot(
    task_card: Mapping[str, object], dependency_evidence_refs: Sequence[str], allocation: Mapping[str, object], *,
    snapshot_ref: str, expires_at: str, now: datetime, max_bytes: int = MAX_CONTEXT_BYTES,
) -> dict[str, Any]:
    """Build one hash-bound immutable projection for a single planned attempt."""
    if not isinstance(task_card, Mapping) or not isinstance(allocation, Mapping) or _unsafe_content(task_card):
        return {"decision": "deny_unsafe_content"}
    if set(allocation) != ALLOCATION_FIELDS or _unsafe_content(allocation):
        return {"decision": "deny_invalid_allocation"}
    if not all(_identifier(allocation.get(key)) for key in ("task_id", "owner")) or not _hex64(allocation.get("allocation_id")):
        return {"decision": "deny_invalid_allocation"}
    if not _relative_ref(allocation.get("branch")) or not _relative_ref(allocation.get("worktree_path")):
        return {"decision": "deny_unsafe_provenance"}
    owner_ref = str(allocation["owner"]).lower()
    if not str(allocation["branch"]).startswith(f"agent/{owner_ref}/") or not str(allocation["worktree_path"]).startswith(f"worktrees/{owner_ref}/"):
        return {"decision": "deny_provenance_policy"}
    identity = {key: str(allocation[key]) for key in ("task_id", "owner", "branch", "worktree_path")}
    if allocation["allocation_id"] != hashlib.sha256(_canonical_bytes(identity)).hexdigest():
        return {"decision": "deny_invalid_allocation"}
    if not _relative_ref(snapshot_ref) or not isinstance(dependency_evidence_refs, Sequence) or isinstance(dependency_evidence_refs, (str, bytes)):
        return {"decision": "deny_unsafe_content"}
    if any(not _relative_ref(ref) for ref in dependency_evidence_refs):
        return {"decision": "deny_unsafe_content"}
    expiry = _parse_time(expires_at)
    if expiry is None or now.tzinfo is None or expiry <= now:
        return {"decision": "deny_expired"}
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1 or max_bytes > MAX_CONTEXT_BYTES:
        return {"decision": "deny_invalid_limit"}
    projection = {key: task_card[key] for key in TASK_CARD_ALLOWLIST if key in task_card}
    if projection.get("task_id") != allocation["task_id"]:
        return {"decision": "deny_provenance_mismatch"}
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "sensitivity_label": SENSITIVITY_LABEL,
        "max_bytes": max_bytes,
        "task_projection": projection,
        "dependency_evidence_refs": list(dependency_evidence_refs),
        "allocation": {
            "task_id": allocation["task_id"], "owner": allocation["owner"],
            "branch_ref": allocation["branch"], "worktree_ref": allocation["worktree_path"],
            "allocation_id": allocation["allocation_id"],
        },
        "expires_at": expires_at,
    }
    encoded = _canonical_bytes(body)
    if len(encoded) > max_bytes:
        return {"decision": "deny_context_too_large"}
    return {
        "decision": "snapshot_ready", "snapshot_ref": snapshot_ref,
        "snapshot_hash": hashlib.sha256(encoded).hexdigest(), "byte_size": len(encoded),
        "schema_version": SCHEMA_VERSION, "sensitivity_label": SENSITIVITY_LABEL,
        "expires_at": expires_at, "snapshot": body,
    }
