---
profile_name: rental-rebuild
schema_version: "1.0"
description: "Rental rebuild project — markdown-oriented task conventions, project-specific specialist roles, separate artifact paths under rental-rebuild/coordination/, and worktree-aware by default."
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
  allowed_execution_modes:
    - REPO_FIRST
    - WORKTREE
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
  owner_naming: "<project>/<role>/<task-id>"
  reviewer_naming: "rental-rebuild-reviewer"
  agent_categories:
    - category: "content-writer"
      label: "Markdown Content Writer"
      task_shapes:
        - "documentation drafts"
        - "specification writing"
        - "release notes"
      default_owner_prefix: "rr-content-"
    - category: "markdown-engineer"
      label: "Markdown Pipeline Engineer"
      task_shapes:
        - "markdown tooling and validation"
        - "template design"
        - "rendering and export"
      default_owner_prefix: "rr-md-"
    - category: "specialist-reviewer"
      label: "Rental Rebuild Reviewer"
      task_shapes:
        - "content review"
        - "technical review"
        - "cross-artifact integration review"
      default_owner_prefix: "rr-review-"
artifact_mapping:
  coordination_structure:
    task_board: "rental-rebuild/coordination/task-board/"
    progress: "rental-rebuild/coordination/progress/"
    incidents: "rental-rebuild/coordination/incidents/"
    delivery: "rental-rebuild/coordination/delivery/"
    reviews: "rental-rebuild/coordination/reviews/"
    templates: "rental-rebuild/coordination/templates/"
  naming_conventions:
    task_card: "<YYYY-MM-DD>_<task-id>_<short-slug>.md"
    progress_file: "<agent-name>.md"
    delivery_report: "<task-id>-delivery-report.md"
    review_report: "review-<task-id>.md"
branch_pr_policy:
  branch_prefix_format: "{type}/rental-rebuild/{task_id}-{short_slug}"
  allowed_branch_types:
    - docs
    - feat
    - fix
    - chore
    - test
    - refactor
  pr_title_format: "[RENTAL] [{TASK_ID}] Short outcome statement"
  pr_description_required: true
  pr_readiness_states:
    - "Draft PR"
    - "Ready for review"
    - "Needs fix"
    - "Accepted"
  one_branch_per_task: true
worktree_policy:
  enabled: true
  default_path_prefix: "worktrees/rental-rebuild/"
  machine_affinity_required: true
  machine_id_field: "machine_id"
  branch_format: "agent/{owner}/rental-rebuild/{task_id}-{short_slug}"
---

# Rental Rebuild Profile

## Purpose

This profile expresses how the rental-rebuild project customizes the core coordination engine. It does not modify global defaults — it declares project-specific conventions over them.

## Differences From Global Defaults

| Dimension | Global Default | Rental-Rebuild Override |
|---|---|---|
| Owner naming | Free-form agent name (`external-agent-*`) | `<project>/<role>/<task-id>` (e.g., `rental-rebuild/content-writer/phase8-task-01`) |
| Reviewer naming | `ORCHESTRATOR` or agent name | `rental-rebuild-reviewer` |
| Agent categories | planning, platform, docs, test | content-writer, markdown-engineer, specialist-reviewer |
| Coordination paths | `coordination/` | `rental-rebuild/coordination/` |
| Default execution mode | `REPO_FIRST` | `WORKTREE` |
| Branch prefix | `{type}/{task_id}-{slug}` | `{type}/rental-rebuild/{task_id}-{slug}` |
| PR title | `[{TASK_ID}] Summary` | `[RENTAL] [{TASK_ID}] Summary` |
| Worktree mode | disabled | enabled |
| Machine affinity | optional | required |
| Optional front matter | core set only | adds `sprint`, `epic` |

## Unresolved Gaps

The following rental-rebuild needs span from "partially supported" to "not yet implemented":

| # | Need | Status | Notes |
|---|------|--------|-------|
| 1 | **Additional artifact directories** (`completed/`, `handoffs/`) | ❌ Not yet supported | Schema covers only `task_board`, `progress`, `incidents`, `delivery`, `reviews`, `templates`. Resolution requires extending the schema block or adding a project-specific extras field. |
| 2 | **Profile-aware dispatch** | ✅ Supported (informational) | `--profile rental-rebuild` loads profile context into the dispatch message. The profile's naming conventions, defaults, and artifact paths are shown in the message body with explicit "Supported by scripts" / "Manual follow-up" separation. The operator must still set `--owner`, `--reviewer`, `--execution-mode`, `--branch`, `--worktree-path`, and `--machine-id` explicitly — the profile does NOT auto-populate fields. |
| 3 | **Profile-aware validation of task cards** | ❌ Not yet supported | The validator does not check that a task card in `rental-rebuild/coordination/task-board/` conforms to this profile's optional front matter or naming conventions. The profile file itself IS validated (schema rules, path safety, subset checks). |
| 4 | **Artifact path remapping** | ❌ Not yet supported | `artifact_mapping` values appear in the dispatch message context but are NOT used for actual file placement. All coordination files remain under `coordination/`. |
| 5 | **Profile-aware review routing** | ❌ Not yet supported | `review_task.py` applies standard decisions uniformly. Profile-specific reviewer naming is a manual convention. |

## Related References

- `profiles/schema-profile-v1.md` — schema definition
- `profiles/global-defaults-profile.md` — global defaults
- `docs/operations/profile-schema-and-boundary.md` — core-vs-profile boundary
