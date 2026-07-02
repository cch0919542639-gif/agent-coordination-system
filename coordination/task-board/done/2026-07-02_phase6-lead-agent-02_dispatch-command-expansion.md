---
task_id: phase6-lead-agent-02
phase: phase6-lead-agent-automation
status: DONE
owner: external-agent-platform-15
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase6-lead-agent-01
allowed_scope:
  - scripts/**
  - docs/operations/**
  - coordination/task-board/**
  - coordination/templates/**
  - tests/** if a lightweight script test is added
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Expand `orchestrate.py dispatch` into a more lead-agent-friendly dispatch flow
  - Support output of a ready-to-send dispatch message using repo-backed context
  - Support reviewer override and owner confirmation without weakening current safety checks
  - Document how the dispatch command fits the new lead-agent protocol and worker assignment policy
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Upgrade the dispatch flow so the lead agent can assign a task and immediately get a standard dispatch payload that can be pasted to a worker agent without manually rewriting the task context.

## Context

The current `scripts/dispatch_task.py` only updates owner and reviewer fields. The repo already includes dispatch message guidance in `docs/operations/external-agent-dispatch-message-templates.md`, but the command does not yet help generate a concrete message or reflect the new lead-agent orchestration model.

## Constraints

Do not build a chat system or external delivery transport. Focus on repo-backed dispatch preparation: task lookup, owner/reviewer update, and dispatch message generation. Keep behavior deterministic and CLI-friendly.

## Implementation Notes

The command may print a dispatch block to stdout, write an optional file, or do both. It should reuse task metadata rather than duplicate business logic in multiple places. Keep the first version compatible with the existing task lifecycle and validator.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Demonstrate dispatch on a ready task and show that the output includes task ID, task file, required protocol doc, and blocked-path instructions.

## Escalation Rules

Raise an incident if the command needs a new policy input that is not yet defined in repo docs, or if dispatch-message generation would require hidden state outside the task card and current protocol files.
