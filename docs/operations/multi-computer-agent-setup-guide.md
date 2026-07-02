# Multi-Computer Agent Setup Guide

## Purpose

This guide explains how to run the repo-first coordination system across multiple computers and multiple agents.

It is written for the practical case where:

- one person or lead agent acts as the orchestrator
- several external agents work on different machines
- GitHub is the shared source of truth
- repo files, not chat logs, define task state

## Core Model

The shared coordination layer is the repository itself.

Each participating computer should use the same GitHub repository and the same repo structure.

Every agent should treat these as the operational truth:

- `coordination/task-board/`
- `coordination/progress/`
- `coordination/incidents/`
- `coordination/delivery/`
- `coordination/reviews/`
- `docs/operations/`

This means the system can recover from:

- chat loss
- tool restart
- switching computers
- replacing one agent with another

## What Each Computer Needs

Minimum requirements:

- Git
- Python 3.13+
- access to the shared GitHub repository

Recommended:

- ability to run `python`
- ability to `git pull`, `git add`, `git commit`, and `git push`

## First-Time Setup On A New Computer

### 1. Clone The Repository

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd <YOUR_REPO_DIRECTORY>
```

### 2. Install Dependencies

If you want the full script and API workflow available:

```bash
python -m pip install -r requirements.txt
```

For repo-first documentation and task-board work, many tasks can still proceed with only Python available, but installing dependencies is the clean default.

### 3. Validate The Repo State

Run:

```bash
python scripts/orchestrate.py validate
```

If this fails, do not start new work until the coordination state is fixed.

### 4. Read The Required Operating Docs

At minimum:

- `docs/operations/agent-task-execution-protocol.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/worker-assignment-policy.md`
- `docs/operations/agent_workflow.md`

If the machine is used by the orchestrator or lead agent, also read:

- `docs/operations/daily-orchestration-flow.md`
- `docs/operations/intake-command-usage.md`

## Standard Roles Across Computers

### Lead Agent / Orchestrator Computer

This machine is responsible for:

- receiving the requirement
- generating intake
- creating task cards
- dispatching work
- reviewing results
- deciding fix, reassign, or accept

Typical commands:

```bash
python scripts/orchestrate.py intake ...
python scripts/orchestrate.py validate
python scripts/orchestrate.py dispatch --task-id <task> --owner <agent> --output -
python scripts/orchestrate.py review --task-id <task> --reviewer orchestrator --decision accepted --summary "<summary>"
python scripts/orchestrate.py next
```

### Worker Agent Computer

This machine is responsible for:

- pulling the latest repo state
- reading the assigned task
- claiming the task
- working only inside allowed scope
- updating progress
- submitting to review

Typical commands:

```bash
git pull
python scripts/orchestrate.py assigned --owner <agent>
python scripts/orchestrate.py claim --task-id <task> --agent <agent>
python scripts/orchestrate.py validate
python scripts/orchestrate.py submit --task-id <task> --agent <agent>
git add .
git commit -m "<task update>"
git push
```

### Reviewer Agent Computer

This machine is responsible for:

- reading the task in `review/`
- checking delivery evidence
- checking validation and tests
- writing review outcomes

Typical commands:

```bash
git pull
python scripts/orchestrate.py validate
python scripts/orchestrate.py review --task-id <task> --reviewer <reviewer> --decision accepted --summary "<summary>"
git add .
git commit -m "Review <task>"
git push
```

## Daily Start Sequence For Every Agent

Before starting work on any machine:

```bash
git pull
python scripts/orchestrate.py validate
```

Then:

- read your assigned task or review target
- confirm current board state
- proceed only after repo state is current

## How To Use GitHub As The Shared Coordination Channel

GitHub is the cross-computer memory.

The practical rule is:

- no local-only task state should be trusted
- if it is not committed and pushed, it does not reliably exist for the team

That means:

- task card changes should be committed
- progress changes should be committed
- incidents should be committed
- delivery reports should be committed
- review outcomes should be committed

## Recommended Sync Rhythm

Each agent should follow this rhythm:

### Before starting work

```bash
git pull
```

### After a meaningful checkpoint

Update repo artifacts, then:

```bash
git add .
git commit -m "<short checkpoint message>"
git push
```

### Before review submission

```bash
git pull
python scripts/orchestrate.py validate
git add .
git commit -m "<task ready for review>"
git push
```

### Before reviewing someone else's work

```bash
git pull
python scripts/orchestrate.py validate
```

## How All Agents Participate In One Flow

The clean operating model is:

1. user gives requirement to lead agent
2. lead agent creates intake
3. lead agent creates ready task cards
4. lead agent dispatches worker A, B, and C
5. each worker pulls latest repo on their own computer
6. each worker claims and executes only their assigned task
7. each worker submits to review and pushes their repo updates
8. reviewer or orchestrator pulls latest repo and performs review
9. accepted tasks move to `done/`
10. lead agent summarizes the phase result back to the user

## Example: First Real Multi-Agent Loop

### On the lead-agent machine

```bash
python scripts/orchestrate.py intake --phase-id phase7-example --objective "Implement feature X" --in-scope "src/example/**" --task '{"id":"phase7-01","objective":"Build service","priority":"high","deps":[],"allowed_scope":["src/example/**"],"forbidden_scope":["docs/**"],"acceptance":["Service works"]}'
python scripts/orchestrate.py validate
python scripts/orchestrate.py dispatch --task-id phase7-01 --owner external-agent-backend-01 --output -
```

Copy the printed dispatch message and send it to the worker.

### On the worker machine

```bash
git pull
python scripts/orchestrate.py assigned --owner external-agent-backend-01
python scripts/orchestrate.py claim --task-id phase7-01 --agent external-agent-backend-01
```

Do the work, update progress, submit for review, then push.

### On the reviewer / orchestrator machine

```bash
git pull
python scripts/orchestrate.py validate
python scripts/orchestrate.py review --task-id phase7-01 --reviewer orchestrator --decision accepted --summary "Task meets acceptance criteria."
git add .
git commit -m "Accept phase7-01"
git push
```

## When To Use The Coordination API

The coordination API is optional for the repo-first operating model.

Use it when you want:

- HTTP-based coordination instead of only file-state coordination
- lease / heartbeat / recovery behavior
- agent CLI calls against an API
- future automation that polls a service instead of reading files directly

Do not make the API a prerequisite for basic multi-computer collaboration.

For startup details, see:

- `docs/operations/coordination-api-startup-guide.md`

## Rules That Prevent Chaos

### Rule 1: Do Not Self-Assign Random Work

Workers should only take tasks that were explicitly dispatched to them.

### Rule 2: Pull Before Acting

Always `git pull` before claiming, reviewing, or reassigning.

### Rule 3: Push Repo Evidence Promptly

Progress that only exists in a local working tree is invisible to the team.

### Rule 4: Do Not Resolve Scope Conflicts In Chat Alone

If scope is wrong, write the incident or update the task card in repo.

### Rule 5: Review State Matters

Only accepted work should reach `done/`.

## Minimal Operator Checklist

If you want the shortest possible operating checklist for a new machine:

1. clone the GitHub repo
2. install Python dependencies
3. run `python scripts/orchestrate.py validate`
4. pull before every work session
5. read the assigned task and execution protocol
6. commit and push every task-state change
7. do not treat chat as the source of truth

## Recommended Next Step

After this guide is in place, the next operational improvement is to give each participating computer:

- a standard agent name
- a standard Git identity
- a standard startup command sheet

That makes replacement, reassignment, and onboarding much easier.
