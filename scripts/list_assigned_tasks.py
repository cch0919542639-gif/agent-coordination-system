#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from coordination_common import ACTIVE_STATES, list_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="List active coordination tasks assigned to an owner.")
    parser.add_argument("--owner", required=True, help="Owner/agent name to filter by.")
    parser.add_argument(
        "--states",
        nargs="+",
        default=list(ACTIVE_STATES),
        help="Task-board states to include. Defaults to active states.",
    )
    args = parser.parse_args()

    matches = []
    for path, front_matter in list_tasks(tuple(args.states)):
        owner = str(front_matter.get("owner", "")).strip()
        if owner != args.owner:
            continue
        matches.append((path, front_matter))

    if not matches:
        print(f"No tasks found for owner `{args.owner}`.")
        return 0

    for path, front_matter in matches:
        print(f"{front_matter.get('task_id')} [{path.parent.name}]")
        print(f"  file: {path}")
        print(f"  phase: {front_matter.get('phase')}")
        print(f"  priority: {front_matter.get('priority')}")
        print(f"  reviewer: {front_matter.get('reviewer')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

