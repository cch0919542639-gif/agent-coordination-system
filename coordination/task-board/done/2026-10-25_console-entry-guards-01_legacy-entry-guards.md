---
task_id: console-entry-guards-01
phase: console-delivery-01
status: DONE
owner: CODEX
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/local_agent_loop.py
  - scripts/worker_poller.py
  - PROGRESS.md
  - coordination/evidence/console-entry-guards-20261025/**
  - coordination/delivery/console-entry-guards-01-delivery-report.md
forbidden_scope:
  - production runtime or credentials
  - main merge or existing PR6/PR9 branch updates
acceptance:
  - Refuse local loop entry and direct worker launch when a Parallel Mode marker exists.
  - Check the actual registered project root before activation inbox or ACK writes.
  - Retest the three original failures and preserve normal marker-absent activation.
  - Record bounded regression logs, native result and exact tested source hashes.
expected_artifacts:
  - delivery_report
  - verification_evidence
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Repair the legacy worker entry guards identified in the PR6 readiness review.

## Context

User directly requested this repair and then authorized commit/push when complete.
Base is92e1248b63dee44a607296b3d63f61207b61f09a. This card records the completed
user-assigned repair at REVIEW; historical DONE tasks are not reopened or accepted.
Branch codex/console-entry-guards-01; independent review remains pending.

## Constraints

Reuse require_serial; preserve source/test scope and all original failure evidence.
No live provider, credentials, schedules, merge or mutation of existing PR branches.

## Implementation Notes

Guard run_loop, launch_worker and the registered-root task-card resolution path.
Activation must reject before durable inbox and acknowledgement side effects.

## Validation Steps

Run parallel_runtime, worker_activation, worker_poller and local_agent_loop suites
with a300second bound; inspect original failing cases and the positive absent-marker
case. Verify source hashes, coordination validator and staged diff.

## Escalation Rules

Stop publication on source/hash/test disagreement; do not hide failures or declare
independent acceptance. Publish only the scoped repair branch authorized by the user.
