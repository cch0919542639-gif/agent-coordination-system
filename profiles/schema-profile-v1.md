# Profile Schema v1

## Overview

This document defines the structure of a project coordination profile. A profile is a YAML-front-matter markdown file that lives under `profiles/<project-name>-profile.md`. It describes how a specific project overrides the global coordination defaults.

## Schema

Every profile file must begin with YAML front matter. The front matter keys are defined below.

### Top-Level Fields

```yaml
---
profile_name: "<string>"               # Required. Unique identifier for this profile.
schema_version: "1.0"                  # Required. Must match the schema version in this document.
description: "<string>"                # Required. One- or two-sentence description of the project and its profile intent.
extends: "<profile_name>" | null       # Optional. Reserved for future inheritance. Must be null in v1.
project_identifier: "<string>"         # Recommended. The repo name, org/project slug, or other stable identifier.
active: true | false                   # Optional. Default false. When true, the profile is considered active by convention.
last_updated: "<YYYY-MM-DD>"           # Recommended. Date of last meaningful change.
---
```

### `task_format`

Controls how task cards are structured for this project.

```yaml
task_format:
  allowed_statuses:                    # Core-defined set; profile may narrow to a subset (default values below)
    - READY
    - IN_PROGRESS
    - REVIEW
    - DONE
    - BLOCKED
    - NEEDS_FIX
    - REASSIGNED
    - CANCELLED
  allowed_execution_modes:             # Core-defined set; profile may narrow to a subset (default values below)
    - REPO_FIRST
    - WORKTREE
  default_status: READY                # Optional. Which status new tasks in this project should start with.
  default_execution_mode: REPO_FIRST   # Optional. Which execution mode is the project default.
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
```

If a field is omitted, the global default is used. An empty list means no additional constraints beyond the core engine's minimum.

`allowed_statuses` and `allowed_execution_modes` are core-defined sets. A profile may narrow them (select a safe subset), set a `default_*` preference, or express opt-in policy (e.g., requiring `WORKTREE`). A profile must not add values that are not recognized by the engine's validation and dispatch logic.

### `role_mapping`

Defines naming conventions and agent categories for this project.

```yaml
role_mapping:
  owner_naming: "<string>"             # Default: "default" — free-form agent name (external-agent-architecture-01)
  reviewer_naming: "<string>"          # Default: "default" — organization-level role (ORCHESTRATOR) or specific agent
  agent_categories:                    # Optional. Overrides or extends the global agent categories.
    - category: "<string>"             # e.g., "planning", "platform", "docs", "test"
      label: "<string>"                # Human-readable label
      task_shapes:
        - "<string>"                   # e.g., "phase intake", "script automation"
      default_owner_prefix: "<string>" # e.g., "external-agent-architecture-"
```

When omitted, the global default agent categories from `worker-assignment-policy.md` are used.

### `artifact_mapping`

Controls where coordination artifacts are placed and how they are named.

```yaml
artifact_mapping:
  coordination_structure:              # Path overrides relative to repo root
    task_board: "<path>"               # Default: coordination/task-board/
    progress: "<path>"                 # Default: coordination/progress/
    incidents: "<path>"                # Default: coordination/incidents/
    delivery: "<path>"                 # Default: coordination/delivery/
    reviews: "<path>"                  # Default: coordination/reviews/
    templates: "<path>"                # Default: coordination/templates/
  naming_conventions:
    task_card: "<pattern>"             # Default: <YYYY-MM-DD>_<task-id>_<short-slug>.md
    progress_file: "<pattern>"         # Default: <agent-name>.md
    delivery_report: "<pattern>"       # Default: <task-id>-delivery-report.md
    review_report: "<pattern>"         # Default: review-<task-id>.md
```

Path overrides are relative to the repo root. When a field is omitted, the global default path is used.

### `branch_pr_policy`

Controls how branches and pull requests are named and managed for this project.

