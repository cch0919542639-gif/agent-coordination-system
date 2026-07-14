# Profile Schema and Boundary

## Purpose

This document defines where the core coordination engine ends and where project-specific policy begins. It enables multi-project capability without rewriting the engine for each project.

## Core Engine vs Profile Override

The table below lists every behavior in the current coordination system, identifies whether it is a global default (core) or a profile overridable (project-specific policy), and explains the boundary.

| # | Behavior | Current Location | Classification | Explanation |
|---|----------|-----------------|---------------|-------------|
| 1 | Task status set (READY, IN_PROGRESS, etc.) | `validate_coordination_files.py:16-25` | **Core** (set definition) / **Profile** (narrow/select only) | The core defines the complete set of allowed statuses. A profile may narrow to a subset or configure a default, but must not add values the engine does not recognize. |
| 2 | Execution mode set (REPO_FIRST, WORKTREE) | `validate_coordination_files.py:27` | **Core** (set definition) / **Profile** (narrow/select only) | The core defines the complete set of allowed execution modes. A profile may narrow to a subset, configure a default, or require a specific mode, but must not add values without matching engine changes. |
| 3 | Required front matter keys | `validate_coordination_files.py:28-39` | **Core** (required) / **Profile** (additional) | A profile may require extra front matter keys (e.g., `sprint`, `epic`) but cannot remove core-required keys. |
| 4 | Optional front matter keys | `validate_coordination_files.py:40-46` | **Core** / **Profile** | A profile may add optional keys but the core always allows the standard optional set. |
| 5 | Required task sections | `validate_coordination_files.py:47-55` | **Core** (required) / **Profile** (additional) | A profile may require extra sections but cannot remove core-required sections. |
| 6 | Task lifecycle flow (ready -> in_progress -> review -> done) | `agent-task-execution-protocol.md:61-74` | **Core** — not overridable | The lifecycle is the engine's state machine. Profiles cannot redefine the flow. |
| 7 | Agent execution loop (8 steps) | `agent-task-execution-protocol.md:91-178` | **Core** — not overridable | The execution loop is the engine's operating contract. Profiles cannot change it. |
| 8 | Owner naming convention | Task packet `owner` field | **Default** / **Profile** | Global default is free-form (e.g., `external-agent-architecture-01`). A profile may define a convention (e.g., `agent-type-task-id`). |
| 9 | Reviewer naming convention | Task packet `reviewer` field | **Default** / **Profile** | Global default uses `ORCHESTRATOR` or specific agent names. A profile may define project-specific review roles. |
| 10 | Agent categories (planning, platform, docs, test) | `worker-assignment-policy.md:53-103` | **Default** / **Profile** | A profile may add project-specific agent categories or override category descriptions. |
| 11 | Coordination directory paths | Built into scripts via `COORDINATION_DIR` | **Default** / **Profile** | A profile may override artifact paths per project (e.g., `rental-rebuild/coordination/`). |
| 12 | Task card filename convention | Implicit in task-board | **Default** / **Profile** | A profile may define a different naming pattern. |
| 13 | Delivery report naming | `coordination_common.py:148-149` | **Default** / **Profile** | A profile may change the naming pattern or location. |
| 14 | Review report naming | `coordination_common.py:157-158` | **Default** / **Profile** | A profile may change the naming pattern or location. |
| 15 | Progress file naming | `coordination_common.py:144-145` | **Default** / **Profile** | A profile may change the naming pattern or location. |
| 16 | Branch naming convention | `github-branch-and-pr-conventions.md:28-40` | **Default** / **Profile** | A profile may define project-specific branch prefixes. |
| 17 | Allowed branch types (docs, feat, fix, etc.) | `github-branch-and-pr-conventions.md:43-52` | **Default** / **Profile** | A profile may restrict or extend allowed branch types. |
| 18 | PR title format | `github-branch-and-pr-conventions.md:72-77` | **Default** / **Profile** | A profile may define project-specific PR title formats. |
| 19 | PR description structure | `github-branch-and-pr-conventions.md:87-109` | **Default** / **Profile** | A profile may require additional sections or a different template. |
| 20 | PR readiness states | `github-branch-and-pr-conventions.md:127-137` | **Default** / **Profile** | A profile may add project-specific readiness states. |
| 21 | Worktree policy (enabled/disabled, path prefix) | `worktree-aware-task-metadata.md` | **Default** / **Profile** | A profile may enable worktree mode and define conventions. |
| 22 | Machine affinity | `worktree-aware-task-metadata.md:56-66` | **Default** / **Profile** | A profile may require machine pinning. |
| 23 | Dispatch message format | `dispatch_task.py` | **Core** — not overridable | The dispatch message is part of the orchestration protocol. |
| 24 | Review outcomes (accepted, needs_fix, reassign, rejected) | `agent-task-execution-protocol.md:268-281` | **Core** — not overridable | Review decisions are part of the engine's control flow. |
| 25 | Validator rules and logic | `validate_coordination_files.py` | **Core** — not overridable | The validation engine's logic is part of the core. Profiles add data, not rules. |
| 26 | Orchestrator role and authority | `lead-agent-orchestration-protocol.md:20-34` | **Core** — not overridable | The orchestrator's role is a system invariant. |

