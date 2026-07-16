---
task_id: phase12-events-02
phase: phase12-event-driven-orchestration
status: READY
owner: external-agent-platform-27
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase12-events-01
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
  - Add an explicit project-scoped routing policy that maps monitor event types to approved orchestrator or registered-worker destinations.
  - Convert eligible events into compact, deterministic notification payloads containing no raw task body, prompt, credential, or machine path.
  - Persist delivery attempts, pending state, acknowledgement, retry schedule, and terminal failure state in ignored local runtime data with idempotent behavior.
  - Reject unknown projects, unregistered destinations, malformed policies, and unsupported event/destination combinations without invoking a process or mutating task lifecycle.
  - Add focused tests for routing, project isolation, duplicate events, acknowledgement, retry/backoff, invalid configuration, no process invocation, and no task-card mutation.
  - Document policy schema, safe payload fields, registration flow, recovery actions, and the boundary before actual Codex/worker wake-up integration.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Build the Phase 12 event-routing layer. It consumes the monitor's local event
ledger and produces safe, idempotent notification requests for the owning
project's orchestrator or registered worker runner. It must not directly launch
an agent, call a webhook, or alter task state.

## Context

Read:

- `docs/operations/phase12-event-driven-orchestration-plan.md`
- `docs/operations/project-repository-boundary.md`
- `docs/operations/phase12-monitor-operator-guide.md`
- `scripts/project_registry.py`
- `scripts/event_ledger.py`
- `scripts/remote_ref_monitor.py`
- `scripts/orchestrate.py`

Events are project-scoped evidence. Routing chooses the next safe destination;
actual Codex heartbeat and worker-poller execution are later tasks.

## Constraints

- Read project registry/policy only from explicit local configuration. Do not
  use a profile's `active` field, infer destinations, or inspect credentials.
- Payloads may include project ID, task ID, event type, ref/commit identity,
  owner/reviewer identifiers, and artifact paths relative to the project root.
  They must not include task body, prompt text, absolute paths, credentials, or
  raw event content.
- Runtime routing/delivery state is Git-ignored, atomically written, and never
  changes task cards, branches, reviews, assignments, or manifests.
- Do not invoke subprocesses, HTTP requests, desktop notifications, Codex APIs,
  or external agent runners. Later adapters consume the payloads.

## Implementation Notes

Extend, do not duplicate, the event-ledger persistence model. Keep policy
parsing, eligibility decisions, payload construction, acknowledgement, and
retry state independently testable. Retry/backoff must be deterministic from
stored attempt metadata; an invocation of this task's command only prepares
requests and records their state.

## Validation Steps

1. Use temporary project registries, policies, and event ledgers in tests.
2. Verify events from one project cannot route to another project's destination.
3. Verify duplicate route passes create no duplicate pending payload.
4. Verify all task-card bytes are unchanged and no subprocess/HTTP hook is
   called.
5. Run focused tests, `python -m pytest tests/scripts/ -q`, and
   `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.

## Escalation Rules

Create an incident and stop if safe routing requires an external process/API,
if policy configuration would need tracked machine paths, or if acknowledgement
semantics require changing task-card lifecycle state.