```yaml
branch_pr_policy:
  branch_prefix_format: "<string>"     # Default: "{type}/{task_id}-{short_slug}"
  allowed_branch_types:
    - "<string>"                       # Default: docs, feat, fix, chore, test, refactor
  pr_title_format: "<string>"          # Default: "[{TASK_ID}] Short outcome statement"
  pr_description_required: true|false  # Default: true
  pr_description_template: "<text>"    # Optional. Default uses the PR convention in github-branch-and-pr-conventions.md
  pr_readiness_states:
    - "<string>"                       # Default: Draft PR, Ready for review, Needs fix, Accepted
  one_branch_per_task: true|false      # Default: true
```

### `worktree_policy` (Optional)

Controls worktree-aware execution for this project.

```yaml
worktree_policy:
  enabled: true|false                  # Default: false
  default_path_prefix: "<path>"        # Default: worktrees/
  machine_affinity_required: true|false # Default: false
  machine_id_field: "<string>"         # Default: machine_id
  branch_format: "<string>"            # Default: "agent/{owner}/{task_id}-{short_slug}"
```

When `enabled` is false (or omitted), the worktree policy block is ignored and the global defaults for execution mode apply.

## Complete Example

```yaml
---
profile_name: rental-rebuild
schema_version: "1.0"
description: "Rental rebuild project — custom task format roles, separate artifact paths, and worktree-aware by default."
project_identifier: internal/rental-rebuild
active: false
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
  default_status: READY
  default_execution_mode: WORKTREE
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
    - sprint
    - epic
  required_sections:
    - "## Objective"
    - "## Context"
    - "## Constraints"
    - "## Implementation Notes"
    - "## Validation Steps"
    - "## Escalation Rules"
role_mapping:
  owner_naming: "agent-type-task"
  reviewer_naming: "project-role"
artifact_mapping:
  coordination_structure:
    task_board: "rental-rebuild/coordination/task-board/"
    progress: "rental-rebuild/coordination/progress/"
    incidents: "rental-rebuild/coordination/incidents/"
    delivery: "rental-rebuild/coordination/delivery/"
    reviews: "rental-rebuild/coordination/reviews/"
    templates: "rental-rebuild/coordination/templates/"
branch_pr_policy:
  branch_prefix_format: "{type}/{project_slug}/{task_id}-{short_slug}"
  allowed_branch_types:
    - docs
    - feat
    - fix
    - chore
    - test
    - refactor
  pr_title_format: "[{PROJECT}] [{TASK_ID}] Short outcome statement"
  pr_description_required: true
  one_branch_per_task: true
worktree_policy:
  enabled: true
  default_path_prefix: "worktrees/rental-rebuild/"
  machine_affinity_required: true
---
```

## Validation Rules

A profile file must satisfy these constraints to be considered valid:

1. `profile_name` must be non-empty and unique across `profiles/`.
2. `schema_version` must be `"1.0"` for this schema version.
3. `description` must be non-empty.
4. `extends` must be `null` in v1 (reserved for future use).
5. All list-type fields must be either omitted or contain valid strings.
6. Path overrides in `artifact_mapping` must not escape the repo root (no `../`).
7. The profile must not redefine fields that are reserved for the core engine (see boundary doc).
8. `allowed_statuses` and `allowed_execution_modes` must be subsets of the core-defined sets (`VALID_TASK_STATUSES` and `VALID_EXECUTION_MODES` in `validate_coordination_files.py`). Profiles must not introduce values the engine does not recognize.

## Extensibility

This schema is designed to be extended in three ways:

1. **New top-level blocks** — future versions may add blocks like `notification_policy` or `review_routing`.
2. **New fields within existing blocks** — additive fields do not break backward compatibility.
3. **Custom front matter** — projects may add project-specific front matter keys (prefixed with `_` or in the profile-specific section).

Breaking changes require a schema version bump and migration of all active profiles.
