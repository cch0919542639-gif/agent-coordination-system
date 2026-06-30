# Daily Orchestration Flow

## Purpose

This document defines the day-to-day operating rhythm for the orchestrator using the repo-first coordination system and helper scripts.

The goal is to reduce manual message relaying by turning the current scripts into a repeatable daily loop.

You can run the flow either through the individual scripts or through the unified entrypoint:

```bash
python scripts/orchestrate.py <subcommand> ...
```

## Core Idea

The orchestrator should no longer ask, "What should I do next?"

Instead, each day should follow the same rhythm:

1. inspect queues
2. dispatch ready work
3. monitor progress
4. handle blocked work
5. review submitted work
6. close accepted tasks

If you want a single recommendation for the current highest-priority action, run:

```bash
python scripts/orchestrate.py next
```

## Script Set

### Agent-side scripts

- `python scripts/list_assigned_tasks.py --owner <agent>`
- `python scripts/claim_task.py --task-id <task> --agent <agent>`
- `python scripts/submit_task.py --task-id <task> --agent <agent>`
- `python scripts/open_incident.py --task-id <task> --agent <agent> --category <cat> --summary "<text>"`

### Orchestrator-side scripts

- `python scripts/daily_orchestration_summary.py`
- `python scripts/dispatch_task.py --task-id <task> --owner <agent>`
- `python scripts/list_review_queue.py`
- `python scripts/review_task.py --task-id <task> --reviewer <name> --decision <decision> --summary "<text>"`
- `python scripts/complete_task.py --task-id <task>`

### Shared validation

- `python scripts/validate_coordination_files.py`

### Unified entrypoint

- `python scripts/orchestrate.py summary`
- `python scripts/orchestrate.py dispatch --task-id <task> --owner <agent>`
- `python scripts/orchestrate.py review --task-id <task> --reviewer <name> --decision <decision> --summary "<text>"`

## Daily Rhythm

## 1. Start Of Day: Inspect Current State

Run:

```bash
python scripts/daily_orchestration_summary.py
```

Equivalent:

```bash
python scripts/orchestrate.py summary
```

This gives you:

- how many tasks are in `ready`
- how many are `in_progress`
- how many are waiting in `review`
- how many are `blocked`
- which owners currently hold active work

If you want to highlight specific owners:

```bash
python scripts/daily_orchestration_summary.py --owners external-agent-tools-02 external-agent-docs-04
```

Then run:

```bash
python scripts/validate_coordination_files.py
```

Equivalent:

```bash
python scripts/orchestrate.py validate
```

If validation fails, fix the coordination state before dispatching new work.

Then optionally ask for the recommended next action:

```bash
python scripts/orchestrate.py next
```

## 2. Dispatch Ready Work

Choose one or more tasks from `ready/`.

Assign or reassign with:

```bash
python scripts/dispatch_task.py --task-id phase3-billing-01 --owner external-agent-backend-01
```

Equivalent:

```bash
python scripts/orchestrate.py dispatch --task-id phase3-billing-01 --owner external-agent-backend-01
```

If needed, also set the reviewer:

```bash
python scripts/dispatch_task.py --task-id phase3-billing-01 --owner external-agent-backend-01 --reviewer ORCHESTRATOR
```

Then send the agent only the minimum message:

- pull latest repo state
- list assigned tasks
- claim the assigned task

## 3. Agent Claim / Execution Path

The external agent should follow:

```bash
git pull
python scripts/list_assigned_tasks.py --owner external-agent-backend-01
python scripts/claim_task.py --task-id phase3-billing-01 --agent external-agent-backend-01
```

Equivalent:

```bash
git pull
python scripts/orchestrate.py assigned --owner external-agent-backend-01
python scripts/orchestrate.py claim --task-id phase3-billing-01 --agent external-agent-backend-01
```

Then the agent executes within scope and updates repo artifacts as needed.

## 4. Handle Blocked Work

If an agent is blocked, they should open an incident:

```bash
python scripts/open_incident.py --task-id phase3-billing-01 --agent external-agent-backend-01 --category scope_conflict --summary "Required schema file is outside allowed scope."
```

Equivalent:

```bash
python scripts/orchestrate.py incident --task-id phase3-billing-01 --agent external-agent-backend-01 --category scope_conflict --summary "Required schema file is outside allowed scope."
```

As orchestrator, blocked work should trigger one of four responses:

- clarify the spec
- split the task
- reassign the task
- take the task back directly

Do not dispatch more work to the same owner until you understand whether the blocker is local or systemic.

## 5. Review Queue Pass

Inspect the review queue:

```bash
python scripts/list_review_queue.py
```

Equivalent:

```bash
python scripts/orchestrate.py review-queue
```

For each task in review:

1. read the task card
2. read progress
3. read delivery artifacts
4. run validator
5. decide `accepted`, `needs_fix`, `reassign`, or `rejected`

Write the review report and apply the decision:

```bash
python scripts/review_task.py --task-id phase3-billing-01 --reviewer orchestrator --decision accepted --summary "Task meets acceptance criteria."
```

Equivalent:

```bash
python scripts/orchestrate.py review --task-id phase3-billing-01 --reviewer orchestrator --decision accepted --summary "Task meets acceptance criteria."
```

Example with findings:

```bash
python scripts/review_task.py --task-id phase3-billing-01 --reviewer orchestrator --decision needs_fix --summary "Missing acceptance coverage for retry path." --finding "Delivery report does not reference the retry validation." --required-change "Add retry-path evidence to the delivery report."
```

## 6. Close Accepted Work

If you want a separate explicit close step after review:

```bash
python scripts/complete_task.py --task-id phase3-billing-01
```

Equivalent:

```bash
python scripts/orchestrate.py complete --task-id phase3-billing-01
```

Use this when:

- you want the review and completion to be separate moments
- you want a final manual confirmation before moving to `done/`

## Recommended Daily Sequence

For a normal day, use this exact order:

```bash
python scripts/daily_orchestration_summary.py
python scripts/validate_coordination_files.py
python scripts/orchestrate.py next
python scripts/list_review_queue.py
python scripts/dispatch_task.py --task-id <next-task> --owner <agent>
```

Then later in the same day:

```bash
python scripts/daily_orchestration_summary.py
python scripts/review_task.py --task-id <review-task> --reviewer orchestrator --decision accepted --summary "<summary>"
python scripts/complete_task.py --task-id <review-task>
python scripts/validate_coordination_files.py
```

## Practical Operating Rules

- Review work before opening too many new tasks.
- Treat `blocked/` as higher urgency than `ready/`.
- Keep owner load balanced by checking the daily summary first.
- Do not bypass validator checks during the normal flow.
- Use chat only for short dispatch or clarification, not as the source of delivery truth.

## What This Replaces

Before these scripts, the orchestrator had to:

- manually inspect repo folders
- manually rewrite owner fields
- manually remember who had what
- manually create review files
- manually move tasks after acceptance

Now the daily loop is lighter:

- queues are listed by command
- owners are updated by command
- review files are written by command
- task closure is handled by command

## Next Level

Once this daily flow becomes routine, the next automation step is:

- command wrappers or batch scripts for common sequences
- CI validation on pull request or push
- eventual API-backed coordination instead of repo-only orchestration
