---
task_id: phase3-billing-11
phase: phase3-billing-wave3
status: DONE
owner: external-agent-architecture-01
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase3-billing-07
  - phase3-billing-08
allowed_scope:
  - src/billing/**
  - tests/billing/**
  - docs/api/billing.md
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - auth framework integration
  - UI work
  - unrelated account systems
acceptance:
  - Define an explicit customer access-boundary contract for billing reads
  - Add billing-local interfaces or helper paths that express customer-scoped read behavior
  - Add tests and documentation describing what billing enforces versus what higher layers must enforce
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Turn customer isolation from an implicit query convention into an explicit billing-local boundary contract for future integration layers.

## Context

Wave 2 proved that customer-specific invoice listings behave correctly in tests, but the billing module still does not clearly separate "data available in storage" from "data a caller is permitted to read". This task creates the billing-local boundary language that later auth and API layers can build on.

## Constraints

Do not integrate a real auth system. Keep the work inside billing-local contracts, helper paths, tests, and documentation.

## Implementation Notes

A good result may introduce a customer-scoped query helper or boundary-oriented read interface, plus documentation that explains where billing enforcement stops and where outer layers must still apply identity and authorization.

## Validation Steps

Run the billing test suite and add focused tests showing intended customer-scoped read behavior and non-goals of the billing layer.

## Escalation Rules

Raise an incident if a useful boundary contract cannot be expressed without introducing broader auth or account-system dependencies outside the billing module.
