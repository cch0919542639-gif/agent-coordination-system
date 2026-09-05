#!/usr/bin/env python3
"""One-shot, in-memory OpenCode launch planning and bounded outcome handling.

This module does not read manifests, resolve executables, or provide a command
line entry point.  The only effectful boundary is an injected process factory,
which is reachable only after every immutable binding validates.  Production
process creation remains an operator-approved call outside this module.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping, Protocol

from controlplane_admission import admit, grant_digest


PILOT = {
    "runtime_id": "opencode",
    "worker_id": "external-agent-platform-33",
    "project_id": "agent-coordination-system",
    "reviewer_id": "ORCHESTRATOR",
    "branch": "agent/external-agent-platform-33/phase14.5-pilot-01",
    "worktree_ref": "worktrees/phase14.5-pilot-01",
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SAFE_ARG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./:=+-]*$")
_REQUIRED_MANIFEST = (
    "manifest_id", "manifest_digest", "run_id", "task_id", "project_id",
    "worker_id", "reviewer_id", "runtime_id", "branch", "worktree_ref",
    "executable_id", "argv", "timeout_seconds", "mode", "enabled",
)
_SENSITIVE = ("credential", "token", "secret", "password", "prompt", "output", "path")
MAX_APPROVAL_AGE_SECONDS = 300


class Process(Protocol):
    returncode: int | None

    def wait(self, timeout: int) -> int: ...

    def terminate(self) -> None: ...


ProcessFactory = Callable[[tuple[str, ...]], Process]


def manifest_digest(manifest: Mapping[str, Any]) -> str:
    """Return the canonical digest for an immutable launch manifest."""
    body = {key: value for key, value in manifest.items() if key != "manifest_digest"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def prepare(
    manifest: object,
    approval: object,
    grant: object,
    task: object,
    *,
    done_task_ids: set[str],
    active_agent_ids: set[str],
    existing_owners: Mapping[str, str],
    consumed_run_ids: set[str],
    now: datetime,
    globally_enabled: bool = True,
    stop_requested: bool = False,
) -> dict[str, object]:
    """Validate one exact launch request and return a safe plan or denial.

    The returned plan intentionally excludes the argv and worktree reference.
    They are retained only in local variables by ``run_once`` after validation.
    """
    if not _valid_manifest(manifest):
        return _decision("deny_invalid_manifest", None)
    assert isinstance(manifest, Mapping)
    if manifest["enabled"] is not True or globally_enabled is not True:
        return _decision("deny_disabled", manifest)
    if stop_requested:
        return _decision("stopped_safety_signal", manifest)
    if not _pilot_matches(manifest):
        category = "deny_worktree_mismatch" if manifest.get("worktree_ref") != PILOT["worktree_ref"] else "deny_provenance_mismatch"
        return _decision(category, manifest)
    if manifest["runtime_id"] != "opencode" or manifest["executable_id"] != "opencode":
        return _decision("deny_allowlist", manifest)
    if manifest["run_id"] in consumed_run_ids:
        return _decision("deny_duplicate", manifest)
    if not _valid_approval(approval, manifest, now):
        return _decision("deny_approval", manifest)
    if not _valid_one_shot_grant(grant, manifest):
        return _decision("deny_invalid_grant", manifest)
    assert isinstance(grant, Mapping)
    admission = admit(
        grant,
        task,
        done_task_ids=done_task_ids,
        active_agent_ids=active_agent_ids,
        existing_owners=existing_owners,
        now=now,
    )
    if admission.get("decision") != "admitted_no_launch":
        return _decision(str(admission.get("decision", "deny_admission")), manifest)
    if not _task_matches_manifest(task, manifest):
        return _decision("deny_provenance_mismatch", manifest)
    return _decision("launch_ready", manifest)


def run_once(
    manifest: object,
    approval: object,
    grant: object,
    task: object,
    *,
    done_task_ids: set[str],
    active_agent_ids: set[str],
    existing_owners: Mapping[str, str],
    consumed_run_ids: set[str],
    now: datetime,
    process_factory: ProcessFactory,
    globally_enabled: bool = True,
    stop_requested: bool = False,
) -> dict[str, object]:
    """Create at most one injected process and emit a redacted terminal result."""
    result = prepare(
        manifest, approval, grant, task, done_task_ids=done_task_ids,
        active_agent_ids=active_agent_ids, existing_owners=existing_owners,
        consumed_run_ids=consumed_run_ids, now=now, globally_enabled=globally_enabled,
        stop_requested=stop_requested,
    )
    if result["decision"] != "launch_ready":
        return result
    assert isinstance(manifest, Mapping)
    argv = tuple(manifest["argv"])
    consumed_run_ids.add(str(manifest["run_id"]))
    try:
        process = process_factory(argv)
    except Exception:
        return _decision("stopped_safety_signal", manifest)
    try:
        returncode = process.wait(timeout=int(manifest["timeout_seconds"]))
    except TimeoutError:
        try:
            process.terminate()
        except Exception:
            return _decision("stopped_safety_signal", manifest)
        return _decision("stopped_timeout", manifest)
    except Exception:
        return _decision("stopped_safety_signal", manifest)
    if returncode != 0:
        return _decision("stopped_nonzero_exit", manifest)
    return _decision("completed", manifest)


def _valid_manifest(value: object) -> bool:
    if not isinstance(value, Mapping) or any(key not in value for key in _REQUIRED_MANIFEST):
        return False
    if any(key not in _REQUIRED_MANIFEST for key in value) or any(key in str(name).lower() for name in value for key in _SENSITIVE):
        return False
    if any(not _safe_id(value[key]) for key in ("manifest_id", "run_id", "task_id", "project_id", "worker_id", "reviewer_id", "runtime_id", "executable_id")):
        return False
    if value.get("mode") != "supervised_one_shot" or type(value.get("enabled")) is not bool:
        return False
    if type(value.get("timeout_seconds")) is not int or not 1 <= value["timeout_seconds"] <= 900:
        return False
    if any(not isinstance(value.get(key), str) for key in ("branch", "worktree_ref")):
        return False
    if not isinstance(value.get("argv"), list) or not 1 <= len(value["argv"]) <= 8:
        return False
    if value["argv"][0] != "opencode" or any(not isinstance(arg, str) or not _SAFE_ARG.fullmatch(arg) for arg in value["argv"]):
        return False
    if not isinstance(value.get("manifest_digest"), str) or value["manifest_digest"] != manifest_digest(value):
        return False
    return True


def _valid_approval(approval: object, manifest: Mapping[str, Any], now: datetime) -> bool:
    if not isinstance(approval, Mapping) or set(approval) != {"approval_id", "manifest_id", "manifest_digest", "run_id", "approver_role", "issued_at", "expires_at", "mode", "enabled"}:
        return False
    if approval.get("enabled") is not True or approval.get("approver_role") != "ORCHESTRATOR" or approval.get("mode") != "supervised_one_shot":
        return False
    if any(approval.get(key) != manifest.get(key) for key in ("manifest_id", "manifest_digest", "run_id")) or not _safe_id(approval.get("approval_id")):
        return False
    issued, expires = _timestamp(approval.get("issued_at")), _timestamp(approval.get("expires_at"))
    return (
        issued is not None
        and expires is not None
        and now.tzinfo is not None
        and issued <= now < expires
        and (now - issued).total_seconds() <= MAX_APPROVAL_AGE_SECONDS
    )


def _valid_one_shot_grant(grant: object, manifest: Mapping[str, Any]) -> bool:
    if not isinstance(grant, Mapping) or grant.get("one_shot") is not True:
        return False
    task_classes = grant.get("allowed_task_classes")
    if not isinstance(task_classes, list) or any(not isinstance(value, str) for value in task_classes):
        return False
    if grant.get("agent_id") != manifest["worker_id"] or grant.get("project_id") != manifest["project_id"]:
        return False
    if grant.get("adapter_id") != "opencode" or "external-runtime-pilot" not in task_classes:
        return False
    try:
        return grant.get("grant_digest") == grant_digest(grant)
    except (TypeError, ValueError):
        return False


def _pilot_matches(manifest: Mapping[str, Any]) -> bool:
    return all(manifest.get(key) == expected for key, expected in PILOT.items())


def _task_matches_manifest(task: object, manifest: Mapping[str, Any]) -> bool:
    return isinstance(task, Mapping) and all(
        task.get(task_key) == manifest.get(manifest_key)
        for task_key, manifest_key in (
            ("task_id", "task_id"),
            ("project_id", "project_id"),
            ("owner", "worker_id"),
            ("branch", "branch"),
            ("worktree_path", "worktree_ref"),
        )
    )


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _safe_id(value: object) -> bool:
    return isinstance(value, str) and bool(_SAFE_ID.fullmatch(value))


def _decision(category: str, manifest: Mapping[str, Any] | None) -> dict[str, object]:
    result: dict[str, object] = {"decision": category, "dry_run": category != "completed"}
    if manifest is not None:
        for key in ("run_id", "manifest_id", "manifest_digest", "task_id", "runtime_id", "worker_id", "project_id", "timeout_seconds"):
            value = manifest.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                result[key] = value
    return result
