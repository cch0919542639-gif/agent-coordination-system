#!/usr/bin/env python3
"""Read-only, project-aware operational status for registered projects.

The projector only derives state from existing local evidence.  It does not
claim work, update task cards or delivery records, invoke Git, or use network
services.  Its output intentionally contains only project IDs, task IDs, and
relative repository paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from coordination_common import parse_front_matter
from event_ledger import load_events
from event_routing import load_delivery_state
from project_registry import ProjectEntry, load_registry


TASK_STATES = ("ready", "in_progress", "review", "blocked", "done")


def _parse_time(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    for candidate in (value.replace("Z", "+00:00"), value):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
        except ValueError:
            pass
    for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _progress_evidence(project: ProjectEntry) -> dict[str, dict[str, str]]:
    """Return compact task-keyed progress evidence without exposing bodies."""
    evidence: dict[str, dict[str, str]] = {}
    progress_dir = Path(project.local_path) / "coordination" / "progress"
    if not progress_dir.is_dir():
        return evidence
    for path in sorted(progress_dir.glob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        fields: dict[str, str] = {"agent": path.stem}
        for line in lines:
            if not line.startswith("- ") or ":" not in line:
                continue
            key, value = line[2:].split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            if key in {"active_task", "status", "last_updated", "agent"}:
                fields[key] = value.strip()
        task_id = fields.get("active_task", "")
        if task_id:
            evidence[task_id] = fields
    return evidence


def _project_cards(project: ProjectEntry) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    root = Path(project.local_path)
    for state in TASK_STATES:
        card_dir = root / "coordination" / "task-board" / state
        if not card_dir.is_dir():
            continue
        for path in sorted(card_dir.glob("*.md")):
            try:
                front_matter, _body = parse_front_matter(path.read_text(encoding="utf-8"))
            except OSError:
                continue
            if not front_matter:
                continue
            task_id = str(front_matter.get("task_id", "")).strip()
            if not task_id:
                continue
            cards.append({
                "project_id": project.project_id,
                "task_id": task_id,
                "state": state,
                "status": str(front_matter.get("status", "")).strip(),
                "owner": str(front_matter.get("owner", "")).strip(),
                "execution_mode": str(front_matter.get("execution_mode", "")).strip(),
                "branch": str(front_matter.get("branch", "")).strip(),
                "path": path.relative_to(root).as_posix(),
            })
    return cards


def _incident_count(project: ProjectEntry) -> int:
    """Count incident evidence without reading or exposing incident bodies."""
    incident_dir = Path(project.local_path) / "coordination" / "incidents"
    if not incident_dir.is_dir():
        return 0
    return sum(1 for path in incident_dir.glob("*.md") if path.is_file())


def build_status(
    projects: list[ProjectEntry], events: list[object], deliveries: list[object],
    now: datetime | None = None, stale_after_hours: float = 24,
) -> dict:
    """Build deterministic status and alerts from supplied local evidence."""
    current = now or datetime.now(timezone.utc)
    threshold = current - timedelta(hours=stale_after_hours)
    alerts: list[dict[str, str]] = []
    project_rows: list[dict] = []

    for project in sorted(projects, key=lambda entry: entry.project_id):
        cards = _project_cards(project)
        by_task = {card["task_id"]: card for card in cards}
        progress = _progress_evidence(project)
        monitored = set(project.monitor_branches or [])
        incident_count = _incident_count(project)

        for card in cards:
            task_id = card["task_id"]
            if card["execution_mode"] == "WORKTREE" and card["branch"] and card["branch"] not in monitored:
                alerts.append(_alert("worker_branch_unmonitored", project.project_id, task_id,
                                     "configured worker branch is absent from monitor_branches"))
            report = progress.get(task_id)
            progress_status = report.get("status", "").strip().lower() if report else ""
            if report and (
                card["state"] != "in_progress"
                or (card["owner"] and report.get("agent") != card["owner"])
                or (progress_status and progress_status != card["state"])
            ):
                alerts.append(_alert("task_progress_mismatch", project.project_id, task_id,
                                     "task-card lifecycle or owner disagrees with progress evidence"))
            if card["state"] == "in_progress":
                observed = _parse_time(report.get("last_updated", "")) if report else None
                if observed is None or observed < threshold:
                    alerts.append(_alert("stale_in_progress", project.project_id, task_id,
                                         "in-progress task lacks recent progress evidence"))

        for task_id, report in progress.items():
            if task_id not in by_task:
                alerts.append(_alert("task_progress_mismatch", project.project_id, task_id,
                                     "progress evidence has no matching task card"))

        project_deliveries = [d for d in deliveries if getattr(d, "project_id", "") == project.project_id]
        project_events = [event for event in events if getattr(event, "project_id", "") == project.project_id]
        for delivery in project_deliveries:
            task_id = str(getattr(delivery, "task_id", ""))
            event_type = getattr(delivery, "event_type", "")
            status = getattr(delivery, "status", "")
            if event_type == "review_submitted" and status == "pending":
                alerts.append(_alert("pending_review_delivery", project.project_id, task_id,
                                     "review submission delivery remains pending"))
            if event_type == "ready_assigned" and status == "acknowledged":
                card = by_task.get(task_id)
                if card and card["state"] != "ready":
                    alerts.append(_alert("acknowledged_ready_nonready", project.project_id, task_id,
                                         "acknowledged ready delivery no longer has a ready card"))

        project_rows.append({
            "project_id": project.project_id,
            "task_count": len(cards),
            "event_count": len(project_events),
            "incident_count": incident_count,
            "alerts": sum(1 for alert in alerts if alert["project_id"] == project.project_id),
            "tasks": [{key: card[key] for key in ("task_id", "state", "status", "owner", "path")} for card in cards],
        })

    alerts.sort(key=lambda item: (item["project_id"], item["task_id"], item["code"]))
    return {"projects": project_rows, "alerts": alerts, "summary": {"projects": len(project_rows), "alerts": len(alerts)}}


def _alert(code: str, project_id: str, task_id: str, message: str) -> dict[str, str]:
    return {"code": code, "project_id": project_id, "task_id": task_id, "message": message}


def status_once(output_json: bool = False, stale_after_hours: float = 24) -> int:
    if stale_after_hours <= 0:
        raise ValueError("stale-after-hours must be positive")
    result = build_status(load_registry(), load_events(), load_delivery_state(), stale_after_hours=stale_after_hours)
    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Projects: {result['summary']['projects']}")
        print(f"Alerts: {result['summary']['alerts']}")
        for alert in result["alerts"]:
            print(f"[{alert['code']}] {alert['project_id']} / {alert['task_id']}: {alert['message']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only project-aware coordination status.")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON output.")
    parser.add_argument("--stale-after-hours", type=float, default=24, help="Progress-evidence staleness threshold (default: 24).")
    args = parser.parse_args()
    try:
        return status_once(args.json, args.stale_after_hours)
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
