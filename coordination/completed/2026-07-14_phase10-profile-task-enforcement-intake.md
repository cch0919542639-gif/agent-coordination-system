# Phase Intake: phase10-profile-task-enforcement

## Phase ID

phase10-profile-task-enforcement

## Objective

Make an explicitly selected project profile a safe task-level constraint for
validation and dispatch, while preserving the default `coordination/` runtime
and compatibility for existing unprofiled tasks.

## Entry Criteria

- Phase 9 profile validator, dispatch context, and operator documentation are accepted.
- `profiles/schema-profile-v1.md` remains the schema source of truth.
- The default repo-first task lifecycle remains stable.

## Exit Criteria

- One shared profile runtime resolver is used by profile-aware scripts.
- A task can explicitly declare a profile and be validated against its supported constraints.
- Dispatch preflights and records an explicitly chosen profile without relying on `active`.
- Existing tasks with no profile remain valid.
- Validator and focused regression tests pass.

## Scope

### In Scope

- `scripts/**` and focused `tests/**`
- `profiles/**`
- `docs/operations/**`
- coordination evidence and task cards

### Out Of Scope

- profile-aware artifact path remapping
- automatic profile detection or activation from `active`
- automatic branch, worktree, owner, or reviewer population
- profile inheritance, API changes, dashboard work, and application features

## Dependencies

- `docs/operations/profile-task-enforcement-runtime-plan.md`
- `profiles/schema-profile-v1.md`
- Phase 9 delivery reports and completed task cards

## Artifact Expectations

- delivery_report (required)
- code_changes
- focused_tests
- docs when a command contract changes

## Task Packet Decomposition

### Task 1: phase10-profile-enforcement-01

- **Objective**: Centralize profile loading and define an explicit runtime/preflight contract.
- **Priority**: high
- **Dependencies**: Phase 9 accepted
- **Allowed Scope**: `scripts/**`, `tests/**`, `docs/operations/**`, `profiles/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: one shared resolver; dispatch reuses it without output regression; explicit documentation that `active` is not a selector; focused tests.

### Task 2: phase10-profile-enforcement-02

- **Objective**: Add additive validation for task cards that explicitly declare a profile.
- **Priority**: high
- **Dependencies**: `phase10-profile-enforcement-01`
- **Allowed Scope**: `scripts/**`, `tests/**`, `docs/operations/**`, `profiles/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: profile-constrained status/mode and declared extra fields are checked; unprofiled cards remain compatible.

### Task 3: phase10-profile-enforcement-03

- **Objective**: Let dispatch preflight and record an explicit profile selection on a task.
- **Priority**: medium
- **Dependencies**: `phase10-profile-enforcement-01`, `phase10-profile-enforcement-02`
- **Allowed Scope**: `scripts/**`, `tests/**`, `docs/operations/**`, `coordination/templates/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: explicit profile evidence persists on task cards; invalid selections fail safely; no automatic activation or path remapping.

### Task 4: phase10-profile-enforcement-04

- **Objective**: Add end-to-end regression coverage and operator guidance for default versus enforced profile tasks.
- **Priority**: medium
- **Dependencies**: `phase10-profile-enforcement-02`, `phase10-profile-enforcement-03`
- **Allowed Scope**: `tests/**`, `docs/operations/**`, `profiles/**`, `coordination/templates/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: regression matrix covers default and profiled flows; operators have a safe command sequence; no future-state features are presented as implemented.

## Review and Acceptance

Review tasks in dependency order. Require focused tests plus the full
coordination validator at each code-changing task. Do not begin artifact-path
remapping until Phase 10 is accepted and a separate migration plan is approved.
