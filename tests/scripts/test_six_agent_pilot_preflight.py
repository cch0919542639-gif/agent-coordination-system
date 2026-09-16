from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from lease_recovery import FakeClock, LeasePolicy, LeaseRecovery
NOW = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
IDENTITIES = tuple(f"agent-{index:02d}" for index in range(1, 7))
TASK_ID = "phase14.5-six-agent-pilot-08"
RUN_ID = "phaseh-run-01"


def safe_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= 128 and all(char.isascii() and (char.isalnum() or char in "-_.") for char in value)


def safe_ref(value: object) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= 256 and not value.startswith(("/", "\\", "./", "refs/")) and all(safe_identifier(part) for part in value.split("/"))


def safe_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def current_time(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
    return parsed if parsed is not None and parsed.tzinfo is not None else None


def exact_approval(value: object) -> bool:
    fields = {"approval_id", "action", "task_id", "run_id", "one_shot", "enabled", "issued_at", "expires_at", "run_window_start", "run_window_end", "timeout_seconds", "stop_authority", "grant_ids", "agent_ids", "worktree_root", "worktree_refs", "network_policy", "adapter_id", "adapter_version", "enforcement_evidence_refs", "manifest_digests", "allocation_digests", "prohibited_actions"}
    if not isinstance(value, dict) or set(value) != fields or value["action"] != "external_runtime_launch" or value["task_id"] != TASK_ID or value["run_id"] != RUN_ID or value["one_shot"] is not True or value["enabled"] is not True:
        return False
    issued, expires, window_start, window_end = (current_time(value[key]) for key in ("issued_at", "expires_at", "run_window_start", "run_window_end"))
    if None in (issued, expires, window_start, window_end) or not (issued <= window_start <= NOW < window_end <= expires):
        return False
    six_ids = ("grant_ids", "agent_ids", "worktree_refs", "enforcement_evidence_refs", "manifest_digests", "allocation_digests")
    if any(not isinstance(value[key], list) or len(value[key]) != 6 or len(set(value[key])) != 6 for key in six_ids):
        return False
    if tuple(value["agent_ids"]) != IDENTITIES or not all(safe_identifier(item) for key in ("approval_id", "run_id", "stop_authority", "adapter_id", "adapter_version") for item in (value[key],)):
        return False
    if not safe_ref(value["worktree_root"]) or not all(safe_identifier(item) for item in value["grant_ids"]) or not all(safe_digest(item) for key in ("manifest_digests", "allocation_digests") for item in value[key]) or not all(safe_ref(item) for key in ("worktree_refs", "enforcement_evidence_refs") for item in value[key]):
        return False
    return value["network_policy"] == "deny" and isinstance(value["timeout_seconds"], int) and 1 <= value["timeout_seconds"] <= 3600 and value["prohibited_actions"] == ["cleanup", "credential_access", "merge", "push"]


def accepted_adapter(value: object) -> bool:
    fields = {"adapter_id", "adapter_version", "task_id", "review_decision", "review_ref", "implementation_ref", "enforcement_capability", "reviewed_commit", "expires_at"}
    if not isinstance(value, dict) or set(value) != fields or value["task_id"] != "phase14.5-effectful-adapter-09" or value["review_decision"] != "accepted" or value["enforcement_capability"] != "sandboxed_one_shot":
        return False
    expiry = current_time(value["expires_at"])
    return expiry is not None and NOW < expiry and all(safe_identifier(value[key]) for key in ("adapter_id", "adapter_version")) and safe_digest(value["reviewed_commit"]) and all(safe_ref(value[key]) for key in ("review_ref", "implementation_ref"))


def preflight(approval: object, connector_records: object, adapter_evidence: object) -> dict[str, object]:
    """Test-only Phase H gate; it validates evidence, never launches anything."""
    if not exact_approval(approval):
        return {"decision": "deny_missing_or_invalid_approval"}
    if not accepted_adapter(adapter_evidence):
        return {"decision": "deny_effectful_adapter_evidence"}
    assert isinstance(approval, dict) and isinstance(adapter_evidence, dict)
    if (adapter_evidence["adapter_id"], adapter_evidence["adapter_version"]) != (approval["adapter_id"], approval["adapter_version"]):
        return {"decision": "deny_effectful_adapter_evidence"}
    if not isinstance(connector_records, list) or len(connector_records) != 6:
        return {"decision": "deny_connector_evidence"}
    identities = {item.get("agent_id") for item in connector_records if isinstance(item, dict)}
    if identities != set(IDENTITIES) or any(item.get("admitted") is not True or item.get("enforcement_verified") is not True for item in connector_records if isinstance(item, dict)):
        return {"decision": "deny_connector_evidence"}
    return {"decision": "pilot_preflight_ready", "agent_ids": sorted(identities)}


def approval() -> dict[str, object]:
    return {"approval_id": "phaseh-approval-01", "action": "external_runtime_launch", "task_id": TASK_ID, "run_id": RUN_ID, "one_shot": True, "enabled": True, "issued_at": "2026-09-17T07:59:00+00:00", "expires_at": "2026-09-17T09:00:00+00:00", "run_window_start": "2026-09-17T08:00:00+00:00", "run_window_end": "2026-09-17T08:30:00+00:00", "timeout_seconds": 900, "stop_authority": "operator-01", "grant_ids": [f"grant-{identity}" for identity in IDENTITIES], "agent_ids": list(IDENTITIES), "worktree_root": "worktrees/phaseh", "worktree_refs": [f"worktrees/phaseh/{identity}" for identity in IDENTITIES], "network_policy": "deny", "adapter_id": "opencode", "adapter_version": "1", "enforcement_evidence_refs": [f"coordination/evidence/{identity}" for identity in IDENTITIES], "manifest_digests": [f"{index:064x}" for index in range(1, 7)], "allocation_digests": [f"{index:064x}" for index in range(7, 13)], "prohibited_actions": ["cleanup", "credential_access", "merge", "push"]}


def adapter() -> dict[str, object]:
    return {"adapter_id": "opencode", "adapter_version": "1", "task_id": "phase14.5-effectful-adapter-09", "review_decision": "accepted", "review_ref": "coordination/reviews/effectful-adapter-09", "implementation_ref": "scripts/effectful-adapter-09", "enforcement_capability": "sandboxed_one_shot", "reviewed_commit": "f" * 64, "expires_at": "2026-09-17T09:00:00+00:00"}


def connectors(*, enforced: bool = True) -> list[dict[str, object]]:
    return [{"agent_id": identity, "admitted": True, "enforcement_verified": enforced} for identity in IDENTITIES]


def test_preflight_fails_closed_without_approval_or_six_enforced_connectors() -> None:
    assert preflight(None, connectors(), adapter())["decision"] == "deny_missing_or_invalid_approval"
    assert preflight(approval(), connectors(enforced=False), adapter())["decision"] == "deny_connector_evidence"
    assert preflight(approval(), connectors()[:5], adapter())["decision"] == "deny_connector_evidence"


def test_preflight_rejects_malformed_mismatched_and_expired_exact_approval() -> None:
    malformed = approval(); malformed["command"] = "unsafe"
    assert preflight(malformed, connectors(), adapter())["decision"] == "deny_missing_or_invalid_approval"
    mismatched = approval(); mismatched["run_id"] = "other-run"
    assert preflight(mismatched, connectors(), adapter())["decision"] == "deny_missing_or_invalid_approval"
    expired = approval(); expired["expires_at"] = "2026-09-17T07:59:00+00:00"
    assert preflight(expired, connectors(), adapter())["decision"] == "deny_missing_or_invalid_approval"


def test_preflight_requires_current_accepted_effectful_adapter_evidence() -> None:
    assert preflight(approval(), connectors(), None)["decision"] == "deny_effectful_adapter_evidence"
    malformed = adapter(); malformed["review_ref"] = "/private/review"
    assert preflight(approval(), connectors(), malformed)["decision"] == "deny_effectful_adapter_evidence"
    stale = adapter(); stale["expires_at"] = "2026-09-17T07:59:00+00:00"
    assert preflight(approval(), connectors(), stale)["decision"] == "deny_effectful_adapter_evidence"
    mismatched = adapter(); mismatched["adapter_version"] = "2"
    assert preflight(approval(), connectors(), mismatched)["decision"] == "deny_effectful_adapter_evidence"


def test_six_identity_fake_clock_harness_has_bounded_fencing_and_incident_routing() -> None:
    clock = FakeClock(NOW)
    model = LeaseRecovery(clock, LeasePolicy(acknowledgement_seconds=10, heartbeat_seconds=20, lease_seconds=30, retry_budget=1))
    for identity in IDENTITIES:
        assert model.dispatch(f"task-{identity}", f"run-{identity}")["decision"] == "lease_dispatched"
        assert model.acknowledge(f"task-{identity}", f"run-{identity}", 1)["decision"] == "accepted_acknowledge"
    clock.advance(seconds=20)
    recovered = model.recover_expired()
    assert len(recovered) == 6 and {item["lease_epoch"] for item in recovered} == {2}
    assert model.submit("task-agent-01", "run-agent-01", 1)["decision"] == "deny_stale_epoch"
    exhausted_clock = FakeClock(NOW)
    exhausted = LeaseRecovery(exhausted_clock, LeasePolicy(acknowledgement_seconds=10, heartbeat_seconds=20, lease_seconds=30, retry_budget=0))
    exhausted.dispatch("task-exhausted", "run-exhausted")
    exhausted_clock.advance(seconds=10)
    assert exhausted.recover_expired()[0]["decision"] == "recovery_exhausted"
    assert len(exhausted.incidents) == len(exhausted.approval_queue) == 1


def test_protocol_preserves_no_merge_push_or_runtime_claim() -> None:
    protocol = Path(__file__).resolve().parents[2].joinpath("docs", "operations", "phase14.5-six-agent-pilot-protocol.md").read_text(encoding="utf-8")
    assert "No real pilot has run." in protocol
    assert "cannot merge or push" in protocol
    assert "six actual admitted enforcement-capable connector instances" in protocol
