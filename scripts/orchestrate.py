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
    "status": "status_projector.py",
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
    from wave_planner import plan_waves

    review_tasks = list_tasks(("review",))
    if review_tasks:
        path, front_matter = review_tasks[0]
        print("Next action: controller_review")
        print(f"Reason: there are {len(review_tasks)} task(s) waiting for the lead agent's evidence-based triage.")
        print("Inspect the task card, delivery report, actual diff, and required validation evidence.")
        print("If a human decision is needed or any risk is identified, record `paused`; otherwise accept and continue dispatch.")
        print("The review command assigns work only; it does not launch a worker.")
        print(f"Top review task: {front_matter.get('task_id')} | owner={front_matter.get('owner')} | file={path}")
        return 0

    ready_tasks = list_tasks(("ready",))
    eligible_ids = set(plan_waves()["ready"])
    eligible = [(path, fm) for path, fm in ready_tasks if fm.get("task_id") in eligible_ids]
    if owner:
        eligible = [(path, fm) for path, fm in eligible if str(fm.get("owner", "")).strip() in (owner, "UNASSIGNED", "")]

    if eligible:
        path, front_matter = eligible[0]
        current_owner = str(front_matter.get("owner", "")).strip()
        suggested_owner = owner or (current_owner if current_owner not in ("", "UNASSIGNED") else "<agent>")
        print("Next action: dispatch")
        print(f"Reason: no review is pending, and `{front_matter.get('task_id')}` has all dependencies completed.")
        print(
            f"Suggested command: python scripts/orchestrate.py dispatch --task-id {front_matter.get('task_id')} "
            f"--owner {suggested_owner}"
        )
        print(f"Top eligible task: {front_matter.get('task_id')} | owner={front_matter.get('owner')} | file={path}")
        return 0

    if owner and eligible_ids:
        print("Next action: wait_for_owner")
        print(f"Reason: no dependency-ready task is unassigned or already assigned to `{owner}`.")
        print("Suggested command: inspect ready task owners or choose another owner explicitly.")
        return 0

    if ready_tasks:
        from wave_planner import dependency_blockers
        path, front_matter = ready_tasks[0]
        blockers = dependency_blockers(str(front_matter.get("task_id", "")))
        detail = ", ".join(f"{item['dependency']} ({item['state']})" for item in blockers) or "dependency graph error"
        print("Next action: resolve_dependencies")
        print(f"Reason: no ready task has all dependencies in done/. First candidate is waiting on: {detail}.")
        print(f"Task: {front_matter.get('task_id')} | file={path}")
        print("Suggested command: inspect the listed dependency cards and correct the task board; dispatch remains disabled.")
        return 0

    blocked_tasks = list_tasks(("blocked",))
    if blocked_tasks:
        path, front_matter = blocked_tasks[0]
        print("Next action: unblock")
        print(f"Reason: {len(blocked_tasks)} task(s) are in blocked/; inspect incident evidence and resolve them.")
        print(f"Top blocked task: {front_matter.get('task_id')} | owner={front_matter.get('owner')} | file={path}")
        print("A blocked task cannot be dispatched; return it to ready/ after its incident is resolved.")
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
