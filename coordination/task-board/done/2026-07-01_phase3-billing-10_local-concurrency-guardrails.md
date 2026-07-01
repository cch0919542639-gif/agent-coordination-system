---
task_id: phase3-billing-10
phase: phase3-billing-wave3
status: DONE
owner: external-agent-backend-08
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase3-billing-09
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - coordination/**
forbidden_scope:
  - distributed infra
  - unrelated queueing systems
  - non-billing global locking
acceptance:
  - Define supported local concurrency behavior for the SQLite billing store
  - Add guarded failure behavior or explicit handling for unsupported contention paths
  - Add tests and documentation that explain the limits clearly
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Clarify and harden the local concurrency story for the durable billing store so write contention does not remain an implicit risk.

## Context

Wave 2 explicitly documented that concurrency is still a gap. Before billing is expanded further, local contention behavior should be intentional rather than accidental.

## Constraints

Do not expand into distributed coordination or platform-wide locking. This task is about local durable-store guardrails only.

## Implementation Notes

A good result may document a supported single-process model, add safe failure behavior for write contention, and add focused tests that prove the contract. The goal is clarity and safety, not over-engineering.

## Validation Steps

Run the billing test suite and add targeted contention or guardrail tests that demonstrate what is supported and how unsupported cases fail or are blocked.

## Escalation Rules

Raise an incident if the desired safety behavior requires infrastructure outside the billing module, or if concurrency assumptions conflict with the current store contract in a way that cannot be resolved locally.
