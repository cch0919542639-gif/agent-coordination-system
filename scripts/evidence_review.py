#!/usr/bin/env python3
"""Pure Phase F review evidence projections and dependency gates.

Callers supply already-read task and evidence metadata.  This module neither
reads repository files nor accepts work: it produces safe review-queue records
and a deterministic DONE-only dependency decision.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


FORBIDDEN_KEYS = frozenset({
    "credential", "credentials", "secret", "password", "token", "prompt",
    "transcript", "source", "source_body", "body", "output", "raw_output",
    "log", "logs", "argv", "command", "env", "environment",
})
TASK_FIELDS = frozenset({"task_id", "status", "owner", "reviewer"})
EVIDENCE_FIELDS = frozenset({
    "task_card_ref", "branch_ref", "changed_files", "validation_refs",
    "delivery_ref", "review_ref", "incident_refs",
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


def _unsafe(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(not isinstance(key, str) or key.lower() in FORBIDDEN_KEYS or _unsafe(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_unsafe(item) for item in value)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped.startswith(("/", "\\")) or (len(stripped) > 1 and stripped[1] == ":") or "://" in stripped
    return False


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_review_bundle(task: Mapping[str, object], evidence: Mapping[str, object]) -> dict[str, Any]:
    """Build a task-keyed, safe, read-only index for a human reviewer."""
    if not isinstance(task, Mapping) or set(task) != TASK_FIELDS or _unsafe(task):
        return {"decision": "deny_invalid_task"}
    if not all(_identifier(task[key]) for key in ("task_id", "owner", "reviewer")) or task["status"] != "REVIEW":
        return {"decision": "deny_invalid_task"}
    if not isinstance(evidence, Mapping) or set(evidence) != EVIDENCE_FIELDS or _unsafe(evidence):
        return {"decision": "deny_unsafe_evidence"}
    refs = ("task_card_ref", "branch_ref", "delivery_ref", "review_ref")
    sequences = ("changed_files", "validation_refs", "incident_refs")
    if any(not _relative_ref(evidence[key]) for key in refs):
        return {"decision": "deny_unsafe_evidence"}
    if any(not isinstance(evidence[key], Sequence) or isinstance(evidence[key], (str, bytes)) for key in sequences):
        return {"decision": "deny_unsafe_evidence"}
    if any(not _relative_ref(item) for key in sequences for item in evidence[key]):
        return {"decision": "deny_unsafe_evidence"}
    bundle = {
        "task_id": task["task_id"], "task_card_ref": evidence["task_card_ref"],
        "branch_ref": evidence["branch_ref"], "changed_files": sorted(evidence["changed_files"]),
        "validation_refs": sorted(evidence["validation_refs"]), "delivery_ref": evidence["delivery_ref"],
        "review_ref": evidence["review_ref"], "incident_refs": sorted(evidence["incident_refs"]),
    }
    return {"decision": "review_bundle_ready", "bundle_hash": _canonical_digest(bundle), "bundle": bundle}


def queue_submission(task: Mapping[str, object], evidence: Mapping[str, object]) -> dict[str, Any]:
    """Queue safe evidence for the named reviewer; never accepts the work."""
    result = build_review_bundle(task, evidence)
    if result["decision"] != "review_bundle_ready":
        return result
    return {
        "decision": "review_queued", "task_id": task["task_id"], "reviewer": task["reviewer"],
        "bundle_hash": result["bundle_hash"], "bundle": result["bundle"],
    }


def dependency_unlock(task_id: object, cards: Mapping[str, Mapping[str, object]]) -> dict[str, Any]:
    """Allow a task only if its complete hard-dependency graph is verified DONE."""
    if not _identifier(task_id) or not isinstance(cards, Mapping) or _unsafe(cards):
        return {"decision": "deny_invalid_graph"}
    visiting: set[str] = set()
    visited: set[str] = set()

    def verify(current: str) -> str | None:
        if current in visiting:
            return "deny_cyclic_dependency"
        card = cards.get(current)
        if not isinstance(card, Mapping):
            return "deny_missing_dependency"
        if set(card) != {"status", "dependencies", "revision_conflicted"}:
            return "deny_invalid_graph"
        if card["revision_conflicted"] is not False:
            return "deny_revision_conflict"
        if not isinstance(card["dependencies"], Sequence) or isinstance(card["dependencies"], (str, bytes)):
            return "deny_invalid_graph"
        if any(not _identifier(dep) for dep in card["dependencies"]):
            return "deny_invalid_graph"
        if current in visited:
            return None
        visiting.add(current)
        for dependency in card["dependencies"]:
            outcome = verify(str(dependency))
            if outcome:
                return outcome
            dependency_card = cards[str(dependency)]
            if dependency_card["revision_conflicted"] is not False:
                return "deny_revision_conflict"
            if dependency_card["status"] != "DONE":
                return "deny_dependency_not_done"
        visiting.remove(current)
        visited.add(current)
        return None

    outcome = verify(str(task_id))
    if outcome:
        return {"decision": outcome, "task_id": task_id}
    if cards[str(task_id)]["status"] != "READY":
        return {"decision": "deny_task_not_ready", "task_id": task_id}
    return {"decision": "dependency_unlocked", "task_id": task_id, "dependency_task_ids": sorted(visited - {str(task_id)})}
