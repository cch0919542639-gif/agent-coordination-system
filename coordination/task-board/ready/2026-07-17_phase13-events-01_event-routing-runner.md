---
task_id: phase13-events-01
phase: phase13-event-delivery-runtime
status: READY
owner: external-agent-platform-29
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase12-events-04
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - services/**
  - src/**
  - clients/**
  - profiles/**
  - cloud/infra/**
acceptance:
  - Add one explicit runtime entry point that reads newly recorded monitor events and produces idempotent delivery records according to project routing policy.
  - Integrate the entry point into the documented bounded monitor workflow without adding webhooks, HTTP calls, agent launches, lifecycle mutations, or credentials.
  - Preserve project isolation and route only safe payload fields already defined by event_routing.py.
  - Ensure repeated monitor-and-route runs do not duplicate delivery records or overwrite acknowledgement and retry state.
  - Add focused regression coverage for ready-assigned delivery to a registered worker, review and incident delivery to orchestrator, no-policy and disabled-policy behavior, and no mutation of project task cards.
  - Document the first-project onboarding sequence through worker poll and acknowledgement, correcting any stale CLI examples encountered.
expected_artifacts:
  - routing_runner
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Close the Phase 12 runtime handoff gap: a monitor event is currently recorded in
the event ledger, but it is not automatically transformed into a persisted,
project-scoped delivery notification for the orchestrator or registered worker.

## Context

Read:

- docs/operations/phase12-event-driven-orchestration-plan.md
- docs/operations/phase12-monitor-operator-guide.md
- docs/operations/codex-heartbeat-operator-guide.md
- docs/operations/project-repository-boundary.md
- scripts/remote_ref_monitor.py
- scripts/event_ledger.py
- scripts/event_routing.py
- scripts/worker_poller.py
- coordination/task-board/ready/2026-07-17_phase13-events-01_event-routing-runner.md

The intended flow is:

```text
remote ref monitor -> event ledger -> routing runner -> delivery state -> worker poll / orchestrator wake-up
```

## Constraints

- The runner may write only ignored local monitor/delivery runtime state. It
  must not edit a registered project repository or its task cards.
- Do not perform HTTP calls, webhooks, agent/process launches, task claims,
  review decisions, commits, or pushes.
- Do not store raw task body, prompts, credentials, source code, or absolute
  paths in notifications or delivery records.
- Reuse the existing `event_routing.py` policy, payload, delivery, retry, and
  acknowledgement semantics rather than redesigning them.
- Correct stale documentation discovered within allowed scope; do not silently
  leave an advertised CLI operation unsupported.

## Implementation Notes

- Prefer a small explicit routing command or a monitor subcommand that can be
  run once and produce machine-readable output. It must consume persisted
  ledger events rather than chat messages or raw GitHub API data.
- Preserve existing delivery records by using the current idempotent append and
  update helpers. Acknowledged, retry-pending, and failed records must never be
  reset to pending merely because the source event is observed again.
- The project registry and routing policy remain local Git-ignored operator
  state. Documentation may show placeholders, never a real machine path.

## Validation Steps

1. Run focused routing-runner tests.
2. Run `python -m pytest tests/scripts/ -q`.
3. Run `python scripts/orchestrate.py validate`.
4. Demonstrate one isolated ready-assigned event becomes one worker-visible
   delivery record and remains single after a repeated run.

## Escalation Rules

Create an incident and stop if completing the integration requires a public
service, stored credential, direct control of a third-party agent, automatic
lifecycle decision, or a breaking routing-policy schema change.
