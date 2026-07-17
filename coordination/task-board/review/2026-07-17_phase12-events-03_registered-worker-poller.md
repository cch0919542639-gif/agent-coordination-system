---
task_id: phase12-events-03
phase: phase12-event-driven-orchestration
status: REVIEW
owner: external-agent-platform-28
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase12-events-01
  - phase12-events-02
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
  - Add an opt-in worker-side polling command that reads only the registered worker's project-scoped pending ready-assignment notification payloads.
  - Render a standard safe dispatch payload with task ID, relative task-card path, project/ref/commit identity, protocol references, and required start/block/finish rules.
  - Require explicit worker registration and explicit acknowledgement; never automatically claim a task, launch an agent, pull code, create a worktree, or mutate task lifecycle.
  - Provide bounded polling configuration with a safe minimum interval, jitter guidance, and an idle/no-work exit that consumes negligible resources.
  - Add focused tests for registration, worker/project isolation, duplicate/no-work polling, acknowledgement, malformed payloads, no subprocess/network invocation, and no lifecycle mutation.
  - Document setup options for external agents, Codex heartbeat/Task Scheduler style invocation, delivery acknowledgement, unregistration, and manual recovery.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Build the opt-in worker-side poller that completes the repo-based handoff loop.
It reads a local registered worker's safe notification payloads and emits a
ready-to-use dispatch message, but leaves actual agent launch and task claim to
the external runner/agent.

## Context

Read:

- `docs/operations/phase12-event-driven-orchestration-plan.md`
- `docs/operations/project-repository-boundary.md`
- `docs/operations/phase12-monitor-operator-guide.md`
- `scripts/project_registry.py`
- `scripts/event_ledger.py`
- `scripts/event_routing.py`
- `scripts/dispatch_task.py`
- `scripts/orchestrate.py`

The worker poller is an adapter boundary. It must make external agents aware of
their work without claiming that a repository event can force-start a third
party process.

## Constraints

- Read only explicit local worker registration and project routing state. Do
  not infer worker identity from OS username, directory, profile `active`, or
  browser/account data.
- Render only fields already approved in the safe notification payload. Do not
  reconstruct or read raw task-card content to enrich the message.
- Acknowledgement confirms local delivery of a notification, not task claim or
  execution. It must be idempotent and project-scoped.
- Do not launch processes, call HTTP/GitHub/Codex APIs, run Git commands, pull
  repositories, create worktrees, or modify task cards.
- Use local ignored runtime state only; no registration details or machine paths
  are committed to Git.

## Implementation Notes

Reuse routing delivery-state semantics rather than creating a second event
queue. The command should support one bounded poll by default and machine
readable output for a trusted local scheduler. Document scheduler examples as
operator instructions, not code that installs or enables a scheduled task.

## Validation Steps

1. Use temporary registries, worker registrations, and routing-state fixtures.
2. Verify an idle poll exits cleanly without writes beyond an explicit allowed
   acknowledgement.
3. Verify no task-card bytes change and no subprocess/network call occurs.
4. Run focused tests, `python -m pytest tests/scripts/ -q`, and
   `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.

## Escalation Rules

Create an incident and stop if worker delivery requires process control,
credentials, direct Codex API access, or semantics equivalent to automatic task
claim/assignment.
