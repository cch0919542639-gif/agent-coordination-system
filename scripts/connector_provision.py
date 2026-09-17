#!/usr/bin/env python3
"""Pure, fail-closed six-record connector provisioning; never starts one."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from controlplane_admission import validate_grant


TASK_ID = "phase14.5-six-agent-pilot-08"
APPROVAL_FIELDS = frozenset({"approval_id", "action", "task_id", "run_id", "one_shot", "enabled", "issued_at", "expires_at", "run_window_start", "run_window_end", "timeout_seconds", "stop_authority", "grant_ids", "agent_ids", "worktree_root", "worktree_refs", "network_policy", "adapter_id", "adapter_version", "enforcement_evidence_refs", "manifest_digests", "allocation_digests", "prohibited_actions"})
ADAPTER_FIELDS = frozenset({"adapter_id", "adapter_version", "task_id", "review_decision", "review_ref", "implementation_ref", "enforcement_capability", "reviewed_commit", "expires_at"})
ATTESTATION_FIELDS = frozenset({"attestation_id", "task_id", "run_id", "grant_id", "agent_id", "worktree_ref", "restricted_writes", "process_identity", "network_egress", "issued_at", "expires_at", "enabled"})
EVIDENCE_FIELDS = frozenset({"enforcement_evidence_ref", "attestation"})


def provision_connectors(approval: object, grants: object, evidence: object, adapter: object, *, now: datetime) -> dict[str, object]:
    """Return six safe in-memory records, or one terminal no-runtime denial."""
    if not _approval(approval, now):
        return {"decision": "deny_invalid_approval"}
    assert isinstance(approval, Mapping)
    if not _adapter(adapter, approval, now):
        return {"decision": "deny_effectful_adapter_evidence"}
    if not isinstance(grants, Sequence) or isinstance(grants, (str, bytes)) or len(grants) != 6:
        return {"decision": "deny_connector_bindings"}
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)) or len(evidence) != 6:
        return _enforcement_denial(approval)
    grant_by_id: dict[str, Mapping[str, Any]] = {}
    for grant in grants:
        if validate_grant(grant, now=now) is not None or not isinstance(grant, Mapping):
            return {"decision": "deny_connector_bindings"}
        grant_id = grant.get("grant_id")
        if not isinstance(grant_id, str) or grant_id in grant_by_id:
            return {"decision": "deny_connector_bindings"}
        grant_by_id[grant_id] = grant
    evidence_by_ref: dict[str, Mapping[str, Any]] = {}
    for item in evidence:
        if not isinstance(item, Mapping) or set(item) != EVIDENCE_FIELDS or not _ref(item.get("enforcement_evidence_ref")):
            return _enforcement_denial(approval)
        ref, attestation = item["enforcement_evidence_ref"], item["attestation"]
        if ref in evidence_by_ref or not isinstance(attestation, Mapping):
            return _enforcement_denial(approval)
        evidence_by_ref[str(ref)] = attestation
    expected = zip(approval["agent_ids"], approval["grant_ids"], approval["worktree_refs"], approval["enforcement_evidence_refs"], approval["manifest_digests"], approval["allocation_digests"])
    records: list[dict[str, object]] = []
    for agent_id, grant_id, worktree_ref, evidence_ref, manifest_digest, allocation_digest in expected:
        grant = grant_by_id.get(str(grant_id))
        attestation = evidence_by_ref.get(str(evidence_ref))
        if grant is None or not _grant_binding(grant, approval, agent_id, worktree_ref):
            return {"decision": "deny_connector_bindings"}
        if attestation is None or not _attestation(attestation, approval, grant_id, agent_id, worktree_ref, now):
            return _enforcement_denial(approval)
        records.append({"task_id": TASK_ID, "run_id": approval["run_id"], "approval_id": approval["approval_id"], "agent_id": agent_id, "grant_id": grant_id, "worktree_ref": worktree_ref, "network_policy": "deny", "adapter_id": approval["adapter_id"], "adapter_version": approval["adapter_version"], "enforcement_evidence_ref": evidence_ref, "attestation_id": attestation["attestation_id"], "manifest_digest": manifest_digest, "allocation_digest": allocation_digest, "admitted": True, "enforcement_verified": True})
    if len(grant_by_id) != len(evidence_by_ref) or set(grant_by_id) != set(approval["grant_ids"]) or set(evidence_by_ref) != set(approval["enforcement_evidence_refs"]):
        return {"decision": "deny_connector_bindings"}
    return {"decision": "provisioned_no_runtime", "records": records}


def _approval(value: object, now: datetime) -> bool:
    if not isinstance(value, Mapping) or set(value) != APPROVAL_FIELDS or value.get("action") != "external_runtime_launch" or value.get("task_id") != TASK_ID or value.get("one_shot") is not True or value.get("enabled") is not True or value.get("network_policy") != "deny" or value.get("prohibited_actions") != ["cleanup", "credential_access", "merge", "push"]:
        return False
    times = [_time(value.get(key)) for key in ("issued_at", "expires_at", "run_window_start", "run_window_end")]
    if any(item is None for item in times) or now.tzinfo is None:
        return False
    issued, expires, start, end = times
    if not (issued <= start <= now < end <= expires):
        return False
    six = ("grant_ids", "agent_ids", "worktree_refs", "enforcement_evidence_refs", "manifest_digests", "allocation_digests")
    if any(not isinstance(value.get(key), list) or len(value[key]) != 6 or len(set(value[key])) != 6 for key in six):
        return False
    return all(_identifier(value.get(key)) for key in ("approval_id", "run_id", "stop_authority", "adapter_id", "adapter_version")) and all(_identifier(item) for key in ("agent_ids", "grant_ids") for item in value[key]) and _ref(value.get("worktree_root")) and all(_within_root(item, value["worktree_root"]) for item in value["worktree_refs"]) and all(_ref(item) for item in value["enforcement_evidence_refs"]) and all(_digest(item) for key in ("manifest_digests", "allocation_digests") for item in value[key]) and type(value.get("timeout_seconds")) is int and 1 <= value["timeout_seconds"] <= 3600


def _adapter(value: object, approval: Mapping[str, Any], now: datetime) -> bool:
    return isinstance(value, Mapping) and set(value) == ADAPTER_FIELDS and value.get("task_id") == "phase14.5-effectful-adapter-09" and value.get("review_decision") == "accepted" and value.get("enforcement_capability") == "sandboxed_one_shot" and (value.get("adapter_id"), value.get("adapter_version")) == (approval["adapter_id"], approval["adapter_version"]) and _time(value.get("expires_at")) is not None and now.tzinfo is not None and now < _time(value["expires_at"]) and all(_identifier(value.get(key)) for key in ("adapter_id", "adapter_version")) and _digest(value.get("reviewed_commit")) and all(_ref(value.get(key)) for key in ("review_ref", "implementation_ref"))


def _grant_binding(grant: Mapping[str, Any], approval: Mapping[str, Any], agent_id: object, worktree_ref: object) -> bool:
    return grant.get("agent_id") == agent_id and grant.get("adapter_id") == approval["adapter_id"] and grant.get("adapter_version") == approval["adapter_version"] and "external-runtime-pilot" in grant.get("allowed_task_classes", []) and grant.get("network_policy") == "deny" and grant.get("worktree_root") == approval["worktree_root"] and _within_root(worktree_ref, grant.get("worktree_root"))


def _attestation(value: Mapping[str, Any], approval: Mapping[str, Any], grant_id: object, agent_id: object, worktree_ref: object, now: datetime) -> bool:
    return set(value) == ATTESTATION_FIELDS and value.get("enabled") is True and all(value.get(key) == expected for key, expected in (("task_id", TASK_ID), ("run_id", approval["run_id"]), ("grant_id", grant_id), ("agent_id", agent_id), ("worktree_ref", worktree_ref))) and value.get("restricted_writes") is True and value.get("process_identity") is True and value.get("network_egress") == "deny" and _identifier(value.get("attestation_id")) and _current(value, now)


def _enforcement_denial(approval: Mapping[str, Any]) -> dict[str, object]:
    return {"decision": "deny_platform_enforcement", "incident": {"category": "capability_mismatch", "task_id": TASK_ID, "run_id": approval["run_id"], "approval_id": approval["approval_id"]}}


def _current(value: Mapping[str, Any], now: datetime) -> bool:
    issued, expires = _time(value.get("issued_at")), _time(value.get("expires_at"))
    return now.tzinfo is not None and issued is not None and expires is not None and issued <= now < expires


def _time(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 128 and ".." not in value and all(char.isascii() and (char.isalnum() or char in "-_.") for char in value)


def _ref(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 256 and not value.startswith(("/", "\\", "./", "refs/")) and all(part not in {"", ".", ".."} and _identifier(part) for part in value.split("/"))


def _within_root(reference: object, root: object) -> bool:
    return _ref(root) and _ref(reference) and str(reference).startswith(str(root) + "/")


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
