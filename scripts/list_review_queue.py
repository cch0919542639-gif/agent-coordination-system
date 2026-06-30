#!/usr/bin/env python3
from __future__ import annotations

import sys

from coordination_common import list_tasks


def main() -> int:
    review_tasks = list_tasks(("review",))
    if not review_tasks:
        print("Review queue is empty.")
        return 0

    for path, front_matter in review_tasks:
        print(f"{front_matter.get('task_id')} [review]")
        print(f"  file: {path}")
        print(f"  owner: {front_matter.get('owner')}")
        print(f"  reviewer: {front_matter.get('reviewer')}")
        print(f"  phase: {front_matter.get('phase')}")
        print(f"  priority: {front_matter.get('priority')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

