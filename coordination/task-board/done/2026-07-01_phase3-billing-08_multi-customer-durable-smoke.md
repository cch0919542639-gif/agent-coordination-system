---
task_id: phase3-billing-08
phase: phase3-billing-wave2
status: DONE
owner: external-agent-test-02
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase3-billing-06
  - phase3-billing-07
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - admin UI
  - unrelated reporting
  - infrastructure provisioning
acceptance:
  - Add durable integration coverage for multiple customers and multiple invoices
  - Verify customer-isolation behavior and durable reopen behavior in at least one realistic test path
  - Document known remaining operational limits such as local-only concurrency assumptions
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---

# Task Packet

## Objective

Prove that the second-wave billing baseline behaves coherently when more than one customer and more than one invoice are involved under durable storage.

## Context

First-wave smoke coverage confirmed a single-customer happy path. The next operational risk is whether invoice ownership, listing, and payment behavior remain isolated and understandable once durable storage and multiple customer records are involved.

## Constraints

Keep the task focused on billing-domain integration behavior. Do not expand into full load testing, distributed concurrency handling, or non-billing reporting systems.

## Implementation Notes

Prefer one or two focused integration scenarios over a large matrix of test cases. If the durable store introduces local concurrency caveats, document them instead of guessing at a production-grade locking model.

## Validation Steps

Run the billing test suite and add durable multi-customer scenarios that demonstrate invoice isolation, payment correctness, and expected listing or query behavior after reopening the store.

## Escalation Rules

Raise an incident if upstream durable persistence or service-contract work is insufficient to construct the scenario safely, or if customer isolation requires new behavior not yet defined in the current billing scope.
