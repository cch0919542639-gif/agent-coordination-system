# Agent Coordination System

This repository contains a repo-first coordination system for multi-agent software delivery.

The purpose of this project is to make agent collaboration repeatable, reviewable, and recoverable through GitHub and repository files instead of fragile chat-only coordination.

## What This Repo Provides

- task-board workflow for `ready / in_progress / review / done / blocked`
- standardized task, progress, incident, and review files
- operating protocols for orchestrator-led delegation
- rollout guidance for the first live GitHub collaboration phase
- validation tooling for coordination file quality

## Repository Layout

```text
coordination/
  task-board/
  progress/
  incidents/
  completed/
  reviews/
  templates/

docs/
  architecture/
  operations/
  specs/

scripts/
```

## Start Here

If you are new to this repo, read these in order:

1. [AGENTS.md](D:\codex work\AGENTS.md)
2. [PLAN.md](D:\codex work\PLAN.md)
3. [PROGRESS.md](D:\codex work\PROGRESS.md)
4. [TASKS.md](D:\codex work\TASKS.md)
5. [docs/operations/universal-work-context-workflow.md](D:\codex work\docs\operations\universal-work-context-workflow.md)
6. [docs/operations/agent-task-execution-protocol.md](D:\codex work\docs\operations\agent-task-execution-protocol.md)

## First Live Pilot

The initial live pilot tasks are currently staged in:

- [coordination/task-board/ready](D:\codex work\coordination\task-board\ready)

The first-wave dispatch instructions are here:

- [docs/operations/first-wave-dispatch-pack.md](D:\codex work\docs\operations\first-wave-dispatch-pack.md)

## Validation

Run this before opening a phase or reviewing a batch of new coordination files:

```bash
python scripts/validate_coordination_files.py
```

## Working Model

This repo follows a strict orchestrator-led model:

- the orchestrator defines the backbone and task packets
- agents execute only assigned work
- blockers become incidents
- completion requires repo evidence
- review decides whether work is accepted, fixed, or reassigned

## Current Status

This repository currently contains:

- the first version of the coordination architecture
- operating protocols and rollout guides
- standard templates and sample files
- the first wave of live pilot task cards

## Controlled Hermes and OpenCode Workers

Both runtimes use the same repo-first, owner-strict handoff: an assigned task
creates a durable delivery, the worker claims at most one matching task, writes
delivery evidence, and submits it to `review/`. Neither runtime may accept,
merge, commit, push, select unassigned work, or handle a second task in one
turn.

### Hermes

Hermes uses the local `coordination-worker` skill and its own cron job. Its
supervised pilot completed one assigned handoff. The Hermes cron remains paused
until an operator explicitly resumes it. See
[Hermes operator guide](docs/operations/hermes-controlled-worker-pilot.md).

### OpenCode

OpenCode uses `opencode/deepseek-v4-flash-free` through the controlled launcher:

```powershell
.\integrations\opencode-coordination-worker\run-controlled-worker.ps1 -Run
```

The launcher isolates runtime state with `XDG_CONFIG_HOME` and processes only
`opencode-coordination-pilot` deliveries. Windows Task Scheduler is the native
wake-up mechanism, using the `OpenCode Controlled Worker` task at a 10-minute
cadence. It is currently **Disabled** after a successful supervised test; enable
it only when scheduled polling is desired. See
[OpenCode operator guide](docs/operations/opencode-controlled-worker-pilot.md).

Before any model run, ensure the selected task is explicitly authorized for
external model processing. Completion still requires an orchestrator review.