## Boundary Summary

### Core (not overridable)

These are part of the coordination engine's invariant rules:

1. Task lifecycle state machine (ready -> in_progress -> review -> done + exception states)
2. Agent execution loop (8 steps)
3. Dispatch message format and content
4. Review outcome decisions (accepted, needs_fix, reassign, rejected)
5. Validator fundamental logic and data structures
6. Orchestrator role and authority
7. The concept of task packets with front matter + body sections

### Global Defaults (overridable by profile)

These are the built-in defaults that a profile may override:

1. Task status subset and default (narrow from core-defined set)
2. Execution mode subset, default, or opt-in requirement (select from core-defined set)
3. Required front matter keys (profile may add additional)
4. Optional front matter keys (profile may add additional)
5. Required task sections (profile may add additional)
6. Owner naming convention
7. Reviewer naming convention
8. Agent categories and task-shape mappings
9. Coordination directory paths
10. Artifact naming conventions (task cards, progress files, delivery/review reports)
11. Branch naming convention and allowed types
12. PR title format, description template, and readiness states
13. Worktree policy (enabled, path prefix, machine affinity)

### Design Rule

If a behavior is a mechanical rule that the coordination engine enforces globally (e.g., "a task must have an owner"), it is core. If a behavior is a convention that makes sense differently per project (e.g., "what prefix should branches use"), it is a profile override.

When in doubt, put it in the global default and let profiles override explicitly.

## How Task Format Fits The Schema

Each task card has two parts: YAML front matter and markdown body sections.

**Front matter** — the profile schema maps as follows:

| Front Matter Field | Schema Block | Overridable? |
|---|---|---|
| `task_id` | `task_format.required_front_matter` | Core-required |
| `phase` | `task_format.required_front_matter` | Core-required |
| `status` | `task_format.allowed_statuses` | Profile narrowable (subset of core-defined set) |
| `owner` | `role_mapping.owner_naming` | Profile overridable |
| `reviewer` | `role_mapping.reviewer_naming` | Profile overridable |
| `priority` | `task_format.required_front_matter` | Core-required |
| `dependencies` | `task_format.required_front_matter` | Core-required |
| `allowed_scope` | `task_format.required_front_matter` | Core-required |
| `forbidden_scope` | `task_format.required_front_matter` | Core-required |
| `acceptance` | `task_format.required_front_matter` | Core-required |
| `expected_artifacts` | `task_format.required_front_matter` | Core-required |
| `execution_mode` | `task_format.allowed_execution_modes` | Profile narrowable (subset of core-defined set) |
| `branch` | `branch_pr_policy` | Profile overridable |
| `worktree_path` | `worktree_policy` | Profile overridable |
| `machine_id` | `worktree_policy.machine_id_field` | Profile overridable |

**Body sections** — the profile schema maps as follows:

| Section | Schema Block | Overridable? |
|---|---|---|
| `## Objective` | `task_format.required_sections` | Core-required |
| `## Context` | `task_format.required_sections` | Core-required |
| `## Constraints` | `task_format.required_sections` | Core-required |
| `## Implementation Notes` | `task_format.required_sections` | Core-required |
| `## Validation Steps` | `task_format.required_sections` | Core-required |
| `## Escalation Rules` | `task_format.required_sections` | Core-required |

## How Role Mapping Fits The Schema

Roles are represented in two places: the task card front matter (`owner`, `reviewer`) and the agent assignment policy (`worker-assignment-policy.md`).

The schema's `role_mapping` block defines:

- `owner_naming` — the convention for owner identifiers (free-form name, agent-type-task-id pattern, project-role pattern)
- `reviewer_naming` — the convention for reviewer identifiers (ORCHESTRATOR, project-specific role, named agent)
- `agent_categories` — the set of recognized agent types and the task shapes each type typically handles

Global defaults use free-form naming for owners and `ORCHESTRATOR` for reviewers. A project profile might enforce a structured naming convention (e.g., `rental-rebuild/backend/phase8-task-01`) and define project-specific agent categories.

