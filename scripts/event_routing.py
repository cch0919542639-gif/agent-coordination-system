#!/usr/bin/env python3
"""Event routing policy and safe notification payloads for Phase 12.

Consumes the monitor's local event ledger and produces compact,
deterministic notification requests.  Never invokes subprocesses,
HTTP requests, webhooks, or agent runners.  Never includes raw
task body, prompt text, credentials, or absolute machine paths.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from coordination_common import ROOT

MONITOR_DIR = ROOT / "coordination" / "monitor"
POLICY_FILE = MONITOR_DIR / "routing_policy.json"
DELIVERY_DIR = MONITOR_DIR / "delivery"
DELIVERY_FILE = DELIVERY_DIR / "delivery_state.jsonl"

SUPPORTED_EVENT_TYPES = frozenset({
    "review_submitted",
    "ready_assigned",
    "incident_opened",
    "fetch_failed",
})

SUPPORTED_DESTINATIONS = frozenset({
    "orchestrator",
    "registered_worker",
})

MAX_RETRY_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 30


# ---------------------------------------------------------------------------
# Routing policy
# ---------------------------------------------------------------------------

@dataclass
class RouteRule:
    """One event-type → destination mapping."""
    event_type: str
    destination: str

    def to_dict(self) -> dict:
        return {"event_type": self.event_type, "destination": self.destination}

    @classmethod
    def from_dict(cls, data: dict) -> RouteRule:
        return cls(event_type=data["event_type"], destination=data["destination"])


@dataclass
class RoutingPolicy:
    """Project-scoped routing policy."""
    project_id: str
    routes: list[RouteRule] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict:
        d: dict = {
            "project_id": self.project_id,
            "routes": [r.to_dict() for r in self.routes],
            "enabled": self.enabled,
        }
        return d

    @classmethod
    def from_dict(cls, data: dict) -> RoutingPolicy:
        routes = [RouteRule.from_dict(r) for r in data.get("routes", [])]
        return cls(
            project_id=data["project_id"],
            routes=routes,
            enabled=data.get("enabled", True),
        )


# ---------------------------------------------------------------------------
# Notification payload
# ---------------------------------------------------------------------------

@dataclass
class NotificationPayload:
    """Compact, safe notification payload — no raw content or paths."""
    payload_id: str
    project_id: str
    task_id: str
    event_type: str
    destination: str
    ref: str
    commit: str
    owner: str
    reviewer: str
    artifact_paths: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> NotificationPayload:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Delivery state
# ---------------------------------------------------------------------------

@dataclass
class DeliveryRecord:
    """Persistent delivery attempt / acknowledgement / retry state."""
    payload_id: str
    project_id: str
    task_id: str
    event_type: str
    destination: str
    ref: str = ""
    commit: str = ""
    owner: str = ""
    reviewer: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    status: str = "pending"
    attempts: int = 0
    last_attempt_at: str = ""
    next_retry_at: str = ""
    acknowledged_at: str = ""
    terminal_failure_at: str = ""
    failure_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DeliveryRecord:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Policy loading / validation
# ---------------------------------------------------------------------------

def load_routing_policies() -> list[RoutingPolicy]:
    """Load all routing policies from disk."""
    if not POLICY_FILE.exists():
        return []
    try:
        data = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [RoutingPolicy.from_dict(p) for p in data if isinstance(p, dict)]


def save_routing_policies(policies: list[RoutingPolicy]) -> None:
    """Save routing policies atomically."""
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    data = [p.to_dict() for p in policies]
    _atomic_write_json(POLICY_FILE, data)


def _atomic_write_json(path: Path, data: object) -> None:
    """Write JSON atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix="." + path.stem + "-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        Path(tmp_path).replace(path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def validate_policy(policy: RoutingPolicy) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    if not policy.project_id or not policy.project_id.strip():
        errors.append("policy.project_id must be non-empty")
    seen: set[tuple[str, str]] = set()
    for route in policy.routes:
        if route.event_type not in SUPPORTED_EVENT_TYPES:
            errors.append(f"unsupported event_type: {route.event_type}")
        if route.destination not in SUPPORTED_DESTINATIONS:
            errors.append(f"unsupported destination: {route.destination}")
        key = (route.event_type, route.destination)
        if key in seen:
            errors.append(f"duplicate route: {route.event_type} -> {route.destination}")
        seen.add(key)
    return errors


def get_policy_for_project(project_id: str) -> RoutingPolicy | None:
    """Look up the routing policy for a specific project."""
    for policy in load_routing_policies():
        if policy.project_id == project_id and policy.enabled:
            return policy
    return None


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

def is_eligible(
    project_id: str,
    event_type: str,
    destination: str,
) -> tuple[bool, str]:
    """Check whether an event type can be routed to a destination.

    Returns (eligible, reason).
    """
    if event_type not in SUPPORTED_EVENT_TYPES:
        return False, f"unsupported event_type: {event_type}"
    if destination not in SUPPORTED_DESTINATIONS:
        return False, f"unsupported destination: {destination}"

    policy = get_policy_for_project(project_id)
    if policy is None:
        return False, f"no routing policy for project: {project_id}"

    for route in policy.routes:
        if route.event_type == event_type and route.destination == destination:
            return True, "ok"

    return False, f"no route for {event_type} -> {destination} in project {project_id}"


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------

