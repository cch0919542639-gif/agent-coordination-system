from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from lease_recovery import FakeClock, LeasePolicy, LeaseRecovery
from operator_surface import critical_action_decision


NOW = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
IDENTITIES = tuple(f"agent-{index:02d}" for index in range(1, 7))


def preflight(approval: object, connector_records: object) -> dict[str, object]:
    """Test-only Phase H gate; it validates evidence, never launches anything."""
    result = critical_action_decision("external_runtime_launch", "phase14.5-six-agent-pilot-08", approval, NOW.isoformat())
    if result["decision"] != "operator_approval_recorded":
        return {"decision": "deny_missing_or_invalid_approval"}
    if not isinstance(connector_records, list) or len(connector_records) != 6:
        return {"decision": "deny_connector_evidence"}
    identities = {item.get("agent_id") for item in connector_records if isinstance(item, dict)}
    if identities != set(IDENTITIES) or any(item.get("admitted") is not True or item.get("enforcement_verified") is not True for item in connector_records if isinstance(item, dict)):
        return {"decision": "deny_connector_evidence"}
    return {"decision": "pilot_preflight_ready", "agent_ids": sorted(identities)}


def approval() -> dict[str, object]:
    return {"approval_id": "phaseh-approval-01", "action": "external_runtime_launch", "task_id": "phase14.5-six-agent-pilot-08", "issued_at": "2026-09-17T07:59:00+00:00", "expires_at": "2026-09-17T09:00:00+00:00", "enabled": True}


def connectors(*, enforced: bool = True) -> list[dict[str, object]]:
    return [{"agent_id": identity, "admitted": True, "enforcement_verified": enforced} for identity in IDENTITIES]


def test_preflight_fails_closed_without_approval_or_six_enforced_connectors() -> None:
    assert preflight(None, connectors())["decision"] == "deny_missing_or_invalid_approval"
    assert preflight(approval(), connectors(enforced=False))["decision"] == "deny_connector_evidence"
    assert preflight(approval(), connectors()[:5])["decision"] == "deny_connector_evidence"


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
