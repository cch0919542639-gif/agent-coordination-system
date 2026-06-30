#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

COMMAND_MAP = {
    "validate": "validate_coordination_files.py",
    "summary": "daily_orchestration_summary.py",
    "assigned": "list_assigned_tasks.py",
    "claim": "claim_task.py",
    "submit": "submit_task.py",
    "incident": "open_incident.py",
    "review-queue": "list_review_queue.py",
    "dispatch": "dispatch_task.py",
    "review": "review_task.py",
    "complete": "complete_task.py",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single entrypoint for repo-first coordination commands.",
        epilog="Example: python scripts/orchestrate.py dispatch --task-id phase2-03 --owner external-agent-docs-04",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in COMMAND_MAP:
        subparsers.add_parser(name, help=f"Run `{COMMAND_MAP[name]}`")

    return parser


def main() -> int:
    parser = build_parser()
    known_args, passthrough = parser.parse_known_args()

    script_name = COMMAND_MAP[known_args.command]
    script_path = SCRIPT_DIR / script_name
    command = [sys.executable, str(script_path), *passthrough]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())