def build_payload(
    project_id: str,
    task_id: str,
    event_type: str,
    destination: str,
    ref: str,
    commit: str,
    owner: str = "",
    reviewer: str = "",
    artifact_paths: list[str] | None = None,
) -> NotificationPayload | None:
    """Build a safe notification payload if routing is eligible.

    Returns None if routing is not eligible.
    """
    eligible, _reason = is_eligible(project_id, event_type, destination)
    if not eligible:
        return None

    payload_id = _make_payload_id(project_id, task_id, event_type, destination)
    now = _now_iso()

    return NotificationPayload(
        payload_id=payload_id,
        project_id=project_id,
        task_id=task_id,
        event_type=event_type,
        destination=destination,
        ref=ref,
        commit=commit,
        owner=owner,
        reviewer=reviewer,
        artifact_paths=artifact_paths or [],
        created_at=now,
    )


def _make_payload_id(
    project_id: str,
    task_id: str,
    event_type: str,
    destination: str,
) -> str:
    """Deterministic payload ID from routing inputs."""
    import hashlib
    content = f"{project_id}:{task_id}:{event_type}:{destination}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def route_event(
    project_id: str,
    task_id: str,
    event_type: str,
    ref: str,
    commit: str,
    owner: str = "",
    reviewer: str = "",
    artifact_paths: list[str] | None = None,
) -> list[tuple[NotificationPayload, DeliveryRecord]]:
    """Route an event to all configured destinations for its project.

    Returns list of (payload, delivery_record) pairs for each destination.
    """
    policy = get_policy_for_project(project_id)
    if policy is None:
        return []

    results: list[tuple[NotificationPayload, DeliveryRecord]] = []
    for route in policy.routes:
        if route.event_type != event_type:
            continue
        payload = build_payload(
            project_id=project_id,
            task_id=task_id,
            event_type=event_type,
            destination=route.destination,
            ref=ref,
            commit=commit,
            owner=owner,
            reviewer=reviewer,
            artifact_paths=artifact_paths,
        )
        if payload is None:
            continue
        record = DeliveryRecord(
            payload_id=payload.payload_id,
            project_id=project_id,
            task_id=task_id,
            event_type=event_type,
            destination=route.destination,
            ref=ref,
            commit=commit,
            owner=owner,
            reviewer=reviewer,
            artifact_paths=artifact_paths or [],
            status="pending",
        )
        results.append((payload, record))

    return results


# ---------------------------------------------------------------------------
# Delivery state persistence
# ---------------------------------------------------------------------------

def load_delivery_state() -> list[DeliveryRecord]:
    """Load all delivery records from disk."""
    if not DELIVERY_FILE.exists():
        return []
    records: list[DeliveryRecord] = []
    for line in DELIVERY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            records.append(DeliveryRecord.from_dict(data))
        except (json.JSONDecodeError, TypeError):
            continue
    return records


def load_delivery_state_map() -> dict[str, DeliveryRecord]:
    """Load delivery records indexed by payload_id."""
    return {r.payload_id: r for r in load_delivery_state()}


def append_delivery_records(records: list[DeliveryRecord]) -> int:
    """Atomically append delivery records, skipping duplicates. Returns count added."""
    if not records:
        return 0

    existing = load_delivery_state_map()
    to_write = [r for r in records if r.payload_id not in existing]
    if not to_write:
        return 0

    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(DELIVERY_DIR),
        prefix=".delivery-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for record in to_write:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        with open(DELIVERY_FILE, "a", encoding="utf-8") as dst:
            with open(tmp_path, "r", encoding="utf-8") as src:
                dst.write(src.read())
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return len(to_write)


def update_delivery_record(record: DeliveryRecord) -> None:
    """Update a single delivery record in-place (idempotent)."""
    records = load_delivery_state()
    updated = False
    for i, existing in enumerate(records):
        if existing.payload_id == record.payload_id:
            records[i] = record
            updated = True
            break
    if not updated:
        records.append(record)

    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(DELIVERY_DIR),
        prefix=".delivery-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        Path(tmp_path).replace(DELIVERY_FILE)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Acknowledgement
# ---------------------------------------------------------------------------

def acknowledge(payload_id: str) -> bool:
    """Acknowledge a pending delivery. Returns True if found and updated."""
    record_map = load_delivery_state_map()
    record = record_map.get(payload_id)
    if record is None:
        return False
    if record.status == "acknowledged":
        return True  # idempotent
    record.status = "acknowledged"
    record.acknowledged_at = _now_iso()
    update_delivery_record(record)
    return True


# ---------------------------------------------------------------------------
# Retry / backoff
# ---------------------------------------------------------------------------

def mark_attempt(record: DeliveryRecord) -> DeliveryRecord:
    """Record a delivery attempt and compute next retry time."""
    record.attempts += 1
    record.last_attempt_at = _now_iso()

    if record.attempts >= MAX_RETRY_ATTEMPTS:
        record.status = "failed"
        record.terminal_failure_at = _now_iso()
        record.failure_reason = f"exceeded max retries ({MAX_RETRY_ATTEMPTS})"
    else:
        record.status = "retry_pending"
        backoff = BASE_BACKOFF_SECONDS * (2 ** (record.attempts - 1))
        next_ts = _now_epoch() + backoff
        record.next_retry_at = _epoch_to_iso(next_ts)

    update_delivery_record(record)
    return record


def is_retry_eligible(record: DeliveryRecord) -> bool:
    """Check if a record is eligible for retry based on backoff schedule."""
    if record.status != "retry_pending":
        return False
    if record.attempts >= MAX_RETRY_ATTEMPTS:
        return False
    if not record.next_retry_at:
        return False
    return _now_epoch() >= _iso_to_epoch(record.next_retry_at)


def get_pending_retries() -> list[DeliveryRecord]:
    """Get all records eligible for retry."""
    records = load_delivery_state()
    return [r for r in records if is_retry_eligible(r)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_epoch() -> float:
    return time.time()


def _epoch_to_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_to_epoch(iso_str: str) -> float:
    dt_obj = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt_obj.timestamp()
