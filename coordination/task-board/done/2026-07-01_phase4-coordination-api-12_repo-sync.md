---
task_id: phase4-coordination-api-12
phase: phase4-coordination-api-wave2
status: DONE
owner: external-agent-platform-12
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-02
allowed_scope:
  - scripts/repo_sync.py
  - tests/**
  - coordination/sync/**
  - scripts/orchestrate.py
  - coordination/delivery/**
  - coordination/task-board/**/*repo-sync*
forbidden_scope:
  - dashboard UI
  - coordination API endpoints
  - agent CLI client
  - billing domain
acceptance:
  - Read-only projection script scripts/repo_sync.py that reads coordination DB state
  - Project state to coordination/sync/state-snapshot.md with phases, tasks, assignments, incidents, events
  - Support --dry-run flag to preview writes without modifying files
  - Safety guardrail: refuse writes outside coordination/sync/
  - Tests for render functions and sync behavior
  - All existing tests still pass
  - Create/update delivery report
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
---
# Task Packet

## Objective

Build the repo-sync/projection layer that reads coordination database state and renders it into deterministic repo-backed markdown artifacts under `coordination/sync/`.

## Context

The coordination API maintains its state in a SQLite database. To enable repo-first workflows (diffs, reviews, history tracking), the DB state needs to be projected into version-controlled markdown files. This is analogous to Terraform's planfiles or DVC's lock files — human-readable, diffable, auditable.

## Constraints

Keep scope to the sync script and its tests. Do not touch API endpoints, agent CLI, or billing domain. All writes must be contained within `coordination/sync/`.

## Implementation Notes

Use a class-free module with focused render functions. The script should read the DB, render sections, and write a single state snapshot markdown file. Dry-run mode prints what would be written. Safety check prevents writes outside the sync directory.

## Validation Steps

Run the repo_sync tests and the full coordination API test suite. Run the validator.

## Escalation Rules

Raise an incident if the DB schema changes in a way that breaks the projection queries.
