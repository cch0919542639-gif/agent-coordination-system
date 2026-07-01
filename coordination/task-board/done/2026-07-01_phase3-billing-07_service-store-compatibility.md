---
task_id: phase3-billing-07
phase: phase3-billing-wave2
status: DONE
owner: external-agent-backend-06
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase3-billing-06
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - unrelated repositories
  - framework-wide refactors
  - third-party gateway code
acceptance:
  - Define or adopt a clear billing store contract that the services can depend on
  - Make generation, payment, and balance-query flows work with the durable store implementation
  - Add tests that prove the core service path works against the durable store
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---

# Task Packet

## Objective

Refine the billing service layer so it depends on an explicit store contract and works cleanly with the new durable persistence path.

## Context

First-wave billing services work end-to-end, but they were proven only with the in-memory store. Second-wave persistence should not remain a side path; the main generation, payment, and query services should operate against the same reusable store interface.

## Constraints

Do not turn this into a broad application architecture refactor. Limit the work to the billing domain and only the abstractions needed to make the service layer store-agnostic within that domain.

## Implementation Notes

Follow the simplest contract that supports the already-existing billing operations. Reuse first-wave tests where practical, and add only the extra coverage needed to show durable-store compatibility.

## Validation Steps

Run the billing test suite and add targeted tests that execute the core billing service path using the durable store rather than only the in-memory implementation.

## Escalation Rules

Raise an incident if a clean billing-local store contract cannot be introduced without cross-cutting repository changes, or if the durable store behavior exposes ambiguity in the first-wave billing service assumptions.
