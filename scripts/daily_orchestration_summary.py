#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict

from coordination_common import COORDINATION_DIR, list_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a daily orchestration summary for the coordination repo.")
    parser.add_argument(
        "--owners",
        nargs="*",
        default=[],
        help="Optional owner names to highlight in the active task summary.",
    )
    args = parser.parse_args()

    ready_tasks = list_tasks(("ready",))
    in_progress_tasks = list_tasks(("in_progress",))
    review_tasks = list_tasks(("review",))
    blocked_tasks = list_tasks(("blocked",))

    print("Daily Orchestration Summary")
    print("===========================")
    print(f"ready: {len(ready_tasks)}")
    print(f"in_progress: {len(in_progress_tasks)}")
    print(f"review: {len(review_tasks)}")
    print(f"blocked: {len(blocked_tasks)}")
    print("")

    owner_counter: Counter[str] = Counter()
    owner_tasks: dict[str, list[str]] = defaultdict(list)
    for _, front_matter in in_progress_tasks + review_tasks + blocked_tasks:
        owner = str(front_matter.get("owner", "")).strip() or "UNASSIGNED"
        task_id = str(front_matter.get("task_id", "")).strip()
        state = str(front_matter.get("status", "")).strip()
        owner_counter[owner] += 1
        owner_tasks[owner].append(f"{task_id} ({state})")

    print("Owner Load")
    print("----------")
    if owner_counter:
        for owner, count in owner_counter.most_common():
            print(f"{owner}: {count}")
            if not args.owners or owner in args.owners:
                for task in sorted(owner_tasks[owner]):
                    print(f"  - {task}")
    else:
        print("No active owner load.")
    print("")

    print("Ready Queue")
    print("-----------")
    if ready_tasks:
        for path, front_matter in ready_tasks:
            print(
                f"{front_matter.get('task_id')} | owner={front_matter.get('owner')} | "
                f"priority={front_matter.get('priority')} | file={path}"
            )
    else:
        print("No ready tasks.")
    print("")

    print("Review Queue")
    print("------------")
    if review_tasks:
        for path, front_matter in review_tasks:
            print(
                f"{front_matter.get('task_id')} | owner={front_matter.get('owner')} | "
                f"priority={front_matter.get('priority')} | file={path}"
            )
    else:
        print("No review tasks.")
    print("")

    print("Blocked Queue")
    print("-------------")
    if blocked_tasks:
        for path, front_matter in blocked_tasks:
            print(
                f"{front_matter.get('task_id')} | owner={front_matter.get('owner')} | "
                f"priority={front_matter.get('priority')} | file={path}"
            )
    else:
        print("No blocked tasks.")
    print("")

    incidents_dir = COORDINATION_DIR / "incidents"
    incident_files = sorted(p for p in incidents_dir.glob("*.md") if p.name != ".gitkeep")
    print("Incident Files")
    print("--------------")
    if incident_files:
        for path in incident_files:
            print(path)
    else:
        print("No incident files.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

