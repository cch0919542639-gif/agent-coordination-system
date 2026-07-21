"""Pure fail-closed validation for the Phase 14.5 single-pilot design.

This module validates in-memory JSON-shaped values only.  It intentionally has
no file, environment, network, or runtime-execution behavior.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any, Mapping


PILOT_BINDINGS = {
    "runtime_id": "opencode",
    "worker_id": "external-agent-platform-33",
    "project_id": "agent-coordination-system",
    "reviewer_id": "ORCHESTRATOR",
    "branch": "agent/external-agent-platform-33/phase14.5-pilot-01",
    "worktree_ref": "worktrees/phase14.5-pilot-01",
}
ALLOWLISTED_EXECUTABLE_ID = "opencode"
MAX_TIMEOUT_SECONDS = 900
_OPAQUE_ARGV_DIGEST = re.compile(r"^[a-f0-9]{64}$")

SAFE_AUDIT_SCHEMA = {
    "run_id": str,
    "manifest_id": str,
    "manifest_digest": str,
    "runtime_id": str,
    "task_id": str,
    "worker_id": str,
    "project_id": str,
    "branch_worktree_digest": str,
    "decision_category": str,
    "exit_category": str,
    "timestamp": str,
    "timeout_seconds": int,
    "safe_artifact_ref": str,
}

_REQUIRED_MANIFEST_TEXT = (
    "manifest_id",
    "manifest_digest",
    "run_id",
    "task_id",
    "project_id",
    "worker_id",
    "reviewer_id",
    "runtime_id",
    "branch",
    "worktree_ref",
    "inbox_payload_ref",
    "executable_id",
    "mode",
)


def manifest_digest(manifest: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 digest excluding the digest field itself."""
    body = {key: value for key, value in manifest.items() if key != "manifest_digest"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def validate_supervised_inputs(
    manifest: object,
    approval: object,
    inbox: object,
    audit: object,
    *,
    global_enabled: bool = True,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return a deterministic safe decision; execution is always unavailable."""
    if not isinstance(manifest, Mapping):
        return _decision("deny_missing_manifest")
    if not _valid_manifest_shape(manifest) or not _digest_matches(manifest):
        return _decision("deny_invalid_manifest", manifest)
    if manifest["enabled"] is not True or global_enabled is not True:
        return _decision("deny_disabled", manifest)
    if manifest["runtime_id"] != PILOT_BINDINGS["runtime_id"] or manifest["executable_id"] != ALLOWLISTED_EXECUTABLE_ID:
        return _decision("deny_allowlist", manifest)
    if not _valid_inbox(inbox, manifest):
        return _decision("deny_inbox", manifest)
    if not _valid_pilot_provenance(manifest):
        return _decision(_provenance_denial(manifest), manifest)
    if not _valid_audit(audit):
        return _decision("deny_invalid_audit", manifest)

    if manifest["mode"] == "dry_run":
        return _decision("dry_run_ready", manifest)
    if manifest["mode"] != "supervised_one_shot" or not _valid_approval(approval, manifest, now):
        return _decision("deny_approval", manifest)

    return _decision("supervised_launch_requires_future_executor", manifest)


def _valid_manifest_shape(manifest: Mapping[str, Any]) -> bool:
    if any(not isinstance(manifest.get(key), str) or not manifest[key] for key in _REQUIRED_MANIFEST_TEXT):
        return False
    if manifest.get("enabled") not in (True, False):
        return False
    timeout = manifest.get("timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        return False
    argv = manifest.get("argv")
    # This task never accepts a command. The one permitted array member is an
    # opaque digest that a future separately approved format may bind to argv.
    return isinstance(argv, list) and len(argv) == 1 and isinstance(argv[0], str) and bool(_OPAQUE_ARGV_DIGEST.fullmatch(argv[0]))


def _digest_matches(manifest: Mapping[str, Any]) -> bool:
    try:
        return manifest["manifest_digest"] == manifest_digest(manifest)
    except (TypeError, ValueError):
        return False


def _valid_inbox(inbox: object, manifest: Mapping[str, Any]) -> bool:
    return isinstance(inbox, Mapping) and all(
        inbox.get(key) == manifest[key]
        for key in ("worker_id", "task_id", "project_id", "inbox_payload_ref")
    )


def _valid_pilot_provenance(manifest: Mapping[str, Any]) -> bool:
    return all(manifest[key] == value for key, value in PILOT_BINDINGS.items())


def _provenance_denial(manifest: Mapping[str, Any]) -> str:
    if manifest["branch"] != PILOT_BINDINGS["branch"] or manifest["worktree_ref"] != PILOT_BINDINGS["worktree_ref"]:
        return "deny_worktree_mismatch"
    return "deny_provenance_mismatch"


def _valid_audit(audit: object) -> bool:
    if not isinstance(audit, Mapping) or not audit or any(key not in SAFE_AUDIT_SCHEMA for key in audit):
        return False
    return all(isinstance(value, SAFE_AUDIT_SCHEMA[key]) and not isinstance(value, bool) for key, value in audit.items())


def _valid_approval(approval: object, manifest: Mapping[str, Any], now: datetime | None) -> bool:
    if not isinstance(approval, Mapping) or approval.get("enabled") is not True:
        return False
    if any(
        approval.get(key) != manifest[key]
        for key in ("manifest_id", "manifest_digest", "run_id")
    ):
        return False
    if not isinstance(approval.get("approval_id"), str) or not approval["approval_id"]:
        return False
    if approval.get("approver_role") != "ORCHESTRATOR" or approval.get("mode") != "supervised_one_shot":
        return False
    issued_at, expires_at = _timestamps(approval)
    if issued_at is None or expires_at is None or issued_at >= expires_at:
        return False
    current = now or datetime.now(issued_at.tzinfo)
    return current.tzinfo is not None and issued_at <= current < expires_at


def _timestamps(approval: Mapping[str, Any]) -> tuple[datetime | None, datetime | None]:
    values: list[datetime | None] = []
    for key in ("issued_at", "expires_at"):
        value = approval.get(key)
        if not isinstance(value, str):
            return None, None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None, None
        if parsed.tzinfo is None:
            return None, None
        values.append(parsed)
    return values[0], values[1]


def _decision(category: str, manifest: Mapping[str, Any] | None = None) -> dict[str, object]:
    result: dict[str, object] = {"decision": category, "dry_run": True}
    if manifest is not None:
        for key in ("run_id", "task_id", "manifest_id", "manifest_digest", "runtime_id", "worker_id", "project_id", "timeout_seconds"):
            value = manifest.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                result[key] = value
        binding = f"{manifest.get('branch', '')}\n{manifest.get('worktree_ref', '')}"
        result["branch_worktree_digest"] = sha256(binding.encode("utf-8")).hexdigest()
    return result
