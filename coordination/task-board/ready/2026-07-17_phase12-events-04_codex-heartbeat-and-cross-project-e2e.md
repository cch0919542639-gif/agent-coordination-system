---
task_id: phase12-events-04
phase: phase12-event-driven-orchestration
status: READY
owner: external-agent-quality-03
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase12-events-01
  - phase12-events-02
  - phase12-events-03
allowed_scope:
  - tests/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - scripts/**
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add end-to-end regression coverage for two isolated project repositories through monitor, event ledger, routing, worker poller, acknowledgement, and no-duplicate repeat poll behavior.
  - Cover review-submitted, ready-assigned, incident-opened, unregistered worker, malformed registry/policy, fetch failure, acknowledgement retry, and project isolation recovery paths.
  - Prove no part of the tested event flow claims tasks, accepts reviews, modifies task cards, invokes subprocesses/HTTP hooks, launches agents, or pushes commits.
  - Publish a Codex heartbeat operator guide that separates what the automation checks from what still requires reviewer or worker decisions, including low-resource cadence and stop/recovery conditions.
  - Document a first-project onboarding sequence using `agent-usage-collector` as an example without committing its local registry path or runtime state.
expected_artifacts:
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Act as the independent Phase 12 quality gate. Verify the complete multi-project
event path from a remote worker delivery to a safe orchestrator/worker
notification handoff, and document how the orchestrator enables a bounded
Codex heartbeat without claiming autonomous control of third-party agents.

## Context

Read:

- `docs/operations/phase12-event-driven-orchestration-plan.md`
- `docs/operations/project-repository-boundary.md`
- `docs/operations/phase12-monitor-operator-guide.md`
- `scripts/project_registry.py`
- `scripts/remote_ref_monitor.py`
- `scripts/event_ledger.py`
- `scripts/event_routing.py`
- `scripts/worker_poller.py`
- `docs/operations/phase11-operator-runbook.md`

This is a test/documentation task. The current Codex thread's actual heartbeat
is configured only by the orchestrator after the quality gate is accepted.

## Constraints

- Do not modify any runtime script. File an incident if test evidence reveals a
  runtime defect; do not weaken tests or documentation to hide it.
- Use isolated temporary local repositories/remotes. Never poll the real GitHub
  repositories or record a user machine path in committed files.
- Do not attempt to create a Codex automation, scheduled task, external process,
  webhook, or agent launch. Document the operator-managed setup only.
- Documentation must explicitly say that heartbeat wakes the orchestrator for
  evidence inspection; review acceptance, scope decisions, and external agent
  execution remain governed by existing policy.

## Implementation Notes

The heartbeat guide should recommend a 10-minute cadence by default and explain
why it has negligible LLM/token cost when no event is pending: it runs bounded
local/Git checks and should return an idle result without broad repo reading.
It must list a 1-minute lower bound only for short supervised debugging, not as
the normal operating mode.

## Validation Steps

1. Add focused cross-project end-to-end tests and run them in isolation.
2. Run `python -m pytest tests/scripts/ -q`.
3. Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.
4. Manually cross-check every heartbeat guide command/claim against current
   scripts and the Phase 12 contracts.

## Escalation Rules

Create an incident and stop if the full flow needs a runtime change, direct
process/agent control, public webhook, credentials in Git, or automatic
lifecycle decision to pass.
