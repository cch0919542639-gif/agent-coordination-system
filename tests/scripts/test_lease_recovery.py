from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from lease_recovery import FakeClock, LeasePolicy, LeaseRecovery


NOW = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)


def leases(retry_budget: int = 1) -> tuple[FakeClock, LeaseRecovery]:
    clock = FakeClock(NOW)
    return clock, LeaseRecovery(clock, LeasePolicy(acknowledgement_seconds=10, heartbeat_seconds=20, lease_seconds=30, retry_budget=retry_budget))


def test_acknowledgement_and_heartbeat_extend_fake_lease() -> None:
    clock, model = leases()
    assert model.dispatch("task-01", "run-01")["lease_epoch"] == 1
    assert model.acknowledge("task-01", "run-01", 1)["decision"] == "accepted_acknowledge"
    clock.advance(seconds=19)
    result = model.heartbeat("task-01", "run-01", 1)
    assert result["decision"] == "accepted_heartbeat"
    assert result["heartbeat_deadline"] == "2026-09-16T08:00:39+00:00"
    assert result["lease_expires_at"] == "2026-09-16T08:00:49+00:00"


def test_acknowledgement_timeout_retries_with_a_new_fenced_epoch() -> None:
    clock, model = leases()
    model.dispatch("task-01", "run-01")
    clock.advance(seconds=10)
    recovered = model.recover_expired()
    assert recovered[0]["decision"] == "recovery_retry"
    assert recovered[0]["lease_epoch"] == 2
    assert model.acknowledge("task-01", "run-01", 1)["decision"] == "deny_stale_epoch"
    assert model.acknowledge("task-01", "run-01", 2)["decision"] == "accepted_acknowledge"


def test_expired_heartbeat_submission_and_cancellation_are_forensic_only() -> None:
    clock, model = leases()
    model.dispatch("task-01", "run-01")
    model.acknowledge("task-01", "run-01", 1)
    clock.advance(seconds=30)
    assert model.heartbeat("task-01", "run-01", 1)["decision"] == "deny_missed_heartbeat"
    for method in (model.submit, model.cancel):
        assert method("task-01", "run-01", 1)["decision"] == "deny_expired_lease"
    assert len(model.forensic_evidence) == 3
    assert model.recover_expired()[0]["lease_epoch"] == 2


def test_retry_exhaustion_routes_one_incident_and_approval_projection() -> None:
    clock, model = leases(retry_budget=0)
    model.dispatch("task-01", "run-01")
    clock.advance(seconds=10)
    result = model.recover_expired()
    assert result == [{"decision": "recovery_exhausted", "incident": model.incidents[0]}]
    assert model.incidents[0]["category"] == "lease_retry_exhausted"
    assert model.approval_queue == [{"decision": "operator_decision_required", "task_id": "task-01", "run_id": "run-01", "incident_category": "lease_retry_exhausted", "lease_epoch": 1}]
    assert model.recover_expired() == []


def test_lease_expiry_recovers_once_then_late_submission_cannot_mutate_new_epoch() -> None:
    clock, model = leases()
    model.dispatch("task-01", "run-01")
    model.acknowledge("task-01", "run-01", 1)
    clock.advance(seconds=30)
    assert model.recover_expired()[0]["decision"] == "recovery_retry"
    assert model.submit("task-01", "run-01", 1)["decision"] == "deny_stale_epoch"
    assert model.submit("task-01", "run-01", 2)["decision"] == "accepted_submission"


def test_submission_is_terminal_and_never_recovers_or_accepts_later_evidence() -> None:
    clock, model = leases()
    model.dispatch("task-01", "run-01")
    model.acknowledge("task-01", "run-01", 1)
    assert model.submit("task-01", "run-01", 1)["state"] == "submitted"
    clock.advance(seconds=30)
    assert model.recover_expired() == []
    for method in (model.submit, model.heartbeat, model.cancel):
        assert method("task-01", "run-01", 1)["decision"] == "deny_terminal_lease"
    assert model.incidents == []
    assert model.approval_queue == []


def test_missed_heartbeat_is_denied_then_recovered_with_new_epoch() -> None:
    clock, model = leases()
    model.dispatch("task-01", "run-01")
    model.acknowledge("task-01", "run-01", 1)
    clock.advance(seconds=20)
    assert model.heartbeat("task-01", "run-01", 1)["decision"] == "deny_missed_heartbeat"
    recovered = model.recover_expired()
    assert recovered[0]["decision"] == "recovery_retry"
    assert recovered[0]["recovery_reason"] == "heartbeat_missed"
    assert recovered[0]["lease_epoch"] == 2


def test_invalid_dispatch_and_policy_fail_closed() -> None:
    clock, model = leases()
    assert model.dispatch("../task", "run-01") == {"decision": "deny_invalid_dispatch"}
    assert model.dispatch("task-01", "run-01")["decision"] == "lease_dispatched"
    assert model.dispatch("task-01", "run-01") == {"decision": "deny_invalid_dispatch"}
    try:
        LeasePolicy(acknowledgement_seconds=0)
    except ValueError:
        pass
    else:  # pragma: no cover - assertion signal
        raise AssertionError("invalid policy accepted")


def test_source_has_no_runtime_network_or_persistence_apis() -> None:
    source = Path(__file__).resolve().parents[2].joinpath("scripts", "lease_recovery.py").read_text(encoding="utf-8")
    for token in ("subprocess", "Popen", "os.system", "socket", "requests", "urllib", "open(", "Path(", "git worktree", "time.sleep"):
        assert token not in source