## How Artifact Mapping Fits The Schema

Artifacts include task cards, progress reports, incident reports, delivery reports, review reports, and templates. Their locations and naming conventions are currently hardcoded in `coordination_common.py`.

The schema's `artifact_mapping` block lets a profile override:

- **Directory paths** — where each artifact type lives (e.g., `rental-rebuild/coordination/` instead of `coordination/`)
- **Naming conventions** — how individual files are named (e.g., `<sprint>-<task_id>-delivery.md` instead of `<task_id>-delivery-report.md`)

The core engine still controls the validation of artifact content. Profiles only control location and naming.

## How Branch/PR Policy Fits The Schema

Branch and PR conventions are currently documented in `github-branch-and-pr-conventions.md`. The rules are advisory — the validator does not enforce branch names or PR formats.

The schema's `branch_pr_policy` block lets a profile define:

- `branch_prefix_format` — template for branch names (e.g., `{type}/{project}/{task_id}-{slug}`)
- `allowed_branch_types` — which type prefixes are valid (e.g., `docs`, `feat`, `fix`)
- `pr_title_format` — template for PR titles (e.g., `[{PROJECT}] [{TASK_ID}] Summary`)
- `pr_description_required` — whether PR descriptions must follow the template
- `pr_readiness_states` — the allowed PR lifecycle states

Global defaults enforce a simple scheme. A project with stricter conventions (e.g., requiring JIRA ticket references in branch names) would express those through a profile.

## How Worktree Policy Fits The Schema

Worktree awareness is an opt-in feature documented in `worktree-aware-task-metadata.md`. The current design treats worktree fields as optional metadata.

The schema's `worktree_policy` block lets a profile:

- Enable worktree mode by default for all tasks
- Set the default worktree path prefix
- Require machine affinity for all tasks
- Define a branch naming format compatible with worktree isolation

Global defaults leave worktree mode disabled. A project that wants all tasks to use isolated worktrees would enable it through a profile.

## Comparison: Global Defaults vs Rental-Rebuild Profile (Illustrative)

| Dimension | Global Default | Rental-Rebuild Profile (planned) |
|---|---|---|
| Owner naming | `<agent-name>` | `<project>/<role>/<task-id>` |
| Reviewer naming | `ORCHESTRATOR` or `<agent-name>` | `rental-rebuild-reviewer` |
| Coordination paths | `coordination/` | `rental-rebuild/coordination/` |
| Branch prefix | `{type}/{task_id}-{slug}` | `{type}/rental-rebuild/{task_id}-{slug}` |
| PR title | `[{TASK_ID}] Summary` | `[RENTAL] [{TASK_ID}] Summary` |
| Worktree mode | disabled | enabled |
| Machine affinity | optional | required |

## Migration Path

This profile layer is designed to be additive. No existing coordination artifacts need to change:

1. All current task cards remain valid — they follow global defaults.
2. Project profiles are new files in `profiles/` — no existing files are touched.
3. The global defaults profile is documentation-only — it does not change engine behavior.
4. Future automation (dispatch flag, validator integration) is optional follow-up work.

## Future Hooks

The following hooks are identified. Status is noted per hook:

| # | Hook | Status | Notes |
|---|------|--------|-------|
| 1 | **`--profile` flag** on dispatch | ✅ Implemented (phase9-runtime-02) | Loads profile by name/path, includes context in dispatch message. Informational only — does not auto-set fields or remap paths. |
| 2 | **Profile-aware validator** that validates task cards against the active profile's constraints | ❌ Not implemented | Profile files themselves are validated. Task card conformity to profile rules is a future hook. |
| 3 | **Profile inheritance** for multi-project setups | ❌ Not implemented | `extends` field is reserved (must be null in v1). |
| 4 | **Auto-detection** of active profile from repo name or configuration | ❌ Not implemented | `active: true/false` has no script effect; operator must pass `--profile` explicitly. |
| 5 | **Template overrides** per profile with different default task packet sections | ❌ Not implemented | Templates remain global. |

See `coordination/delivery/phase8-profile-01-delivery-report.md` and `coordination/delivery/phase9-profile-runtime-02-delivery-report.md` for implementation details.

## References

- `profiles/schema-profile-v1.md` — schema definition
- `profiles/global-defaults-profile.md` — global defaults as a profile
- `profiles/README.md` — profile layer overview
- `docs/operations/worker-assignment-policy.md` — agent categories
- `docs/operations/github-branch-and-pr-conventions.md` — branch/PR conventions
- `docs/operations/worktree-aware-task-metadata.md` — worktree metadata
