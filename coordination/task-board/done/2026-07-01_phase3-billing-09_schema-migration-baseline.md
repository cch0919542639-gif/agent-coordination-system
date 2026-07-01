---
task_id: phase3-billing-09
phase: phase3-billing-wave3
status: DONE
owner: external-agent-backend-07
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase3-billing-06
  - phase3-billing-07
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - unrelated app domains
  - gateway code
  - non-billing database layers
acceptance:
  - Add a schema-version and migration baseline for the SQLite billing store
  - Ensure the store open/startup path applies the migration baseline safely
  - Prove versioned reopen behavior preserves readable invoice data
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Introduce the minimum schema-evolution mechanism needed so the durable billing store can change safely over time.

## Context

Wave 2 introduced `SqliteInvoiceStore`, but it still has no explicit schema versioning or migration baseline. That is acceptable for a prototype, but it becomes a real risk as soon as the billing persistence shape needs to evolve.

## Constraints

Keep the implementation inside the billing module. Do not expand into global migration tooling or unrelated persistence layers.

## Implementation Notes

The goal is not to design a large migration framework. A lightweight billing-local version table and startup migration path is enough if it is explicit, testable, and safe for the current store shape.

## Validation Steps

Run the billing test suite and add tests proving the store can recognize or initialize schema versioning and still reopen existing data safely.

## Escalation Rules

Raise an incident if a safe migration baseline cannot be introduced without changing non-billing persistence layers, or if preserving existing durable data requires a broader storage redesign.
