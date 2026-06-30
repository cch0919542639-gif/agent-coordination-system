#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coordination_common import COORDINATION_DIR, find_task, progress_file_for, sanitize_slug, utc_now_string, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a standard incident report for a blocked task.")
    parser.add_argument("--task-id", required=True, help="Task ID associated with the incident.")
    parser.add_argument("--agent", required=True, help="Agent opening the incident.")
    parser.add_argument("--category", required=True, help="Incident category, e.g. scope_conflict.")
    parser.add_argument("--severity", default="medium", choices=["low", "medium", "high"], help="Incident severity.")
    parser.add_argument("--summary", required=True, help="Short incident summary.")
    parser.add_argument(
        "--attempted",
        default="Documented current task state and stopped at the last safe point.",
        help="What was attempted before opening the incident.",
    )
    parser.add_argument(
        "--blocker",
        default="Further progress requires orchestrator review.",
        help="Exact blocker description.",
    )
    parser.add_argument(
        "--impact",
        default="Task cannot proceed safely until the blocker is resolved.",
        help="Scope/risk impact summary.",
    )
    parser.add_argument(
        "--next-action",
        default="Orchestrator should review and decide whether to clarify, split, or reassign the task.",
        help="Recommended next action.",
    )
    args = parser.parse_args()

    try:
        _, front_matter, _ = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    timestamp = utc_now_string()
    incident_id = f"{timestamp.replace('-', '').replace(':', '').replace(' ', '-')}-{sanitize_slug(args.agent)}-{sanitize_slug(args.category)}"
    filename = f"{timestamp[:10].replace('-', '')}-{timestamp[11:16].replace(':', '')}-{sanitize_slug(args.agent)}-{sanitize_slug(args.category)}.md"
    incident_path = COORDINATION_DIR / "incidents" / filename

    incident_content = (
        "# Incident Report\n\n"
        f"- Incident ID: {incident_id.upper()}\n"
        f"- Agent: {args.agent}\n"
        f"- Task ID: {args.task_id}\n"
        f"- Phase: {front_matter.get('phase')}\n"
        f"- Severity: {args.severity}\n"
        f"- Category: {args.category}\n"
        "- Status: OPEN\n"
        f"- Created At: {timestamp}\n\n"
        "## Summary\n\n"
        f"{args.summary}\n\n"
        "## What Was Attempted\n\n"
        f"{args.attempted}\n\n"
        "## Exact Blocker\n\n"
        f"{args.blocker}\n\n"
        "## Scope / Risk Impact\n\n"
        f"{args.impact}\n\n"
        "## Recommended Next Action\n\n"
        f"{args.next_action}\n"
    )
    write_text(incident_path, incident_content)

    progress_path = progress_file_for(args.agent)
    if progress_path.exists():
        progress_content = (
            "# Progress Report\n\n"
            f"- Agent: {args.agent}\n"
            f"- Active Task: {args.task_id}\n"
            f"- Phase: {front_matter.get('phase')}\n"
            "- Status: BLOCKED\n"
            f"- Last Updated: {timestamp}\n\n"
            "## Current Step\n\n"
            "Blocked. Incident opened and awaiting orchestrator direction.\n\n"
            "## Changes So Far\n\n"
            f"- {incident_path.relative_to(incident_path.parents[1])}\n\n"
            "## Blocker Status\n\n"
            f"{args.summary}\n\n"
            "## Next Step\n\n"
            "Wait for orchestrator review and follow-up instruction.\n"
        )
        write_text(progress_path, progress_content)

    print(f"Opened incident for task `{args.task_id}`.")
    print(f"Incident file: {incident_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

