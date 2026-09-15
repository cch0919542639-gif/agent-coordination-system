#!/usr/bin/env python3
"""Deterministic Phase E lease fencing and recovery fixtures.

This in-memory helper deliberately has no scheduler, filesystem, runtime,
network, credential, or timer-service dependency.  A caller supplies a
``FakeClock`` and consumes the safe projections it returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


def _identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= 128
        and value == value.strip()
        and ".." not in value
        and all(char.isalnum() or char in "-_." for char in value)
    )


class FakeClock:
    """UTC-only clock advanced explicitly by deterministic tests."""

    def __init__(self, now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("fake clock requires timezone-aware time")
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> datetime:
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
            raise ValueError("seconds must be a non-negative integer")
        self._now += timedelta(seconds=seconds)
        return self._now


@dataclass(frozen=True)
class LeasePolicy:
    acknowledgement_seconds: int = 30
    heartbeat_seconds: int = 60
    lease_seconds: int = 180
    retry_budget: int = 1

    def __post_init__(self) -> None:
        values = (self.acknowledgement_seconds, self.heartbeat_seconds, self.lease_seconds)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in values):
            raise ValueError("lease intervals must be positive integers")
        if self.acknowledgement_seconds > self.lease_seconds or self.heartbeat_seconds > self.lease_seconds:
            raise ValueError("lease intervals must fit within lease duration")
        if isinstance(self.retry_budget, bool) or not isinstance(self.retry_budget, int) or not 0 <= self.retry_budget <= 16:
            raise ValueError("retry budget must be between zero and sixteen")


class LeaseRecovery:
    """Tracks one active lease per ``task_id/run_id`` with epoch fencing."""

    def __init__(self, clock: FakeClock, policy: LeasePolicy = LeasePolicy()) -> None:
        self.clock = clock
        self.policy = policy
        self._leases: dict[str, dict[str, Any]] = {}
        self.incidents: list[dict[str, Any]] = []
        self.approval_queue: list[dict[str, Any]] = []
        self.forensic_evidence: list[dict[str, Any]] = []

    @staticmethod
    def _key(task_id: object, run_id: object) -> str | None:
        return f"{task_id}/{run_id}" if _identifier(task_id) and _identifier(run_id) else None

    def dispatch(self, task_id: str, run_id: str) -> dict[str, Any]:
        key = self._key(task_id, run_id)
        if key is None or key in self._leases:
            return {"decision": "deny_invalid_dispatch"}
        lease = self._new_lease(task_id, run_id, attempt=1, epoch=1)
        self._leases[key] = lease
        return self._projection(lease, "lease_dispatched")

    def acknowledge(self, task_id: str, run_id: str, lease_epoch: int) -> dict[str, Any]:
        lease, denial = self._active(task_id, run_id, lease_epoch, "acknowledge")
        if denial:
            return denial
        if self.clock.now() >= lease["acknowledgement_deadline"]:
            return self._late(lease, "acknowledge", "deny_acknowledgement_timeout")
        lease["acknowledged"] = True
        return self._projection(lease, "accepted_acknowledge")

    def heartbeat(self, task_id: str, run_id: str, lease_epoch: int) -> dict[str, Any]:
        lease, denial = self._active(task_id, run_id, lease_epoch, "heartbeat")
        if denial:
            return denial
        if not lease["acknowledged"]:
            return self._late(lease, "heartbeat", "deny_unacknowledged")
        if self.clock.now() >= lease["lease_expires_at"]:
            return self._late(lease, "heartbeat", "deny_expired_lease")
        lease["lease_expires_at"] = self.clock.now() + timedelta(seconds=self.policy.lease_seconds)
        return self._projection(lease, "accepted_heartbeat")

    def submit(self, task_id: str, run_id: str, lease_epoch: int) -> dict[str, Any]:
        lease, denial = self._active(task_id, run_id, lease_epoch, "submit")
        if denial:
            return denial
        if self.clock.now() >= lease["lease_expires_at"]:
            return self._late(lease, "submit", "deny_expired_lease")
        return self._projection(lease, "accepted_submission")

    def cancel(self, task_id: str, run_id: str, lease_epoch: int) -> dict[str, Any]:
        lease, denial = self._active(task_id, run_id, lease_epoch, "cancel")
        if denial:
            return denial
        if self.clock.now() >= lease["lease_expires_at"]:
            return self._late(lease, "cancel", "deny_expired_lease")
        lease["state"] = "cancelled"
        return self._projection(lease, "accepted_cancel")

    def recover_expired(self) -> list[dict[str, Any]]:
        """Recover every due active lease in sorted order; never loop/retry itself."""
        recovered: list[dict[str, Any]] = []
        for key in sorted(self._leases):
            lease = self._leases[key]
            if lease["state"] != "active":
                continue
            now = self.clock.now()
            reason = None
            if not lease["acknowledged"] and now >= lease["acknowledgement_deadline"]:
                reason = "acknowledgement_timeout"
            elif now >= lease["lease_expires_at"]:
                reason = "lease_expired"
            if reason is None:
                continue
            if lease["attempt"] <= self.policy.retry_budget:
                next_lease = self._new_lease(lease["task_id"], lease["run_id"], lease["attempt"] + 1, lease["lease_epoch"] + 1)
                self._leases[key] = next_lease
                recovered.append(self._projection(next_lease, "recovery_retry", recovery_reason=reason))
                continue
            lease["state"] = "exhausted"
            incident = {
                "category": "lease_retry_exhausted",
                "task_id": lease["task_id"],
                "run_id": lease["run_id"],
                "attempt": lease["attempt"],
                "lease_epoch": lease["lease_epoch"],
                "reason": reason,
                "at": now.isoformat(),
            }
            self.incidents.append(incident)
            self.approval_queue.append({
                "decision": "operator_decision_required",
                "task_id": lease["task_id"],
                "run_id": lease["run_id"],
                "incident_category": incident["category"],
                "lease_epoch": lease["lease_epoch"],
            })
            recovered.append({"decision": "recovery_exhausted", "incident": dict(incident)})
        return recovered

    def _new_lease(self, task_id: str, run_id: str, attempt: int, epoch: int) -> dict[str, Any]:
        now = self.clock.now()
        return {
            "task_id": task_id,
            "run_id": run_id,
            "attempt": attempt,
            "lease_epoch": epoch,
            "acknowledged": False,
            "state": "active",
            "acknowledgement_deadline": now + timedelta(seconds=self.policy.acknowledgement_seconds),
            "lease_expires_at": now + timedelta(seconds=self.policy.lease_seconds),
        }

    def _active(self, task_id: str, run_id: str, epoch: object, kind: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        key = self._key(task_id, run_id)
        lease = self._leases.get(key or "")
        if lease is None or isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 1:
            return None, {"decision": "deny_unknown_lease"}
        if epoch != lease["lease_epoch"]:
            return None, self._late(lease, kind, "deny_stale_epoch", received_epoch=epoch)
        if lease["state"] != "active":
            return None, self._late(lease, kind, "deny_terminal_lease")
        return lease, None

    def _late(self, lease: dict[str, Any], kind: str, decision: str, **extra: Any) -> dict[str, Any]:
        record = {"kind": kind, "decision": decision, "task_id": lease["task_id"], "run_id": lease["run_id"],
                  "lease_epoch": lease["lease_epoch"], "at": self.clock.now().isoformat(), **extra}
        self.forensic_evidence.append(record)
        return record

    @staticmethod
    def _projection(lease: dict[str, Any], decision: str, **extra: Any) -> dict[str, Any]:
        return {
            "decision": decision,
            "task_id": lease["task_id"],
            "run_id": lease["run_id"],
            "attempt": lease["attempt"],
            "lease_epoch": lease["lease_epoch"],
            "acknowledged": lease["acknowledged"],
            "state": lease["state"],
            "acknowledgement_deadline": lease["acknowledgement_deadline"].isoformat(),
            "lease_expires_at": lease["lease_expires_at"].isoformat(),
            **extra,
        }
