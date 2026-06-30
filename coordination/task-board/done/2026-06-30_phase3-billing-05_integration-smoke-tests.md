---
task_id: phase3-billing-05
phase: phase3-billing
status: DONE
owner: external-agent-test-01
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase3-billing-02
  - phase3-billing-03
  - phase3-billing-04
allowed_scope:
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - src/**
  - infra/**
  - unrelated test suites
acceptance:
  - Add a billing smoke path covering create invoice, record payment, and query balance
  - Document validation notes and known residual gaps
  - Keep test work focused on billing integration behavior
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Create a small integration smoke path that proves the first billing tasks work together coherently.

## Context

This is the stabilization task for the first billing phase wave. It validates that the minimal create -> pay -> query flow behaves consistently.

## Constraints

Do not broaden the work into full end-to-end platform testing. Keep it focused on the billing flow assembled in this phase.

## Implementation Notes

Use the simplest meaningful test path that can confirm the behavior without overbuilding.

## Validation Steps

Confirm the smoke path covers invoice generation, payment recording, and balance query in sequence.

## Escalation Rules

Raise an incident if the smoke path cannot be assembled because upstream billing tasks lack required interfaces or test hooks.
