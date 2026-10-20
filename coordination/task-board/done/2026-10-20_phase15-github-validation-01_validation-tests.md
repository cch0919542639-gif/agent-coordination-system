---
task_id: phase15-github-validation-01
phase: phase15-github-01
status: DONE
owner: phase15-angeline-worker
reviewer: codex-phase15-github-review
priority: high
dependencies: []
allowed_scope:
  - tests/scripts/test_phase15_github_validation.py
  - coordination/task-board/*/*phase15-github-validation-01*.md
  - coordination/progress/phase15-angeline-worker.md
  - coordination/delivery/phase15-github-validation-01-delivery-report.md
  - coordination/incidents/*phase15-github-validation-01*.md
  - coordination/evidence/phase15-github-01/validation/**
forbidden_scope:
  - Production modules, other worker files, shared DB, private keys, direct peer connections, services and schedules
  - Self acceptance, merge or push without its explicit grant
acceptance:
  - All assigned cases add distinct coverage beyond existing88 tests and preserve source pins.
  - Complete execution evidence and independent review are required before acceptance.
expected_artifacts:
  - report
  - delivery_report
execution_mode: REPO_FIRST
branch: codex/phase15-github-validation-01
machine_id: angeline
---
# Task Packet

## Objective

Add the validation cases specified in coordination/plans/phase15-github-01.md
as an independent test-only contribution on assigned host angeline.

## Context

Read PLAN.md, PROGRESS.md, TASKS.md, the phase15-github-01 plan,
docs/operations/phase15-github-handoff-guide.md and agent-task-execution-protocol.md.
Existing offline input pins are in coordination/evidence/phase15-github-01/source-pins.json.

## Constraints

Released READY by user-approved GitHub publication on2026-10-21.
Claim only after the exact published release/owner assignment is verified. Use
the published worker-base commit and codex/phase15-github-validation-01; no automatic task claiming or peer access.
Zero new model/provider calls or paid services. No production code modification.
Only existing Python/pytest/PyYAML; missing dependencies mean stop, not install.

## Implementation Notes

Implement only this task's cases from the plan. First inspect existing88 tests;
add distinct boundaries or persistence observations, not renamed duplicates.
Use temporary local DBs and synthetic fixtures. Do not depend on the other
worker's unpublished test file. Write only this task's unique evidence/progress.
Move only your own card; canonical shared root progress is lead-owned after integration.

## Validation Steps

Run existing test_offline_inbox.py plus this new test file. Per host: at most
three pytest invocations,180s each,30min active work window. Preserve all failures,
JUnit and execution.json including machine/OS, versions, release/candidate SHA,
file digests, command,UTC start/end,exit code and counts. No private logs or DBs.
Run python scripts/validate_coordination_files.py before submission.

## Escalation Rules

Missing release, wrong source hash, wrong owner, repeated assignment, missing
local tools, test failure, source defect, quota, scope conflict or lost access:
stop and retain evidence. Repair only within declared budget and scope. Local
operator stops local processes; do not obtain remote control. Never self-accept.
