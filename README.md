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

1. [docs/operations/agent-task-execution-protocol.md](D:\codex work\docs\operations\agent-task-execution-protocol.md)
2. [docs/operations/github-collaboration-readiness-checklist.md](D:\codex work\docs\operations\github-collaboration-readiness-checklist.md)
3. [docs/operations/first-live-phase-rollout-guide.md](D:\codex work\docs\operations\first-live-phase-rollout-guide.md)
4. [coordination/README.md](D:\codex work\coordination\README.md)

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

