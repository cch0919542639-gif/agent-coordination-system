"""Pure non-secret projection for a later, separately authorized L1 launch."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Mapping

from local_control_provision import (
    DRAFT_APPROVAL_FIELDS,
    PROJECT_CONTEXT_KEY,
    TASK_ID,
    _binding,
    _digest,
    _identifier,
    _network_exception,
    _ref,
    _within_root,
)
from local_opencode_live_runner import (
    PINNED_LAUNCHER,
    PINNED_RUNTIME_CONTENT_DIGEST,
    PINNED_WRAPPER_CONTENT_DIGEST,
)


LAUNCHER_IDENTITY_FIELDS = frozenset({"runtime_id", "launcher_id", "powershell_identity", "wrapper_content_digest", "runtime_content_digest"})
REVIEWED_IDENTITY_FIELDS = frozenset({"agent_id", "worktree_ref", "manifest_digest", "allocation_digest"})
FORBIDDEN_WORDS = ("api_key", "authorization", "bearer", "credential", "password", "secret", "token")


def build_nonsecret_launch_projection(approval_draft: object, reviewed_identities: object, launcher_identity: object) -> dict[str, object]:
    """Freeze only public identities; immediate-boundary values stay absent."""
    if _unsafe(approval_draft) or _unsafe(reviewed_identities) or _unsafe(launcher_identity):
        return {"decision": "deny_unsafe_projection_input"}
    if not _draft(approval_draft) or not _reviewed_identities(reviewed_identities, approval_draft) or not _launcher_identity(launcher_identity):
        return {"decision": "deny_invalid_projection"}
    assert isinstance(approval_draft, Mapping)
    bindings = approval_draft["bindings"]
    assert isinstance(bindings, list)
    projected = [_binding_projection(approval_draft, binding) for binding in bindings]
    return {
        "decision": "projected_nonsecret_no_runtime",
        "projection": {
            "schema_version": "phase14.5-nonsecret-launch-v1",
            "requests": [_request_projection(binding) for binding in projected],
            "approval_draft": _draft_projection(approval_draft, projected),
            "binding_records": projected,
            "project_context_key_names": (PROJECT_CONTEXT_KEY,),
            "launcher_identity": dict(launcher_identity),
        },
    }


def validate_nonsecret_launch_projection(value: object) -> bool:
    """Validate a builder result without consulting host or process state."""
    if not isinstance(value, Mapping) or set(value) != {"decision", "projection"} or value.get("decision") != "projected_nonsecret_no_runtime":
        return False
    projection = value.get("projection")
    if not isinstance(projection, Mapping) or set(projection) != {"schema_version", "requests", "approval_draft", "binding_records", "project_context_key_names", "launcher_identity"}:
        return False
    if projection.get("schema_version") != "phase14.5-nonsecret-launch-v1" or projection.get("project_context_key_names") != (PROJECT_CONTEXT_KEY,):
        return False
    draft, records, requests = projection.get("approval_draft"), projection.get("binding_records"), projection.get("requests")
    if not _projected_draft(draft) or not isinstance(records, list) or not isinstance(requests, list) or len(records) != len(requests) != 6:
        return False
    if not all(_projected_binding(record) for record in records) or records != draft["bindings"]:
        return False
    root = draft["worktree_root"]
    if not isinstance(root, str) or len({record["agent_id"] for record in records if isinstance(record, Mapping)}) != 6 or len({record["grant_id"] for record in records if isinstance(record, Mapping)}) != 6 or len({record["worktree_ref"] for record in records if isinstance(record, Mapping)}) != 6 or not all(isinstance(record, Mapping) and _within_root(record["worktree_ref"], root) for record in records):
        return False
    expected_requests = [_request_projection(record) for record in records if isinstance(record, Mapping)]
    return requests == expected_requests and _launcher_identity(projection.get("launcher_identity")) and not _unsafe(projection)


def _draft(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != DRAFT_APPROVAL_FIELDS:
        return False
    if value.get("action") != "local_control_start" or value.get("task_id") != TASK_ID or value.get("one_shot") is not True or value.get("enabled") is not True:
        return False
    if not _identifier(value.get("run_id")) or not _ref(value.get("worktree_root")) or not _network_exception(value.get("network_provider_exception")):
        return False
    exception = value["network_provider_exception"]
    expected = ["cleanup", "merge", "push"] if isinstance(exception, Mapping) and exception.get("enabled") else ["cleanup", "credential_access", "merge", "network_activation", "push"]
    if value.get("prohibited_actions") != expected:
        return False
    times = tuple(_time(value.get(key)) for key in ("issued_at", "expires_at", "run_window_start", "run_window_end"))
    if any(item is None for item in times):
        return False
    issued, expires, start, end = times
    assert issued is not None and expires is not None and start is not None and end is not None
    bindings = value.get("bindings")
    return issued <= start < end <= expires and isinstance(bindings, list) and len(bindings) == 6 and all(_binding(binding, str(value["worktree_root"])) for binding in bindings) and all(len({binding[key] for binding in bindings if isinstance(binding, Mapping)}) == 6 for key in ("agent_id", "grant_id", "worktree_ref"))


def _reviewed_identities(value: object, draft: object) -> bool:
    if not isinstance(value, list) or not isinstance(draft, Mapping) or not isinstance(draft.get("bindings"), list) or len(value) != 6:
        return False
    if not all(isinstance(item, Mapping) and set(item) == REVIEWED_IDENTITY_FIELDS and _identifier(item.get("agent_id")) and _ref(item.get("worktree_ref")) and _digest(item.get("manifest_digest")) and _digest(item.get("allocation_digest")) for item in value):
        return False
    expected = {(binding["agent_id"], binding["worktree_ref"], binding["manifest_digest"], binding["allocation_digest"]) for binding in draft["bindings"] if isinstance(binding, Mapping)}
    actual = {(item["agent_id"], item["worktree_ref"], item["manifest_digest"], item["allocation_digest"]) for item in value if isinstance(item, Mapping)}
    return len(expected) == len(actual) == 6 and actual == expected


def _launcher_identity(value: object) -> bool:
    return isinstance(value, Mapping) and set(value) == LAUNCHER_IDENTITY_FIELDS and value.get("runtime_id") == "opencode" and value.get("launcher_id") == PINNED_LAUNCHER["launcher_id"] and value.get("powershell_identity") == "windows-powershell-v1" and value.get("wrapper_content_digest") == PINNED_WRAPPER_CONTENT_DIGEST and value.get("runtime_content_digest") == PINNED_RUNTIME_CONTENT_DIGEST


def _binding_projection(draft: Mapping[str, object], binding: object) -> dict[str, object]:
    assert isinstance(binding, Mapping)
    result = {key: binding[key] for key in ("agent_id", "grant_id", "worktree_ref", "runtime_id", "timeout_seconds", "heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds", "stop_authority", "scheduler_ref", "lease_ref", "review_ref", "manifest_digest", "allocation_digest")}
    result.update({"task_id": draft["task_id"], "run_id": draft["run_id"]})
    result["argv_allowlist_id"] = _argv_identity(binding["argv_allowlist"])
    result["binding_id"] = _identity(result)
    result["control_level"] = "best_effort"
    result["process_tree_stop_handling"] = True
    return result


def _request_projection(binding: Mapping[str, object]) -> dict[str, object]:
    return {key: binding[key] for key in ("task_id", "run_id", "agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist_id", "timeout_seconds", "stop_authority", "binding_id")}


def _draft_projection(draft: Mapping[str, object], bindings: list[dict[str, object]]) -> dict[str, object]:
    exception = draft["network_provider_exception"]
    assert isinstance(exception, Mapping)
    return {
        "action": draft["action"], "task_id": draft["task_id"], "run_id": draft["run_id"], "one_shot": draft["one_shot"], "enabled": draft["enabled"],
        "issued_at": draft["issued_at"], "expires_at": draft["expires_at"], "run_window_start": draft["run_window_start"], "run_window_end": draft["run_window_end"], "worktree_root": draft["worktree_root"],
        "bindings": [dict(binding) for binding in bindings], "network_provider_exception": {"enabled": exception["enabled"], "environment_key_names": tuple(exception["environment_keys"])}, "prohibited_actions": draft["prohibited_actions"],
    }


def _projected_draft(value: object) -> bool:
    return isinstance(value, Mapping) and set(value) == {"action", "task_id", "run_id", "one_shot", "enabled", "issued_at", "expires_at", "run_window_start", "run_window_end", "worktree_root", "bindings", "network_provider_exception", "prohibited_actions"} and value.get("action") == "local_control_start" and value.get("task_id") == TASK_ID and _identifier(value.get("run_id")) and _ref(value.get("worktree_root")) and isinstance(value.get("bindings"), list) and len(value["bindings"]) == 6 and all(isinstance(binding, Mapping) and binding.get("task_id") == value["task_id"] and binding.get("run_id") == value["run_id"] for binding in value["bindings"]) and isinstance(value.get("network_provider_exception"), Mapping) and set(value["network_provider_exception"]) == {"enabled", "environment_key_names"} and value["network_provider_exception"].get("environment_key_names") in ((), (PROJECT_CONTEXT_KEY,))


def _projected_binding(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != {"task_id", "run_id", "agent_id", "grant_id", "worktree_ref", "runtime_id", "timeout_seconds", "heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds", "stop_authority", "scheduler_ref", "lease_ref", "review_ref", "manifest_digest", "allocation_digest", "argv_allowlist_id", "binding_id", "control_level", "process_tree_stop_handling"}:
        return False
    interval, missed, ceiling, timeout = (value.get(key) for key in ("heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds", "timeout_seconds"))
    return value.get("task_id") == TASK_ID and _identifier(value.get("run_id")) and _identifier(value.get("agent_id")) and _identifier(value.get("grant_id")) and _ref(value.get("worktree_ref")) and value.get("runtime_id") == "opencode" and _identifier(value.get("stop_authority")) and all(_ref(value.get(key)) for key in ("scheduler_ref", "lease_ref", "review_ref")) and _digest(value.get("manifest_digest")) and _digest(value.get("allocation_digest")) and isinstance(value.get("argv_allowlist_id"), str) and len(value["argv_allowlist_id"]) == 37 and value["argv_allowlist_id"].startswith("argv-") and type(timeout) is int and type(interval) is int and type(missed) is int and type(ceiling) is int and 1 <= timeout <= ceiling <= 900 and 1 <= interval <= 60 and 1 <= missed <= 10 and interval * missed <= ceiling and value.get("control_level") == "best_effort" and value.get("process_tree_stop_handling") is True and isinstance(value.get("binding_id"), str) and len(value["binding_id"]) == 40 and value["binding_id"] == _identity({key: value[key] for key in value if key not in {"binding_id", "control_level", "process_tree_stop_handling"}})


def _argv_identity(value: object) -> str:
    return "argv-" + hashlib.sha256(json.dumps(value, separators=(",", ":")).encode("utf-8")).hexdigest()[:32]


def _identity(value: Mapping[str, object]) -> str:
    return "binding-" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:32]


def _time(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _unsafe(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_unsafe(key) or _unsafe(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_unsafe(item) for item in value)
    if not isinstance(value, str) or value == "credential_access":
        return False
    normalized = value.casefold().replace("nonsecret", "")
    return any(word in normalized for word in FORBIDDEN_WORDS)
