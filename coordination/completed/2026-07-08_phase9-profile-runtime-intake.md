# Phase Intake: phase9-profile-runtime

## Phase ID

phase9-profile-runtime

## Objective

Move the profile layer from documentation-only design into first-pass runtime support so the coordination system can validate profile files, carry explicit profile context through dispatch, and keep operator-facing examples aligned with actual script behavior.

## Entry Criteria

- `phase8-profile-01` is accepted as the profile schema backbone
- `phase8-profile-02` is accepted as the first real profile instance
- `phase8-profile-03` is corrected and accepted so operator examples match current protocol
- Current repo-first coordination flow remains the source of truth

## Exit Criteria

- Profile files can be validated by the coordination validator
- Dispatch flow can carry an explicit profile context without redefining the task lifecycle
- Operator docs/examples are updated to reflect actual supported profile behavior instead of future-state assumptions

## Scope

### In Scope

- `scripts/**`
- `profiles/**`
- `docs/operations/**`
- `coordination/task-board/**`
- `coordination/templates/**`
- `tests/**` for focused script and validator coverage

### Out Of Scope

- application-domain project features
- coordination API runtime integration
- full profile-aware path remapping across every script
- dashboard/UI work
- remote execution infrastructure

## Dependencies

- `profiles/schema-profile-v1.md`
- `profiles/global-defaults-profile.md`
- `profiles/rental-rebuild-profile.md`
- `docs/operations/profile-schema-and-boundary.md`
- `phase8-profile-03`

## Artifact Expectations

- delivery_report (required)
- code_changes
- docs

## Task Packet Decomposition

### Task 1: phase9-profile-runtime-01

- **Objective**: Add validator support for profile files and core schema constraints
- **Priority**: high
- **Dependencies**: `phase8-profile-03`
- **Allowed Scope**: `scripts/**`, `profiles/**`, `docs/operations/**`, `tests/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: validator detects and validates profile files; uniqueness and subset rules are enforced; documentation reflects actual checks

### Task 2: phase9-profile-runtime-02

- **Objective**: Add explicit `--profile` context to dispatch flow without pretending full profile automation already exists
- **Priority**: high
- **Dependencies**: `phase9-profile-runtime-01`
- **Allowed Scope**: `scripts/**`, `docs/operations/**`, `tests/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: dispatch accepts a profile reference, includes profile context in output, and preserves current repo-first lifecycle semantics

### Task 3: phase9-profile-runtime-03

- **Objective**: Refresh operator docs and examples so they align with the implemented runtime support
- **Priority**: medium
- **Dependencies**: `phase9-profile-runtime-01`, `phase9-profile-runtime-02`
- **Allowed Scope**: `docs/operations/**`, `profiles/**`, `coordination/task-board/**`, `coordination/templates/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: operator guidance clearly distinguishes supported behavior from future hooks, and example flows match actual validator/dispatch behavior

## Review and Acceptance

Review this phase in order:

1. validator foundation
2. dispatch profile context
3. operator example refresh

Do not treat full profile path remapping as complete in this phase unless the scripts genuinely implement it and the acceptance criteria are updated first.
