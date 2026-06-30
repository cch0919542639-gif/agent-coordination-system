#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import find_task, move_task, progress_file_for, read_text, utc_now_string, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Claim a ready task and move it to in_progress.")
    parser.add_argument("--task-id", required=True, help="Task ID to claim.")
    parser.add_argument("--agent", required=True, help="Agent/owner claiming the task.")
    parser.add_argument(
        "--force-owner",
        action="store_true",
        help="Override the owner field if it does not already match the agent.",
    )
    args = parser.parse_args()

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name != "ready":
        print(f"Task `{args.task_id}` is not in ready/; current state is `{path.parent.name}`.", file=sys.stderr)
        return 1

    current_owner = str(front_matter.get("owner", "")).strip()
    if current_owner and current_owner not in ("UNASSIGNED", args.agent) and not args.force_owner:
        print(
            f"Task `{args.task_id}` is assigned to `{current_owner}`. Use --force-owner to override.",
            file=sys.stderr,
        )
        return 1

    front_matter["owner"] = args.agent
    destination = move_task(path, "in_progress", front_matter, body)

    progress_path = progress_file_for(args.agent)
    if not progress_path.exists():
        progress_content = (
            "# Progress Report\n\n"
            f"- Agent: {args.agent}\n"
            f"- Active Task: {args.task_id}\n"
            f"- Phase: {front_matter.get('phase')}\n"
            "- Status: IN_PROGRESS\n"
            f"- Last Updated: {utc_now_string()}\n\n"
            "## Current Step\n\n"
            "Claimed task and started work.\n\n"
            "## Changes So Far\n\n"
            f"- {destination.relative_to(destination.parents[1])}\n\n"
            "## Blocker Status\n\n"
            "none\n\n"
            "## Next Step\n\n"
            "Read the task packet, inspect referenced docs, and begin implementation.\n"
        )
        write_text(progress_path, progress_content)

    print(f"Claimed task `{args.task_id}` for `{args.agent}`.")
    print(f"Moved: {destination}")
    print(f"Progress file: {progress_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
