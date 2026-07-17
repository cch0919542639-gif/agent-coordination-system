#!/usr/bin/env python3
"""Atomic, idempotent event ledger for Phase 12 event-driven orchestration.

Events have deterministic IDs and are appended atomically.  The ledger is
Git-ignored and contains no credentials, prompts, source code, or raw
task content.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from coordination_common import ROOT

MONITOR_DIR = ROOT / "coordination" / "monitor"
EVENTS_FILE = MONITOR_DIR / "events.jsonl"
STATE_FILE = MONITOR_DIR / "state.json"


@dataclass
class Event:
    """One detection event."""

    event_id: str
    project_id: str
    repository: str
    ref: str
    commit: str
    task_id: str
    event_type: str
    detected_at: str
    delivery_state: str = "pending"
    owner: str = ""
    reviewer: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Event:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def make_event_id(
    project_id: str,
    repository: str,
    ref: str,
    commit: str,
    task_id: str,
    event_type: str,
) -> str:
    """Generate a deterministic event ID from key inputs."""
    content = f"{project_id}:{repository}:{ref}:{commit}:{task_id}:{event_type}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def detect_event_type(front_matter: dict) -> str | None:
    """Determine event type from task-card front matter."""
    status = str(front_matter.get("status", "")).upper()
    if status == "REVIEW":
        return "review_submitted"
    if status == "READY":
        owner = str(front_matter.get("owner", "")).strip()
        if owner and owner != "UNASSIGNED":
            return "ready_assigned"
    if status == "BLOCKED":
        return "incident_opened"
    return None


def load_events() -> list[Event]:
    """Load all events from the ledger."""
    if not EVENTS_FILE.exists():
        return []
    events: list[Event] = []
    for line in EVENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            events.append(Event.from_dict(data))
        except (json.JSONDecodeError, TypeError):
            continue
    return events


def _load_event_ids() -> set[str]:
    """Load existing event IDs for fast dedup."""
    if not EVENTS_FILE.exists():
        return set()
    ids: set[str] = set()
    for line in EVENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            eid = data.get("event_id", "")
            if eid:
                ids.add(eid)
        except (json.JSONDecodeError, TypeError):
            continue
    return ids


def append_events(new_events: list[Event]) -> int:
    """Atomically append events, skipping duplicates. Returns count added."""
    if not new_events:
        return 0

    existing_ids = _load_event_ids()
    to_write = [e for e in new_events if e.event_id not in existing_ids]
    if not to_write:
        return 0

    MONITOR_DIR.mkdir(parents=True, exist_ok=True)

    # Atomic write via temp file + rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(MONITOR_DIR),
        prefix=".events-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for event in to_write:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        # Append to existing file
        with open(EVENTS_FILE, "a", encoding="utf-8") as dst:
            with open(tmp_path, "r", encoding="utf-8") as src:
                dst.write(src.read())
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return len(to_write)


def load_state() -> dict:
    """Load monitor state (cursors, last poll time, etc.)."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    """Save monitor state atomically."""
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(MONITOR_DIR),
        prefix=".state-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
        Path(tmp_path).replace(STATE_FILE)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def now_iso() -> str:
    """Current time in ISO 8601 UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
