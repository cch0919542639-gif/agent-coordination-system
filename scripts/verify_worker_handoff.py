#!/usr/bin/env python3
"""Read-only verification of an acknowledged local worker handoff."""
import argparse
import json

from local_agent_loop import LoopError, handoff, identifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--payload-id", required=True)
    args = parser.parse_args()
    try:
        identifier(args.task_id)
        identifier(args.owner)
        import re
        if not re.fullmatch(r"[a-f0-9]{16}", args.payload_id):
            raise LoopError("Invalid payload identifier.")
        handoff(args.task_id, args.owner, args.payload_id)
        print(json.dumps({"verified": True, "task_id": args.task_id, "payload_id": args.payload_id}))
        return 0
    except (LoopError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"verified": False, "reason": str(exc) if isinstance(exc, LoopError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
