---
task_id: phase1-live-03
phase: phase1-live-pilot
status: READY
owner: external-agent-docs-02
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - docs/**
  - coordination/**
forbidden_scope:
  - src/**
  - database/**
  - infra/**
acceptance:
  - Create a short reviewer playbook for evaluating incoming agent submissions
  - Include the minimum review checks and review outcome meanings
  - Include a quick triage rule for accept, needs_fix, reassign, and reject
  - Keep all changes inside docs and coordination folders
expected_artifacts:
  - docs
  - delivery_report
---

# Task Packet

## Objective

Create a compact reviewer playbook that helps the orchestrator or reviewer apply the same review logic consistently during the first live phase.

## Context

The first pilot will only work well if review is fast and consistent. This task reduces reviewer drift and makes acceptance decisions easier to repeat.

## Constraints

Do not redefine the entire protocol. Focus on an actionable checklist or playbook that complements the existing review report template.

## Implementation Notes

The playbook should align with the execution protocol and the rollout guide. Keep it practical enough to use during a real review pass.

## Validation Steps

Confirm the final document can be used to answer:

- did the agent stay in scope
- is delivery evidence sufficient
- does the result satisfy acceptance
- what decision should be returned

## Escalation Rules

Raise an incident if review decision criteria conflict with the existing protocol or checklist.
