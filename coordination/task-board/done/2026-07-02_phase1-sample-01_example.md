---
task_id: phase1-sample-01
phase: phase1-foundation
status: DONE
owner: external-agent-live-02
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - docs/**
  - coordination/**
forbidden_scope:
  - src/**
  - database/**
acceptance:
  - Create a sample task card using the standard template
  - Keep all changes inside documentation and coordination folders
  - Include validation notes in the final delivery report
expected_artifacts:
  - task_card
  - delivery_report
---
# Task Packet

## Objective

Create a sample task packet and demonstrate the expected repo-backed coordination flow.

## Context

This task exists as a reference example for future agents joining the project.

## Constraints

Do not modify application source code.

## Implementation Notes

Use the standard templates in `coordination/templates/`.

## Validation Steps

Confirm the task card is valid markdown and follows the required front matter fields.

## Escalation Rules

Raise an incident if the required coordination template is missing or contradictory.

