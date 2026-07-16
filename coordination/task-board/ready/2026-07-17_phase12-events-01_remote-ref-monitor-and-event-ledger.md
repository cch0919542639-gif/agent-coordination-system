---
task_id: phase12-events-01
phase: phase12-event-driven-orchestration
status: READY
owner: external-agent-platform-26
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add a bounded multi-project remote-ref monitor that uses local Git transport/object inspection to find review-submitted, ready-assigned, and incident-opened task-card evidence on configured project remote branches.
  - Add an ignored, atomic, idempotent event ledger with deterministic IDs containing repository, ref, commit, task ID, event type, detection time, and delivery state.
  - Default to a single poll operation; expose an explicit interval option with a safe minimum and jitter support without a busy loop.
  - Emit structured human and JSON output; report retryable fetch/parse health failures without changing task cards, branches, assignments, or reviews.
  - Add focused tests for duplicate polls, changed commits, malformed task cards, remote fetch failure, lifecycle no-mutation, and branch isolation.
  - Document configuration, state-file privacy, event schema, cadence/resource budget, and recovery procedure.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Build the first Phase 12 component: a low-frequency Git remote-ref monitor and
idempotent local event ledger. It detects repository evidence only; it does not
wake agents, accept reviews, or modify lifecycle state.

## Context

Read:

- `docs/operations/phase12-event-driven-orchestration-plan.md`
- `docs/operations/project-repository-boundary.md`
- `coordination/completed/2026-07-17_phase12-event-driven-orchestration-intake.md`
- `docs/operations/phase11-operator-runbook.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `scripts/orchestrate.py`
- `scripts/coordination_common.py`

The monitor replaces manual report relaying with Git-backed evidence. It must
remain inexpensive: one bounded Git fetch/poll at the configured interval and
no LLM/API calls.

## Constraints

- Use existing Git executable discovery/normal subprocess patterns. Do not
  embed GitHub tokens, call an LLM, or add a network dependency.
- Runtime event state must be ignored by Git and contain no credentials, prompt
  text, source code, or raw unredacted task content.
- Do not mutate task cards, create commits, write review reports, or trigger a
  process/automation. Event delivery is a later task.
- Preserve default repo-first behavior when no monitor configuration exists.
- Use an explicit local-only project registry; do not assume engine task cards
  represent product-project task state.

## Implementation Notes

Follow the existing delegated-subcommand pattern in `scripts/orchestrate.py`.
Keep Git collection, task-card parsing, event identity, and atomic ledger I/O
separate so every part can be tested with isolated temporary remotes. The
monitor should inspect remote refs directly after a bounded fetch rather than
checking out worker branches or relying on GitHub API calls.

## Validation Steps

1. Build temporary isolated repositories/remotes in tests; do not contact the
   real GitHub repository.
2. Verify a second unchanged poll produces zero new events.
3. Verify invalid/missing source evidence produces a health event, not an
   exception or lifecycle mutation.
4. Run focused tests, `python -m pytest tests/scripts/ -q`, and
   `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.

## Escalation Rules

Create an incident and stop if required detection cannot be implemented through
bounded Git operations, if event state would need a repository commit, or if an
agent/process must be invoked to satisfy this task.
