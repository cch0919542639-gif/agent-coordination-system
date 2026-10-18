#!/usr/bin/env python3
"""Prepare fresh local-only registrations and a finite demo; launch nothing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from coordination_common import ROOT, save_task, utc_now_string
from local_agent_loop import PROJECT, WORKERS, digest, identifier


def prepare(run_id, workers=None):
    workers = workers or ("opencode-coordination-pilot", "hermes-coordination-pilot")
    if any(owner not in WORKERS for owner in workers):
        raise ValueError("Unsupported worker registration.")
    identifier(run_id)
    if len(run_id) > 80:
        raise ValueError("Run ID must be at most 80 characters.")
    task_ids = [f"{run_id}-{i:02}" for i in (1, 2, 3)]
    plan_path = ROOT / f"coordination/plans/{run_id}.json"
    if plan_path.exists() or (ROOT / f"coordination/monitor/local-loop/{run_id}").exists():
        raise ValueError("Run already exists; use the existing plan/resume or a fresh run ID. No receipt is reset.")
    for card in (ROOT / "coordination/task-board").glob("*/*.md"):
        from coordination_common import load_task
        if load_task(card)[0].get("task_id") in task_ids:
            raise ValueError("Task ID already exists; use a fresh run ID.")
    from project_registry import REGISTRY_FILE, ProjectEntry, add_project, get_project
    from worker_poller import WORKERS_FILE, get_worker, register_worker
    from event_routing import POLICY_FILE, RoutingPolicy, RouteRule, load_routing_policies, save_routing_policies
    # Existing malformed or conflicting machine state must never be overwritten.
    for path in (REGISTRY_FILE, WORKERS_FILE, POLICY_FILE):
        if path.exists() and not isinstance(json.loads(path.read_text(encoding="utf-8")), list):
            raise ValueError("Local registry must contain a JSON list; preserve and inspect the existing file.")
    project = get_project(PROJECT)
    if project and Path(project.local_path).resolve() != ROOT.resolve():
        raise ValueError("Project registration points to another checkout; no automatic retargeting.")
    for owner in workers:
        worker = get_worker(owner)
        if worker and (worker.project_id != PROJECT or not worker.enabled):
            raise ValueError("Worker registration conflicts or is disabled; inspect it before preparing work.")
    policies = load_routing_policies()
    matching = [p for p in policies if p.project_id == PROJECT]
    needed = {("ready_assigned", "registered_worker"), ("review_submitted", "orchestrator")}
    if matching and (len(matching) != 1 or not matching[0].enabled or
                     not needed.issubset({(r.event_type, r.destination) for r in matching[0].routes}) or
                     any(sum((r.event_type, r.destination) == pair for r in matching[0].routes) != 1 for pair in needed)):
        raise ValueError("Routing policy differs from this finite demo contract; no automatic replacement.")
    if not project:
        add_project(ProjectEntry(PROJECT, str(ROOT.resolve())))
    for owner in workers:
        if not get_worker(owner):
            register_worker(owner, PROJECT)
    if not matching:
        save_routing_policies([*policies, RoutingPolicy(PROJECT, [RouteRule(*pair) for pair in sorted(needed)])])

    directory = f"coordination/evidence/{run_id}"
    outputs = [f"{directory}/stage1.json", f"{directory}/stage2.json", f"{directory}/final.json"]
    owners = ["opencode-coordination-pilot", "hermes-coordination-pilot", "opencode-coordination-pilot"]
    expected = [{"stage": 1, "agent": "opencode", "value": 7},
                {"stage": 2, "agent": "hermes", "value": 21},
                {"status": "completed", "value": 21, "workers": ["opencode", "hermes"]}]
    objectives = [
        f"Write {outputs[0]}. On the first submission deliberately write {{\"stage\":1,\"agent\":\"opencode\",\"value\":6}} to demonstrate bounded repair; then submit a truthful report. On a same-task needs_fix repair, correct value to7. Never accept your own work.",
        f"Read the accepted {outputs[0]}, multiply its value by3, and write {outputs[1]} with exactly {{\"stage\":2,\"agent\":\"hermes\",\"value\":21}}. Submit truthful delivery evidence.",
        f"Read the accepted {outputs[1]} and write {outputs[2]} with exactly {{\"status\":\"completed\",\"value\":21,\"workers\":[\"opencode\",\"hermes\"]}}. Submit truthful delivery evidence and stop.",
    ]
    tasks = []
    date = utc_now_string().split()[0]
    for i, (task_id, owner, output, value) in enumerate(zip(task_ids, owners, outputs, expected)):
        checks = [{"path": output, "json_equals": value}]
        basename = f"{date}_{task_id}_download-loop-demo.md"
        header = {
            "task_id": task_id, "phase": "local-download-verification", "status": "READY",
            "owner": owner, "reviewer": "LOCAL_LOOP", "priority": "high",
            "dependencies": task_ids[i-1:i] if i else [],
            "allowed_scope": [f"coordination/task-board/{state}/{basename}" for state in ("ready", "in_progress", "review")]
                             + [output, f"coordination/delivery/{task_id}-delivery-report.md", f"coordination/progress/{owner}.md"],
            "forbidden_scope": ["scripts/**", "integrations/**", "tests/**", "docs/**", "coordination/plans/**", "coordination/reviews/**", "other_task_cards", "credentials", "git_commit_push_merge"],
            "acceptance": ["Preserve the exact owner-matching acknowledged payload.", "Deliver the pinned JSON artifact and truthful report; reviewer verifies independently.", "Submit only this task to REVIEW and stop."],
            "expected_artifacts": ["delivery_report"], "execution_mode": "REPO_FIRST",
            "local_loop_checks_sha256": digest(checks),
        }
        body = f"""# Task Packet

## Objective

{objectives[i]}

## Context

This is a finite, operator-authorized local download verification. Read PLAN.md,
PROGRESS.md and docs/operations/agent-task-execution-protocol.md. Codex owns
control and LOCAL_LOOP checks the exact JSON. No other task may be selected.

## Constraints

Write only allowed paths. Preserve source, plans, other cards, credentials and
existing edits. No review, accept, dispatch, agents, commit, push or merge.

## Implementation Notes

Claim only this task. Use submit_task.py --task-id {task_id} --agent {owner}
--payload-id YOUR_ACK --summary 'truthful short summary' --artifact '{output}'
for canonical reporting, validation and submission. On IN_PROGRESS repair,
skip claim and fix the review findings using the same ACK. Never reset receipts.

## Validation Steps

Check the artifact exists, run coordination validation, and submit. LOCAL_LOOP
compares JSON independently and may return needs_fix within two attempts.

## Escalation Rules

Stop on unsafe scope, wrong identity or unavailable provider. Do not fabricate
completion, alter check contracts or perform any unassigned work.
"""
        card = ROOT / f"coordination/task-board/ready/{basename}"
        card.parent.mkdir(parents=True, exist_ok=True)
        save_task(card, header, body)
        tasks.append({"task_id": task_id, "owner": owner, "checks": checks})
    plan = {"version": 1, "run_id": run_id, "tasks": tasks, "max_attempts": 2,
            "worker_timeout_seconds": 900, "check_timeout_seconds": 30, "run_timeout_seconds": 3600}
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path.relative_to(ROOT).as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Fresh bounded demo identity, never an existing run ID.")
    args = parser.parse_args()
    try:
        print(json.dumps({"prepared_plan": prepare(args.run_id), "workers_launched": 0}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
