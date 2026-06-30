---
task_id: phase3-billing-03
phase: phase3-billing
status: READY
owner: external-agent-backend-03
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase3-billing-01
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - src/gateway/**
  - infra/**
  - src/**
acceptance:
  - Implement payment recording against an invoice
  - Update invoice balance or payment state correctly for a simple test case
  - Include tests or validation notes for success and invalid-input behavior
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---

# Task Packet

## Objective

Implement the internal payment recording path for billing invoices.

## Context

This task adds the second major billing behavior needed for the alpha flow: recording a payment and reflecting it in invoice state.

## Constraints

Do not implement third-party payment gateway integration. Treat payment recording as an internal domain update only.

## Implementation Notes

Prefer a narrow internal record/update path that later tasks can query for balance information.

## Validation Steps

Confirm that recording a payment updates invoice state or balance correctly, and invalid input does not silently succeed.

## Escalation Rules

Raise an incident if the task requires non-billing infrastructure or gateway work.

