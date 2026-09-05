#!/usr/bin/env python3
"""Fail-closed, local-only bootstrap handoff for a manually started OpenCode worker.

This module validates an operator approval record and materializes one bounded,
immutable, single-use task-context envelope.  It never starts a process, reads a
credential, touches Git, or authorises a runtime launch.
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from typing import Any, Mapping


SCHEMA_VERSION = "1.0"
MAX_PAYLOAD_BYTES = 8192
SENSITIVITY_LABEL = "internal"
LAUNCH_AUTHORIZED = False

TASK_CARD_ALLOWLIST = (
    "task_id",
    "phase",
    "status",
    "owner",
    "reviewer",
    "priority",
    "dependencies",
    "allowed_scope",
    "forbidden_scope",
    "acceptance",
)

PROTOCOL_REFERENCES = [
    "docs/operations/agent-task-execution-protocol.md",
    "docs/architecture/controlled-orchestration-architecture.md",
    "docs/operations/phase14.5-supervised-launch-design.md",
]

APPROVAL_REQUIRED_FIELDS = (
    "approval_id",
    "task_id",
    "worker_id",
    "worktree_ref",
    "issued_at",
    "expires_at",
    "approver_role",
    "one_shot",
    "enabled",
)


def approval_digest(approval: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 digest excluding the digest field itself."""
    body = {k: v for k, v in approval.items() if k != "approval_digest"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _is_relative_safe(path: str) -> bool:
    """Return True only for forward-slash, dot-free, non-absolute project-relative paths."""
    if not path or not isinstance(path, str):
        return False
    if ".." in path or "\\" in path or ":" in path:
        return False
    if path.startswith("/"):
        return False
    if path.startswith("./"):
        return False
    return True


def _validate_approval(approval: object, *, now: datetime | None = None) -> str | None:
    """Return None on success, or a terminal denial category string."""
    if not isinstance(approval, Mapping):
        return "deny_missing_approval"

    for field in APPROVAL_REQUIRED_FIELDS:
        value = approval.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return "deny_invalid_approval"

    supplied_digest = approval.get("approval_digest")
    if not isinstance(supplied_digest, str) or not compare_digest(
        supplied_digest, approval_digest(approval)
    ):
        return "deny_invalid_approval"

    if approval.get("approver_role") != "ORCHESTRATOR":
        return "deny_invalid_approval"
    if approval.get("one_shot") is not True:
        return "deny_invalid_approval"
    if approval.get("enabled") is not True:
        return "deny_disabled"

    issued_at = _parse_timestamp(str(approval.get("issued_at", "")))
    expires_at = _parse_timestamp(str(approval.get("expires_at", "")))
    if issued_at is None or expires_at is None or issued_at >= expires_at:
        return "deny_invalid_approval"

    current = now or datetime.now(issued_at.tzinfo)
    if current.tzinfo is None:
        return "deny_invalid_approval"
    if not (issued_at <= current < expires_at):
        return "deny_approval_expired"

    return None


def _validate_task_projection(task_card: Mapping[str, Any], approval: Mapping[str, Any]) -> str | None:
    """Return None if the task card projection is safe and matches the approval."""
    task_id = task_card.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return "deny_invalid_task"
    if task_id != approval.get("task_id"):
        return "deny_task_mismatch"
    return None


def _validate_worktree_ref(worktree_ref: str, approval: Mapping[str, Any]) -> str | None:
    if worktree_ref != approval.get("worktree_ref"):
        return "deny_worktree_mismatch"
    if not _is_relative_safe(worktree_ref):
        return "deny_unsafe_path"
    return None


def _build_task_projection(task_card: Mapping[str, Any]) -> dict[str, Any]:
    """Return only the allowlisted, safe subset of the task card."""
    projection: dict[str, Any] = {}
    for key in TASK_CARD_ALLOWLIST:
        value = task_card.get(key)
        if value is not None:
            projection[key] = value
    return projection


def _idempotency_key(task_id: str, approval_id: str, worker_id: str) -> str:
    raw = f"{task_id}|{approval_id}|{worker_id}"
    return sha256(raw.encode("utf-8")).hexdigest()


def build_handoff(
    approval: object,
    task_card: object,
    worktree_ref: str,
    dependency_evidence_refs: list[str] | None = None,
    *,
    now: datetime | None = None,
    idempotency_store: set[str] | None = None,
) -> dict[str, Any]:
    """Validate inputs and produce one immutable, single-use handoff envelope.

    Parameters
    ----------
    approval : dict
        Operator approval record.
    task_card : dict
        Task card front matter projected to safe fields.
    worktree_ref : str
        Project-relative worktree reference.
    dependency_evidence_refs : list[str] | None
        Optional safe project-relative references to dependency evidence.
    now : datetime | None
        Fake clock for deterministic tests.
    idempotency_store : set[str] | None
        Mutable set for replay denial testing.

    Returns
    -------
    dict
        Either a ``handoff`` envelope or a terminal denial record.
    """
    if not isinstance(task_card, Mapping):
        return {"decision": "deny_invalid_task"}

    approval_denial = _validate_approval(approval, now=now)
    if approval_denial is not None:
        return {"decision": approval_denial}

    assert isinstance(approval, Mapping)  # narrowed by validation

    task_denial = _validate_task_projection(task_card, approval)
    if task_denial is not None:
        return {"decision": task_denial}

    wt_denial = _validate_worktree_ref(worktree_ref, approval)
    if wt_denial is not None:
        return {"decision": wt_denial}

    if dependency_evidence_refs is None:
        dependency_evidence_refs = []
    for ref in dependency_evidence_refs:
        if not _is_relative_safe(ref):
            return {"decision": "deny_unsafe_path"}

    idem_key = _idempotency_key(
        str(task_card["task_id"]),
        str(approval["approval_id"]),
        str(approval["worker_id"]),
    )
    if idempotency_store is not None and idem_key in idempotency_store:
        return {"decision": "deny_replay", "idempotency_key": idem_key}

    projection = _build_task_projection(task_card)
    envelope: dict[str, Any] = {
        "handoff_id": f"handoff-{idem_key[:16]}",
        "schema_version": SCHEMA_VERSION,
        "approval_id": approval["approval_id"],
        "task_id": task_card["task_id"],
        "worker_id": approval["worker_id"],
        "worktree_ref": worktree_ref,
        "task_card_projection": projection,
        "protocol_references": list(PROTOCOL_REFERENCES),
        "dependency_evidence_refs": list(dependency_evidence_refs),
        "idempotency_key": idem_key,
        "max_payload_bytes": MAX_PAYLOAD_BYTES,
        "sensitivity_label": SENSITIVITY_LABEL,
        "expires_at": approval["expires_at"],
        "one_shot": True,
        "launch_authorized": LAUNCH_AUTHORIZED,
        "decision": "handoff_prepared",
    }

    encoded = json.dumps(
        {k: v for k, v in envelope.items() if k != "content_digest"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        return {"decision": "deny_payload_too_large"}
    envelope["content_digest"] = sha256(encoded.encode("utf-8")).hexdigest()

    if idempotency_store is not None:
        idempotency_store.add(idem_key)

    return envelope
