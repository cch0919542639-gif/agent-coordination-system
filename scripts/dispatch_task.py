#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import find_task, save_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign or reassign a task owner and optionally reviewer.")
    parser.add_argument("--task-id", required=True, help="Task ID to dispatch.")
    parser.add_argument("--owner", required=True, help="Owner/agent to assign.")
    parser.add_argument("--reviewer", help="Optional reviewer override.")
    parser.add_argument(
        "--allow-terminal",
        action="store_true",
        help="Allow dispatching tasks already in terminal states such as done/.",
    )
    args = parser.parse_args()

    try:
        path, front_matter, body = find_task(args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if path.parent.name in ("done", "cancelled") and not args.allow_terminal:
        print(
            f"Task `{args.task_id}` is in terminal state `{path.parent.name}`. Use --allow-terminal to override.",
            file=sys.stderr,
        )
        return 1

    front_matter["owner"] = args.owner
    if args.reviewer:
        front_matter["reviewer"] = args.reviewer
    save_task(path, front_matter, body)

    print(f"Dispatched task `{args.task_id}`.")
    print(f"  file: {path}")
    print(f"  owner: {args.owner}")
    if args.reviewer:
        print(f"  reviewer: {args.reviewer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
