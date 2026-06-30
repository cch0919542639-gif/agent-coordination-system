---
task_id: phase3-billing-01
phase: phase3-billing
status: DONE
owner: external-agent-backend-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - src/payments/**
  - infra/**
acceptance:
  - Create a billing invoice model and persistence path suitable for later billing tasks
  - Support create/load behavior for a test invoice flow
  - Include tests or validation notes for the basic happy path
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Create the billing invoice model and persistence layer that later Phase 3 tasks will build on.

## Context

This is the first engineering task in the billing phase. It establishes the data foundation for invoice generation, payment recording, and balance querying.

## Constraints

Stay inside the billing domain. Do not implement payment gateway integration or unrelated persistence changes.

## Implementation Notes

Prefer simple, explicit invoice state and balance fields that can support later tasks without introducing subscription or tax logic.

## Validation Steps

Confirm the model and persistence path can create and load an invoice for a simple test customer or test fixture.

## Escalation Rules

Raise an incident if the task requires schema or framework changes outside the defined billing scope.
