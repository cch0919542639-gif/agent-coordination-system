---
task_id: phase14-local-01
phase: phase14-same-machine-worker-automation
status: REVIEW
owner: external-agent-platform-30
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase13-events-01
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - services/**
  - src/**
  - clients/**
  - cloud/infra/**
  - profiles/**
acceptance:
  - Add a bounded same-machine worker activation command that consumes only an owner-matching pending delivery and emits one safe local action payload.
  - Keep acknowledgement separate from task claim and execution; no lifecycle mutation may occur before the worker agent acts.
  - Make duplicate activation idempotent and fail closed for missing, empty, mismatched, malformed, acknowledged, retry-pending, or failed records.
  - Add two-worker same-machine tests proving isolation, no duplicate action payload, no task-card mutation, and no subprocess, HTTP, or agent launch.
  - Publish an operator bootstrap guide for one-time worker registration and per-worker heartbeat configuration in Codex and generic local runtimes.
expected_artifacts:
  - activation_command
  - focused_tests
  - bootstrap_guide
  - delivery_report
---
# Task Packet

## Objective

Implement the first code-level bridge for same-machine automatic worker
handoff. A central monitor already routes safe local delivery records. This
task adds a bounded worker activation command that prepares a safe action
payload for a worker's own agent heartbeat without claiming, implementing, or
launching that agent.

## Context

Read:

- docs/operations/phase14-same-machine-worker-automation-plan.md
- docs/operations/phase12-monitor-operator-guide.md
- docs/operations/codex-heartbeat-operator-guide.md
- docs/operations/agent-task-execution-protocol.md
- scripts/event_routing.py
- scripts/worker_poller.py
- scripts/routing_runner.py

## Constraints

- Work only with local Git-ignored runtime state under `coordination/monitor/`.
- Do not launch Codex, MiMo, a shell, a process, or another agent.
- Do not use HTTP, webhooks, GitHub APIs, credentials, or public services.
- Do not claim, move, review, merge, commit, or push any task card.
- A missing or mismatched owner must never produce an action payload.

## Implementation Notes

- Prefer an explicit single-shot CLI suitable for a worker-specific heartbeat.
- Acknowledge only after the activation payload is durably available; keep
  acknowledgement idempotent and independently testable.
- Payload fields must remain limited to the existing safe delivery contract;
  never embed raw task body, prompt text, source code, or absolute paths.
- The bootstrap guide must be truthful: it configures an already-running agent
  session to poll; it does not claim a Python script can universally launch an
  arbitrary LLM agent.

## Validation Steps

1. Run focused activation tests.
2. Run `python -m pytest tests/scripts/ -q`.
3. Run `python scripts/orchestrate.py validate`.
4. Demonstrate two local workers where only the matching owner receives one
   activation payload, and a repeated invocation does not duplicate it.

## Escalation Rules

Create an incident and stop if completion requires a cross-machine service,
credential, direct process control, automatic task lifecycle change, or a
breaking delivery-state schema change.
