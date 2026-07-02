# New Agent Machine Checklist

## Purpose

Use this checklist when a new agent or a new computer joins the coordination system.

The goal is to make setup fast, consistent, and safe.

## One-Time Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd <YOUR_REPO_DIRECTORY>
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Confirm the repo is healthy

```bash
python scripts/orchestrate.py validate
```

Do not start work if validation fails.

## Required Reading

Read these before doing any task:

1. `docs/operations/agent-task-execution-protocol.md`
2. `docs/operations/agent_workflow.md`
3. `docs/operations/lead-agent-orchestration-protocol.md`
4. your assigned task card

If acting as orchestrator or reviewer, also read:

5. `docs/operations/worker-assignment-policy.md`
6. `docs/operations/daily-orchestration-flow.md`

## Every Work Session

Before starting:

```bash
git pull
python scripts/orchestrate.py validate
```

Then:

1. read the assigned task card
2. confirm `allowed_scope` and `forbidden_scope`
3. only then claim or review work

## Worker Agent Flow

If you are a worker agent:

```bash
python scripts/orchestrate.py assigned --owner <agent-name>
python scripts/orchestrate.py claim --task-id <task-id> --agent <agent-name>
```

During work:

- update `coordination/progress/<agent-name>.md`
- stay inside `allowed_scope`
- raise an incident if blocked

Before submission:

```bash
python scripts/orchestrate.py validate
python scripts/orchestrate.py submit --task-id <task-id> --agent <agent-name>
```

Then commit and push your changes.

## Reviewer Flow

If you are reviewing:

```bash
git pull
python scripts/orchestrate.py validate
python scripts/orchestrate.py review --task-id <task-id> --reviewer <reviewer-name> --decision accepted --summary "<summary>"
```

Then commit and push your changes.

## Lead Agent Flow

If you are the lead agent:

1. generate intake
2. create task cards
3. dispatch workers
4. monitor progress and incidents
5. review or route review
6. summarize back to the user

Typical commands:

```bash
python scripts/orchestrate.py intake ...
python scripts/orchestrate.py dispatch --task-id <task-id> --owner <agent-name> --output -
python scripts/orchestrate.py next
python scripts/orchestrate.py review ...
```

## Stop Conditions

Stop and ask for help if:

- validator fails
- the required change is outside `allowed_scope`
- the task card is missing or contradictory
- another agent already changed the same task state unexpectedly
- you are blocked and cannot proceed safely

## Non-Negotiable Rules

- Always `git pull` before acting.
- Always use repo files as the source of truth.
- Never rely on chat-only completion reports.
- Never self-assign unassigned work unless explicitly instructed.
- Never bypass scope restrictions by guessing.

## Fast Start Summary

If you only remember one sequence, use this:

```bash
git pull
python scripts/orchestrate.py validate
read your task card
claim or review the task
update repo evidence
validate again
commit and push
```
