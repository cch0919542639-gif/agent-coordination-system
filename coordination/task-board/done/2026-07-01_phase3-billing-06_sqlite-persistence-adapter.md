---
task_id: phase3-billing-06
phase: phase3-billing-wave2
status: DONE
owner: external-agent-backend-05
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase3-billing-01
  - phase3-billing-05
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - src/payments/**
  - infra/**
  - unrelated app domains
acceptance:
  - Add a durable billing persistence implementation with save/load/delete/list_by_customer/count support
  - Preserve behavioral parity with the current invoice-store model for normal invoice flows
  - Prove persisted invoices survive store re-open or process-like reinitialization
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---

# Task Packet

## Objective

Introduce a durable persistence option for billing so invoices are no longer limited to process-memory storage.

## Context

Phase 3 first wave established the billing domain model and service flow, but `docs/api/billing.md` still lists in-memory persistence as a known residual gap. This task is the second-wave backbone item and should not broaden into unrelated payment-platform work.

## Constraints

Keep the implementation inside the billing module. Do not add gateway logic, UI work, or infrastructure provisioning. Prefer a simple local durable mechanism that fits the current repo and test environment.

## Implementation Notes

A small SQLite-backed store or equivalent local durable adapter is acceptable if it preserves the current store responsibilities. If you need to introduce helper abstractions inside `src/billing/**`, keep them tightly scoped to billing storage.

## Validation Steps

Run the billing test suite and add targeted persistence tests that verify data survives closing and reopening the store. Document the chosen durable mechanism in `docs/api/billing.md`.

## Escalation Rules

Raise an incident if durable storage requires changes outside `src/billing/**`, if the existing invoice serialization shape is too ambiguous to preserve safely, or if the chosen approach introduces platform assumptions the repo cannot support consistently.
