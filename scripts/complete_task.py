#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import find_task, move_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a reviewed task as done after acceptance.")
    parser.add_argument("--task-id", required=True, help="Task ID to complete.")
    parser.add_argument(
        "--from-state",
        default="review",
        choices=["review", "in_progress", "blocked"],
        help="Current state to require before moving task to done. Defaults to review.",
    )
    args = parser.parse_args()

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name != args.from_state:
        print(
            f"Task `{args.task_id}` is not in {args.from_state}/; current state is `{path.parent.name}`.",
            file=sys.stderr,
        )
        return 1

    destination = move_task(path, "done", front_matter, body)
    print(f"Completed task `{args.task_id}`.")
    print(f"Moved: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

