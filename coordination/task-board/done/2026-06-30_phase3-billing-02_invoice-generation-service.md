---
task_id: phase3-billing-02
phase: phase3-billing
status: DONE
owner: external-agent-backend-02
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
  - src/payments/**
  - infra/**
acceptance:
  - Implement an invoice generation service or endpoint using the billing model
  - Return a valid invoice payload for a simple test customer scenario
  - Include tests or validation notes for one success path and one failure path
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---

# Task Packet

## Objective

Implement invoice generation using the billing model created in the first billing task.

## Context

This task makes the billing phase visible as an actual feature by generating a concrete invoice payload for downstream use.

## Constraints

Do not include payment recording or third-party gateway logic in this task.

## Implementation Notes

Keep the generation path focused on a minimal alpha workflow: one customer, one invoice, one simple payload shape.

## Validation Steps

Confirm that invoice generation succeeds for a valid input and returns a clear failure for an invalid or incomplete input.

## Escalation Rules

Raise an incident if invoice generation requires changes outside the billing model or API documentation scope defined here.
