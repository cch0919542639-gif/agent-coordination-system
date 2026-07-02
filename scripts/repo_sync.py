#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SYNC_DIR = Path(__file__).resolve().parents[1] / "coordination" / "sync"
SAFE_PREFIXES = (
    str(SYNC_DIR.resolve()),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_db(db_path: str) -> dict:
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    phases = [dict(r) for r in cursor.execute("SELECT * FROM phases ORDER BY created_at").fetchall()]
    tasks = [dict(r) for r in cursor.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()]
    agents = [dict(r) for r in cursor.execute("SELECT * FROM agents ORDER BY name").fetchall()]
    assignments = [dict(r) for r in cursor.execute(
        "SELECT * FROM assignments ORDER BY assigned_at"
    ).fetchall()]
    incidents = [dict(r) for r in cursor.execute(
        "SELECT * FROM incidents ORDER BY created_at DESC"
    ).fetchall()]
    reviews = [dict(r) for r in cursor.execute(
        "SELECT * FROM reviews ORDER BY created_at DESC"
    ).fetchall()]
    recent_events = [dict(r) for r in cursor.execute(
        "SELECT * FROM task_events ORDER BY created_at DESC LIMIT 20"
    ).fetchall()]

    conn.close()
    return {
        "phases": phases,
        "tasks": tasks,
        "agents": agents,
        "assignments": assignments,
        "incidents": incidents,
        "reviews": reviews,
        "recent_events": recent_events,
    }


def _render_tasks_summary(data: dict) -> str:
    tasks = data["tasks"]
    counts: Dict[str, int] = {}
    for t in tasks:
        s = t.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1

    lines = ["### Task Status Summary", "", "| Status | Count |", "|---|---|"]
    for status in sorted(counts):
        lines.append(f"| {status} | {counts[status]} |")
    lines.append("")
    return "\n".join(lines)


def _render_active_assignments(data: dict) -> str:
    active = [a for a in data["assignments"] if a.get("closed_at") is None]
    if not active:
        return "### Active Assignments\n\n(none)\n"

    lines = ["### Active Assignments", "", "| Task | Agent | Since | Lease Expires |", "|---|---|---|---|"]
    for a in active:
        lease = a.get("lease_expires_at", "")
        lines.append(f"| {a['task_id']} | {a['agent_id']} | {a['assigned_at'][:19]} | {lease[:19] if lease else '-'} |")
    lines.append("")
    return "\n".join(lines)


def _render_open_incidents(data: dict) -> str:
    open_incidents = [i for i in data["incidents"] if i.get("status") == "open"]
    if not open_incidents:
        return "### Open Incidents\n\n(none)\n"

    lines = ["### Open Incidents", "", "| Incident | Task | Severity | Agent | Summary |", "|---|---|---|---|---|"]
    for i in open_incidents:
        lines.append(f"| {i['incident_id'][:8]}... | {i['task_id']} | {i['severity']} | {i['agent_id']} | {i['summary'][:50]} |")
    lines.append("")
    return "\n".join(lines)


def _render_phases(data: dict) -> str:
    phases = data["phases"]
    if not phases:
        return "### Phases\n\n(none)\n"

    lines = ["### Phases", "", "| Phase | Name | Status |", "|---|---|---|"]
    for p in phases:
        lines.append(f"| {p['phase_id']} | {p['name']} | {p['status']} |")
    lines.append("")
    return "\n".join(lines)


def _render_all_tasks(data: dict) -> str:
    tasks = data["tasks"]
    if not tasks:
        return "### Tasks\n\n(none)\n"

    active_assignments = {a["task_id"]: a for a in data["assignments"] if a.get("closed_at") is None}

    lines = ["### All Tasks", "", "| Task | Phase | Status | Priority | Assignee |", "|---|---|---|---|---|"]
    for t in tasks:
        assignee = ""
        active = active_assignments.get(t["task_id"])
        if active:
            assignee = active["agent_id"]
        lines.append(f"| {t['task_id']} | {t['phase_id']} | {t['status']} | {t.get('priority', 'medium')} | {assignee} |")
    lines.append("")
    return "\n".join(lines)


def _render_recent_events(data: dict) -> str:
    events = data.get("recent_events", [])
    if not events:
        return "### Recent Events\n\n(none)\n"

    lines = ["### Recent Events (last 20)", "", "| Time | Task | Type | Actor |", "|---|---|---|---|"]
    for e in events:
        lines.append(f"| {e['created_at'][:19]} | {e['task_id']} | {e['event_type']} | {e['actor_id']} |")
    lines.append("")
    return "\n".join(lines)


def render_state_snapshot(data: dict) -> str:
    ts = _now()[:19]
    parts = [
        "# Coordination State Snapshot",
        "",
        f"- Generated: {ts} UTC",
        f"- Tasks: {len(data['tasks'])}",
        f"- Phases: {len(data['phases'])}",
        f"- Agents: {len(data['agents'])}",
        f"- Open Incidents: {len([i for i in data['incidents'] if i.get('status') == 'open'])}",
        f"- Active Assignments: {len([a for a in data['assignments'] if a.get('closed_at') is None])}",
        "",
        "---",
        "",
        _render_phases(data),
        "---",
        "",
        _render_tasks_summary(data),
        "",
        _render_all_tasks(data),
        "---",
        "",
        _render_active_assignments(data),
        "---",
        "",
        _render_open_incidents(data),
        "---",
        "",
        _render_recent_events(data),
    ]
    return "\n".join(parts)


def _is_safe_path(path: Path) -> bool:
    resolved = path.resolve()
    return any(str(resolved).startswith(prefix) for prefix in SAFE_PREFIXES)


def sync(db_path: str, dry_run: bool = False) -> List[str]:
    data = _read_db(db_path)
    snapshot = render_state_snapshot(data)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    files: List[Path] = [SYNC_DIR / "state-snapshot.md"]
    manifest = []

    for fp in files:
        if not _is_safe_path(fp):
            raise RuntimeError(f"Refusing to write outside safe zone: {fp}")

        if dry_run:
            manifest.append(f"[DRY-RUN] would write {fp.relative_to(Path.cwd())} ({len(snapshot)} chars)")
        else:
            fp.write_text(snapshot, encoding="utf-8")
            manifest.append(f"wrote {fp.relative_to(Path.cwd())} ({len(snapshot)} chars)")

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project coordination DB state into repo-backed coordination artifacts."
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to coordination SQLite database (default: $COORDINATION_DB_PATH or coordination.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without writing any files",
    )
    args = parser.parse_args()

    import os

    db_path = args.db_path or os.environ.get("COORDINATION_DB_PATH", "coordination.db")
    if not Path(db_path).exists():
        print(f"error: database not found at {db_path}", file=sys.stderr)
        return 1

    try:
        manifest = sync(db_path, dry_run=args.dry_run)
        for entry in manifest:
            print(entry)
        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
