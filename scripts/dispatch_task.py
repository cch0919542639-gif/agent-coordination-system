#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coordination_common import find_task, save_task

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
PROTOCOL_DOC = "docs/operations/agent-task-execution-protocol.md"
EXECUTION_DOC = "docs/operations/lead-agent-orchestration-protocol.md"
ASSIGNMENT_DOC = "docs/operations/worker-assignment-policy.md"


def build_dispatch_message(
    task_id: str,
    task_file: Path,
    owner: str,
    reviewer: str | None,
) -> str:
    rel_task = task_file.relative_to(ROOT).as_posix()
    agent_name = owner
    lines = [
        f"You are assigned task {task_id}.",
        "",
        "Please pull the latest repo, then read:",
        f"- {rel_task}",
        f"- {PROTOCOL_DOC}",
        "",
        "When you start:",
        f"- move the task card to coordination/task-board/in_progress/",
        f"- update coordination/progress/{agent_name}.md",
        "",
        "If blocked:",
        "- create an incident in coordination/incidents/",
        "- do not continue by guessing outside the task scope",
        "",
        "When finished:",
        "- move the task card to coordination/task-board/review/",
        "- submit repo-based delivery evidence and validation notes",
        "",
        "Protocol references:",
        f"- {PROTOCOL_DOC}",
        f"- {EXECUTION_DOC}",
        f"- {ASSIGNMENT_DOC}",
    ]
    if reviewer:
        lines.append("")
        lines.append(f"Reviewer: {reviewer}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assign or reassign a task owner, optionally update reviewer, and generate a dispatch message.",
    )
    parser.add_argument("--task-id", required=True, help="Task ID to dispatch.")
    parser.add_argument("--owner", required=True, help="Owner/agent to assign.")
    parser.add_argument("--reviewer", help="Optional reviewer override.")
    parser.add_argument(
        "--allow-terminal",
        action="store_true",
        help="Allow dispatching tasks already in terminal states such as done/.",
    )
    parser.add_argument(
        "--no-message",
        action="store_true",
        help="Suppress dispatch message output.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the dispatch message to FILE (use `-` for stdout-only, suppresses the decorated print block).",
    )
    parser.add_argument(
        "--message-only",
        action="store_true",
        help="Print the dispatch message without updating owner/reviewer.",
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

    # Update owner/reviewer unless --message-only
    if not args.message_only:
        front_matter["owner"] = args.owner
        if args.reviewer:
            front_matter["reviewer"] = args.reviewer
        save_task(path, front_matter, body)
        print(f"Dispatched task `{args.task_id}`.")
        print(f"  file: {path}")
        print(f"  owner: {args.owner}")
        if args.reviewer:
            print(f"  reviewer: {args.reviewer}")

    # Generate dispatch message
    reviewer = args.reviewer or str(front_matter.get("reviewer", "")).strip() or None
    message = build_dispatch_message(args.task_id, path, args.owner, reviewer)

    if args.output == "-":
        print(message, end="")
    elif not args.no_message:
        print()
        print("--- Dispatch Message ---")
        print(message)

    if args.output and args.output != "-":
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(message, encoding="utf-8", newline="\n")
        print(f"Dispatch message written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
