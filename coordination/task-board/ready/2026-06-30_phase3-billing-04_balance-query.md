---
task_id: phase3-billing-04
phase: phase3-billing
status: READY
owner: external-agent-backend-04
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase3-billing-01
  - phase3-billing-03
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - src/reporting/**
  - infra/**
  - src/**
acceptance:
  - Implement a balance query path for invoice state
  - Return correct balance information for defined test scenarios
  - Update docs or validation notes to describe the output shape
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---

# Task Packet

## Objective

Implement a balance query path that exposes invoice state after payment activity.

## Context

This task allows the billing phase to answer a core user question: what is the current balance of an invoice after payments have been recorded.

## Constraints

Do not build broader reporting or admin UI behavior here. Keep the work inside the billing query path.

## Implementation Notes

Keep the output focused on invoice balance and basic state suitable for alpha review.

## Validation Steps

Confirm the balance query returns correct values for at least one unpaid case and one partially or fully paid case.

## Escalation Rules

Raise an incident if the query path depends on unrelated reporting or analytics systems.

