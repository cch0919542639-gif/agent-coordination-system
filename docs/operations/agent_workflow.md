# Agent Workflow

## Purpose

This document is the practical command-level workflow for external agents using the repo-first coordination system.

It explains the normal path from:

- finding assigned work
- claiming a task
- doing the work
- opening an incident if blocked
- submitting for review

This guide assumes the agent is working directly against the repository and using the helper scripts in `scripts/`.

## Pre-Flight

Before doing anything else:

1. pull the latest repo state
2. read the assigned task packet
3. read `docs/operations/agent-task-execution-protocol.md`

Minimum required command:

```bash
git pull
```

## Step 1: Find Assigned Tasks

List tasks assigned to your owner name:

```bash
python scripts/list_assigned_tasks.py --owner external-agent-docs-01
```

You can limit or expand the states checked:

```bash
python scripts/list_assigned_tasks.py --owner external-agent-docs-01 --states ready in_progress review
```

If no tasks are listed, stop and wait for assignment.

## Step 2: Claim a Ready Task

When you are assigned a task in `ready/`, claim it:

```bash
python scripts/claim_task.py --task-id phase2-03 --agent external-agent-docs-04
```

What this does:

- moves the task from `coordination/task-board/ready/` to `coordination/task-board/in_progress/`
- updates the owner in the task card
- creates a basic progress file if one does not exist

If the owner field does not match but you are explicitly told to take it, use:

```bash
python scripts/claim_task.py --task-id phase2-03 --agent external-agent-docs-04 --force-owner
```

## Step 3: Work Inside Scope

After claiming the task:

- stay within `allowed_scope`
- do not touch `forbidden_scope`
- update your progress file as you make real progress

Your progress file will be under:

```text
coordination/progress/<agent-name>.md
```

If your task requires a delivery report, create or update:

```text
coordination/delivery/<task-id>-delivery-report.md
```

Use:

```text
coordination/templates/delivery-report.md
```

as the template.

## Step 4: If Blocked, Open an Incident

Do not keep guessing if the task is blocked.

Open an incident:

```bash
python scripts/open_incident.py --task-id phase2-03 --agent external-agent-docs-04 --category scope_conflict --summary "Required file is outside allowed scope."
```

Optional detail flags:

- `--severity`
- `--attempted`
- `--blocker`
- `--impact`
- `--next-action`

What this does:

- creates a standard incident markdown file in `coordination/incidents/`
- updates your progress file to `BLOCKED` if it already exists

After that, stop and wait for orchestrator direction.

## Step 5: Validate Before Submission

Before submitting, run:

```bash
python scripts/validate_coordination_files.py
```

If your task includes a delivery report, make sure it exists before submission.

## Step 6: Submit For Review

When the task is complete:

```bash
python scripts/submit_task.py --task-id phase2-03 --agent external-agent-docs-04
```

What this does:

- moves the task from `in_progress/` to `review/`
- updates the progress file to `WAITING_FOR_REVIEW`
- checks for a delivery report when the task packet requires one

If you are doing a special recovery case and need to bypass delivery report checking:

```bash
python scripts/submit_task.py --task-id phase2-03 --agent external-agent-docs-04 --skip-delivery-check
```

Do not use `--skip-delivery-check` unless explicitly instructed.

## Step 7: Wait For Review

Once submitted:

- do not keep editing the task unless the reviewer returns `needs_fix`
- watch for reviewer feedback in repo artifacts or direct instruction

To see what is currently waiting in review:

```bash
python scripts/list_review_queue.py
```

## Reviewer / Orchestrator Step

After a task is accepted, the reviewer or orchestrator can mark it done:

```bash
python scripts/complete_task.py --task-id phase2-03
```

This moves the task from `review/` to `done/`.

## Common Command Sequence

For a normal happy path:

```bash
git pull
python scripts/list_assigned_tasks.py --owner external-agent-docs-04
python scripts/claim_task.py --task-id phase2-03 --agent external-agent-docs-04
python scripts/validate_coordination_files.py
python scripts/submit_task.py --task-id phase2-03 --agent external-agent-docs-04
```

For a blocked path:

```bash
git pull
python scripts/list_assigned_tasks.py --owner external-agent-docs-04
python scripts/claim_task.py --task-id phase2-03 --agent external-agent-docs-04
python scripts/open_incident.py --task-id phase2-03 --agent external-agent-docs-04 --category scope_conflict --summary "Required file is outside allowed scope."
```

## Command Map

| Goal | Command |
|---|---|
| Find my tasks | `python scripts/list_assigned_tasks.py --owner <agent>` |
| Claim a task | `python scripts/claim_task.py --task-id <task> --agent <agent>` |
| Submit for review | `python scripts/submit_task.py --task-id <task> --agent <agent>` |
| Open incident | `python scripts/open_incident.py --task-id <task> --agent <agent> --category <cat> --summary "<text>"` |
| List review queue | `python scripts/list_review_queue.py` |
| Mark accepted task done | `python scripts/complete_task.py --task-id <task>` |

## Important Rules

- Always pull latest repo state first.
- Always read the task packet before changing files.
- Do not work outside `allowed_scope`.
- If blocked, open an incident instead of improvising.
- Do not declare completion in chat only; use repo artifacts.

