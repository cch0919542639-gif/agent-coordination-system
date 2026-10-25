---
task_id: console-handoff-pilot-prep-01
phase: console-handoff-01
status: DONE
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - console-handoff-main-integration-01
allowed_scope:
  - .gitattributes
  - docs/operations/dual-machine-pilot-20261025/**
  - coordination/evidence/console-handoff-pilot-prep-01/**
  - coordination/delivery/console-handoff-pilot-prep-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - product code and existing release branch modifications
  - actual handoff init sync dispatch receive watch or provider activation
  - credentials permissions schedules and PR9 main merge
acceptance:
  - Prepare exact-version transport-only configurations and a hash-bound READY payload for distinct named peers.
  - Define one queue and explicit remote-write scope with runner null and execution disabled.
  - Validate config/card with the existing implementation without initialization or network mutation.
  - Supply ordered guarded commands and an other-computer preparation prompt.
  - Publish the preparation package separately without advancing PR9 code_ref or creating the pilot queue.
expected_artifacts:
  - delivery_report
  - pilot_package
  - verification_evidence
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Prepare the next real dual-computer transport/intake acceptance stage requested by
the user, without treating general continuation as exact live queue activation.

## Context

PR9 remains draft at1d7b85b on mainc3682d3. The code has passed core241 and handoff48
separate native regressions. This package is documentation/preparation only.

## Constraints

No new runtime wrapper or product logic, external model call, actual peer activation
or remote handoff write. Each host uses its own fresh clone/config/state. Existing
source/release branches remain unchanged; package is on a separate docs branch.

## Implementation Notes

Use angeline coordinator and human-labeled技嘉202509 mapped to gigabyte-202509 receiver.
Both peers list the receiver identity, matching the existing contract. Bind code1d7b85b,
new queue codex/handoff-dual-intake-20261025-01 and one RECEIVE-only payload.
Later runner qualification requires a new task/queue/store, not mutating this config.

## Validation Steps

Verify package digests, PowerShell parsing, existing HandoffService config and card
validation with only local origin reads, no state creation; check remote refs read-only.
Run coordination validator and scope diff. Record activation approval as pending.

## Escalation Rules

Stop if code ref moved, queue exists, template/card disagrees, peer is not a distinct
physical computer, or any requested operation exceeds the approved live scope.
