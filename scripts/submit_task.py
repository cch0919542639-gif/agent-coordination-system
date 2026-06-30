#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import delivery_file_for, find_task, move_task, progress_file_for, utc_now_string, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit an in-progress task for review.")
    parser.add_argument("--task-id", required=True, help="Task ID to submit.")
    parser.add_argument("--agent", required=True, help="Submitting agent/owner.")
    parser.add_argument(
        "--skip-delivery-check",
        action="store_true",
        help="Allow submit even if expected delivery_report is missing.",
    )
    args = parser.parse_args()

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name not in ("in_progress", "blocked"):
        print(
            f"Task `{args.task_id}` is not in in_progress/ or blocked/; current state is `{path.parent.name}`.",
            file=sys.stderr,
        )
        return 1

    current_owner = str(front_matter.get("owner", "")).strip()
    if current_owner and current_owner != args.agent:
        print(f"Task `{args.task_id}` is owned by `{current_owner}`, not `{args.agent}`.", file=sys.stderr)
        return 1

    expected_artifacts = front_matter.get("expected_artifacts", [])
    if isinstance(expected_artifacts, list) and "delivery_report" in expected_artifacts and not args.skip_delivery_check:
        delivery_path = delivery_file_for(args.task_id)
        if not delivery_path.exists():
            print(
                f"Missing required delivery report: {delivery_path}. Use --skip-delivery-check to bypass.",
                file=sys.stderr,
            )
            return 1

    destination = move_task(path, "review", front_matter, body)

    progress_path = progress_file_for(args.agent)
    if progress_path.exists():
        progress_content = (
            "# Progress Report\n\n"
            f"- Agent: {args.agent}\n"
            f"- Active Task: {args.task_id}\n"
            f"- Phase: {front_matter.get('phase')}\n"
            "- Status: WAITING_FOR_REVIEW\n"
            f"- Last Updated: {utc_now_string()}\n\n"
            "## Current Step\n\n"
            "Implementation complete. Ready for review.\n\n"
            "## Changes So Far\n\n"
            f"- {destination.relative_to(destination.parents[1])}\n\n"
            "## Blocker Status\n\n"
            "none\n\n"
            "## Next Step\n\n"
            "Await orchestrator review.\n"
        )
        write_text(progress_path, progress_content)

    print(f"Submitted task `{args.task_id}` for review.")
    print(f"Moved: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
