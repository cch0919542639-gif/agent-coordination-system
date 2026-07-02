---
task_id: phase6-lead-agent-03
phase: phase6-lead-agent-automation
status: DONE
owner: external-agent-docs-05
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase6-lead-agent-01
  - phase6-lead-agent-02
allowed_scope:
  - docs/operations/**
  - scripts/**
  - coordination/templates/**
  - coordination/task-board/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Update operator-facing docs so the lead-agent loop explains intake and dispatch together
  - Ensure script usage examples are consistent across the relevant operations docs
  - Add any lightweight validation or README updates needed so the new commands are discoverable
  - Keep all changes aligned with the lead-agent protocol and worker assignment policy
  - Validator passes cleanly after the change
expected_artifacts:
  - docs
  - code_changes
  - delivery_report
---
# Task Packet

## Objective

Integrate the new intake and dispatch workflow into the operator-facing documentation set so the lead-agent loop is coherent, discoverable, and usable without tribal knowledge.

## Context

This packet closes the first automation wave after the intake and dispatch commands exist. The repo already contains `daily-orchestration-flow.md`, `agent_workflow.md`, onboarding docs, and dispatch templates, but they predate the lead-agent orchestration model being formalized.

## Constraints

Do not redefine the protocol from scratch. Update only the documents and script-facing references needed to make the new commands operationally clear. Avoid unrelated doc cleanup.

## Implementation Notes

Likely touchpoints include `docs/operations/daily-orchestration-flow.md`, `docs/operations/external-agent-dispatch-message-templates.md`, and `scripts/README.md`. If a tiny validation improvement is clearly needed for the new workflow, keep it narrow and evidence-driven.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Manually read the updated docs and confirm the lead-agent path from intake -> dispatch -> worker execution -> review is consistent end to end.

## Escalation Rules

Raise an incident if the new commands land with behavior that contradicts the existing onboarding or execution protocol, or if a broader doc refactor would be required to explain them safely.
