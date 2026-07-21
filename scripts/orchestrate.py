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
    "next": None,
    "intake": "intake_phase.py",
    "assigned": "list_assigned_tasks.py",
    "claim": "claim_task.py",
    "submit": "submit_task.py",
    "incident": "open_incident.py",
    "review-queue": "list_review_queue.py",
    "doctor": "doctor.py",
    "waves": "wave_planner.py",
    "manifest": "manifest.py",
    "worktree": "worktree_provision.py",
    "monitor": "remote_ref_monitor.py",
    "route-events": None,
    "dispatch": "dispatch_task.py",
    "review": "review_task.py",
    "complete": "complete_task.py",
    "repo-sync": "repo_sync.py",
    "worker": "worker_poller.py",
    "runtime-preflight": "runtime_adapter_preflight.py",
    "launcher-dry-run": "launcher_dry_run.py",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single entrypoint for repo-first coordination commands.",
        epilog="Example: python scripts/orchestrate.py dispatch --task-id phase2-03 --owner external-agent-docs-04",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in COMMAND_MAP:
        if name == "next":
            next_parser = subparsers.add_parser(name, help="Recommend the next orchestrator action based on repo state.")
            next_parser.add_argument(
                "--owner",
                help="Optional owner name to prioritize when suggesting ready work.",
            )
            continue
        if name == "intake":
            subparsers.add_parser(name, help="Generate a draft phase-intake markdown file from CLI input.")
            continue
        if name == "doctor":
            subparsers.add_parser(
                name,
                help="Run read-only preflight diagnostics for the orchestration environment.",
            )
            continue
        if name == "waves":
            subparsers.add_parser(
                name,
                help="Propose dependency-aware execution waves without lifecycle mutation.",
            )
            continue
        if name == "manifest":
            subparsers.add_parser(
                name,
                help="Write an immutable run manifest for an operator-approved execution wave.",
            )
            continue
        if name == "worktree":
            subparsers.add_parser(
                name,
                help="Preflight and provision a local Git worktree from an immutable manifest.",
            )
            continue
        if name == "monitor":
            monitor_parser = subparsers.add_parser(
                name,
                help="Monitor remote Git refs for task-card evidence across registered projects.",
            )
            monitor_parser.add_argument(
                "--route",
                action="store_true",
                help="After monitoring, route pending events to delivery records.",
            )
            continue
        if name == "route-events":
            subparsers.add_parser(
                name,
                help="Route pending monitor events to delivery records without fetching.",
            )
            continue
        if name == "dispatch":
            subparsers.add_parser(
                name,
                help="Dispatch a task: assign owner/reviewer and print a ready-to-send dispatch message.",
            )
            continue
        if name == "worker":
            subparsers.add_parser(
                name,
                help="Worker-side polling: register, poll, and acknowledge notifications.",
            )
            continue
        if name == "runtime-preflight":
            subparsers.add_parser(
                name,
                help="Read-only OpenCode/MiMo adapter discovery; never launches a runtime.",
            )
            continue
        if name == "launcher-dry-run":
            subparsers.add_parser(name, help="Fail-closed launcher dry run; never starts a runtime.")
            continue
        subparsers.add_parser(name, help=f"Run `{COMMAND_MAP[name]}`")

    return parser


def run_next(owner: str | None) -> int:
    from coordination_common import list_tasks

    review_tasks = list_tasks(("review",))
    if review_tasks:
        path, front_matter = review_tasks[0]
        print("Next action: review")
        print(f"Reason: there are {len(review_tasks)} task(s) waiting in review, which should be handled before new dispatch.")
        print(
            f"Suggested command: python scripts/orchestrate.py review --task-id {front_matter.get('task_id')} "
            f"--reviewer orchestrator --decision accepted --summary \"<summary>\""
        )
        print(f"Top review task: {front_matter.get('task_id')} | owner={front_matter.get('owner')} | file={path}")
        return 0

    blocked_tasks = list_tasks(("blocked",))
    if blocked_tasks:
        path, front_matter = blocked_tasks[0]
        print("Next action: unblock")
        print(f"Reason: there are {len(blocked_tasks)} blocked task(s), which have higher priority than dispatching new work.")
        print(
            f"Suggested command: inspect incident(s), then use python scripts/orchestrate.py dispatch --task-id "
            f"{front_matter.get('task_id')} --owner {front_matter.get('owner')}"
        )
        print(f"Top blocked task: {front_matter.get('task_id')} | owner={front_matter.get('owner')} | file={path}")
        return 0

    ready_tasks = list_tasks(("ready",))
    if ready_tasks:
        selected = None
        if owner:
            for path, front_matter in ready_tasks:
                if str(front_matter.get("owner", "")).strip() in (owner, "UNASSIGNED", ""):
                    selected = (path, front_matter)
                    break
        if selected is None:
            selected = ready_tasks[0]
        path, front_matter = selected
        current_owner = str(front_matter.get("owner", "")).strip()
        suggested_owner = owner or (current_owner if current_owner not in ("", "UNASSIGNED") else "<agent>")
        print("Next action: dispatch")
        print(f"Reason: no review or blocked work is pending, and there are {len(ready_tasks)} task(s) in ready.")
        print(
            f"Suggested command: python scripts/orchestrate.py dispatch --task-id {front_matter.get('task_id')} "
            f"--owner {suggested_owner}"
        )
        print(f"Top ready task: {front_matter.get('task_id')} | owner={front_matter.get('owner')} | file={path}")
        return 0

    print("Next action: idle")
    print("Reason: there are no tasks in review, blocked, or ready.")
    print("Suggested command: prepare a new phase packet or add new ready tasks.")
    return 0


def main() -> int:
    parser = build_parser()
    known_args, passthrough = parser.parse_known_args()

    if known_args.command == "next":
        return run_next(getattr(known_args, "owner", None))

    if known_args.command == "route-events":
        from routing_runner import route_pending_events
        output_json = "--json" in passthrough
        return route_pending_events(output_json=output_json)

    if known_args.command == "monitor":
        from remote_ref_monitor import monitor_once
        output_json = "--json" in passthrough
        if getattr(known_args, "route", False) and output_json:
            print("ERROR: --route --json is not supported. Run separately:", file=sys.stderr)
            print("  python scripts/orchestrate.py monitor --json", file=sys.stderr)
            print("  python scripts/orchestrate.py route-events --json", file=sys.stderr)
            return 1
        rc = monitor_once(output_json=output_json)
        if rc == 0 and getattr(known_args, "route", False):
            from routing_runner import route_pending_events
            route_rc = route_pending_events(output_json=False)
            return route_rc
        return rc

    script_name = COMMAND_MAP[known_args.command]
    script_path = SCRIPT_DIR / script_name
    command = [sys.executable, str(script_path), *passthrough]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
