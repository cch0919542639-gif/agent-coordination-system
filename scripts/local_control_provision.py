"""L1 local-control binding validation; never provisions or launches a worker."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping


TASK_ID = "phase14.5-six-agent-pilot-08"
APPROVAL_FIELDS = frozenset({"approval_id", "launch_time", "action", "task_id", "run_id", "one_shot", "enabled", "issued_at", "expires_at", "run_window_start", "run_window_end", "worktree_root", "bindings", "network_provider_exception", "prohibited_actions"})
DRAFT_APPROVAL_FIELDS = APPROVAL_FIELDS - {"approval_id", "launch_time"}
BINDING_FIELDS = frozenset({"agent_id", "grant_id", "worktree_ref", "runtime_id", "argv_allowlist", "timeout_seconds", "heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds", "stop_authority", "scheduler_ref", "lease_ref", "review_ref", "manifest_digest", "allocation_digest"})
PROHIBITED_ACTIONS = ["cleanup", "credential_access", "merge", "network_activation", "push"]
EXCEPTION_PROHIBITED_ACTIONS = ["cleanup", "merge", "push"]
NETWORK_EXCEPTION_FIELDS = frozenset({"enabled", "network_access", "provider_configuration", "environment_keys"})
PROJECT_CONTEXT_KEY = "OPENCODE_PROJECT_WORKTREE"


def provision_local_workers(approval: object, *, now: datetime) -> dict[str, object]:
    """Validate one L1 approval and return six safe, non-launch records."""
    if not _approval(approval, now):
        return {"decision": "deny_invalid_approval"}
    assert isinstance(approval, Mapping)
    records = [_record(approval, binding) for binding in approval["bindings"]]
    return {"decision": "provisioned_best_effort_no_runtime", "records": records}


def validate_approval(approval: object, *, now: datetime) -> bool:
    """Expose the exact approval check for the separate fake process boundary."""
    return _approval(approval, now)


def materialize_launch_approval(draft: object, *, now: datetime) -> dict[str, object]:
    """Create the sole approval ID at the immediate launch boundary."""
    if not isinstance(draft, Mapping) or set(draft) != DRAFT_APPROVAL_FIELDS:
        return {"decision": "deny_invalid_approval"}
    materialized = dict(draft)
    materialized["launch_time"] = now.isoformat()
    payload = json.dumps(materialized, sort_keys=True, separators=(",", ":"))
    materialized["approval_id"] = "launch-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
    if not _approval(materialized, now):
        return {"decision": "deny_invalid_approval"}
    return {"decision": "launch_time_approval", "approval": materialized}


def _approval(value: object, now: datetime) -> bool:
    if not isinstance(value, Mapping) or set(value) != APPROVAL_FIELDS:
        return False
    if value.get("action") != "local_control_start" or value.get("task_id") != TASK_ID or value.get("one_shot") is not True or value.get("enabled") is not True:
        return False
    exception = value.get("network_provider_exception")
    if exception is not None and not _network_exception(exception):
        return False
    expected_prohibitions = EXCEPTION_PROHIBITED_ACTIONS if isinstance(exception, Mapping) and exception["enabled"] else PROHIBITED_ACTIONS
    if value.get("prohibited_actions") != expected_prohibitions:
        return False
    issued, expires, start, end, launch_time = (_time(value.get(key)) for key in ("issued_at", "expires_at", "run_window_start", "run_window_end", "launch_time"))
    if now.tzinfo is None or None in (issued, expires, start, end, launch_time) or launch_time != now or not (issued <= start <= now < end <= expires):
        return False
    if not _identifier(value.get("approval_id")) or not _identifier(value.get("run_id")) or not _ref(value.get("worktree_root")):
        return False
    draft = {key: item for key, item in value.items() if key not in {"approval_id", "launch_time"}}
    payload = json.dumps({**draft, "launch_time": str(value["launch_time"])}, sort_keys=True, separators=(",", ":"))
    if value["approval_id"] != "launch-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]:
        return False
    bindings = value.get("bindings")
    if not isinstance(bindings, list) or len(bindings) != 6 or not all(_binding(item, value["worktree_root"]) for item in bindings):
        return False
    for key in ("agent_id", "grant_id", "worktree_ref"):
        if len({item[key] for item in bindings}) != 6:
            return False
    return True


def _network_exception(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != NETWORK_EXCEPTION_FIELDS or type(value.get("enabled")) is not bool:
        return False
    if value["enabled"] is False:
        return value.get("network_access") == "deny" and value.get("provider_configuration") == "none" and value.get("environment_keys") == []
    keys = value.get("environment_keys")
    return value.get("network_access") == "configured_model_service_only" and value.get("provider_configuration") == "existing_local_opaque" and keys == [PROJECT_CONTEXT_KEY]


def _binding(value: object, root: str) -> bool:
    if not isinstance(value, Mapping) or set(value) != BINDING_FIELDS:
        return False
    if not all(_identifier(value.get(key)) for key in ("agent_id", "grant_id", "runtime_id", "stop_authority")):
        return False
    if not _within_root(value.get("worktree_ref"), root) or not _argv(value.get("argv_allowlist")):
        return False
    if type(value.get("timeout_seconds")) is not int or not 1 <= value["timeout_seconds"] <= 900:
        return False
    interval, missed, ceiling = (value.get(key) for key in ("heartbeat_interval_seconds", "missed_heartbeat_threshold", "per_child_hard_ceiling_seconds"))
    if type(interval) is not int or type(missed) is not int or type(ceiling) is not int or not (1 <= interval <= 60 and 1 <= missed <= 10 and interval * missed <= ceiling <= 900 and value["timeout_seconds"] <= ceiling):
        return False
    return all(_ref(value.get(key)) for key in ("scheduler_ref", "lease_ref", "review_ref")) and all(_digest(value.get(key)) for key in ("manifest_digest", "allocation_digest"))


def _record(approval: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, object]:
    return {"task_id": TASK_ID, "run_id": approval["run_id"], "approval_id": approval["approval_id"], "agent_id": binding["agent_id"], "grant_id": binding["grant_id"], "worktree_ref": binding["worktree_ref"], "runtime_id": binding["runtime_id"], "argv_allowlist": list(binding["argv_allowlist"]), "timeout_seconds": binding["timeout_seconds"], "stop_authority": binding["stop_authority"], "scheduler_ref": binding["scheduler_ref"], "lease_ref": binding["lease_ref"], "review_ref": binding["review_ref"], "manifest_digest": binding["manifest_digest"], "allocation_digest": binding["allocation_digest"], "control_level": "best_effort", "process_tree_stop_handling": True}


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


def _within_root(value: object, root: str) -> bool:
    return _ref(root) and _ref(value) and str(value).startswith(root + "/")


def _argv(value: object) -> bool:
    return isinstance(value, list) and 1 <= len(value) <= 16 and all(_identifier(item) for item in value)


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
