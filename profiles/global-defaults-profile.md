---
profile_name: global-defaults
schema_version: "1.0"
description: "Explicit representation of the coordination system's built-in global defaults."
project_identifier: core-coordination-engine
active: true
last_updated: "2026-07-08"
task_format:
  allowed_statuses:
    - READY
    - IN_PROGRESS
    - REVIEW
    - DONE
    - BLOCKED
    - NEEDS_FIX
    - REASSIGNED
    - CANCELLED
  allowed_execution_modes:
    - REPO_FIRST
    - WORKTREE
  required_front_matter:
    - task_id
    - phase
    - status
    - owner
    - reviewer
    - priority
    - dependencies
    - allowed_scope
    - forbidden_scope
    - acceptance
    - expected_artifacts
  optional_front_matter:
    - execution_mode
    - branch
    - worktree_path
    - machine_id
  required_sections:
    - "## Objective"
    - "## Context"
    - "## Constraints"
    - "## Implementation Notes"
    - "## Validation Steps"
    - "## Escalation Rules"
role_mapping:
  owner_naming: "default"
  reviewer_naming: "default"
artifact_mapping:
  coordination_structure:
    task_board: "coordination/task-board/"
    progress: "coordination/progress/"
    incidents: "coordination/incidents/"
    delivery: "coordination/delivery/"
    reviews: "coordination/reviews/"
    templates: "coordination/templates/"
  naming_conventions:
    task_card: "<YYYY-MM-DD>_<task-id>_<short-slug>.md"
    progress_file: "<agent-name>.md"
    delivery_report: "<task-id>-delivery-report.md"
    review_report: "review-<task-id>.md"
branch_pr_policy:
  branch_prefix_format: "{type}/{task_id}-{short_slug}"
  allowed_branch_types:
    - docs
    - feat
    - fix
    - chore
    - test
    - refactor
  pr_title_format: "[{TASK_ID}] Short outcome statement"
  pr_description_required: true
  pr_readiness_states:
    - "Draft PR"
    - "Ready for review"
    - "Needs fix"
    - "Accepted"
  one_branch_per_task: true
worktree_policy:
  enabled: false
  default_path_prefix: "worktrees/"
  machine_affinity_required: false
  machine_id_field: "machine_id"
---

# Global Defaults Profile

This file is an explicit reference profile that documents the current global defaults. It is not loaded by any runtime — it exists so that project profiles can be compared against a single source of truth.

## What This Covers

Every field in this profile mirrors the hardcoded defaults in the coordination engine:

- `scripts/validate_coordination_files.py` — defines `VALID_TASK_STATUSES`, `VALID_EXECUTION_MODES`, `TASK_REQUIRED_KEYS`, `TASK_OPTIONAL_KEYS`, `TASK_REQUIRED_SECTIONS`
- `coordination/templates/task-packet.md` — defines the default front matter structure and sections
- `docs/operations/github-branch-and-pr-conventions.md` — defines branch naming and PR conventions
- `docs/operations/worker-assignment-policy.md` — defines agent categories and default owner/reviewer patterns

## How To Use This

1. When creating a new project profile, copy the relevant sections from this file and override only the fields that differ.
2. When adding a new feature to the core engine, update this file to reflect the new default.
3. When reviewing a project profile, diff it against this file to see exactly what changed.

## Non-Overridable Fields

The following aspects of the coordination system are part of the core engine and are not overridable through profiles:

- `VERSION` structure and validation rules in `validate_coordination_files.py`
- The dispatch, review, incident, and submission protocols in `docs/operations/`
- The agent execution lifecycle (task lifecycle states as a flow, not just valid values)
- The orchestrator's role and authority as defined in `lead-agent-orchestration-protocol.md`
