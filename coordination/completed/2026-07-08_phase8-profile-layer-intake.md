# Phase Intake: phase8-profile-layer

## Phase ID

phase8-profile-layer

## Objective

Introduce a project-profile layer so the coordination system can support project-specific task formats, role mappings, artifact mappings, and branch/PR policy without hardcoding one project's rules into the global core.

## Entry Criteria

- `phase7-worktree-aware-coordination` is substantially defined and `phase7-worktree-03` is ready to close the first worktree-aware wave
- Core coordination artifacts and validator remain repo-first and YAML-capable
- Strategic direction in `coordination/progress/codex.md` and `docs/operations/orca-comparison-and-roadmap.md` is aligned on profile-driven evolution

## Exit Criteria

- A first profile schema is defined for the coordination system
- The boundary between core rules and project-specific rules is documented
- A `rental-rebuild` profile example exists without changing the global defaults
- Operators have concrete examples showing how profile-driven execution differs from default execution

## Scope

### In Scope

- `docs/operations/**`
- `profiles/**`
- `scripts/**`
- `coordination/task-board/**`
- `coordination/templates/**`
- `tests/**` for focused validator/script/profile coverage

### Out Of Scope

- application-domain feature work
- coordination API runtime changes unrelated to profiles
- UI dashboard redesign
- remote execution or infrastructure automation
- forcing all existing projects to migrate immediately

## Dependencies

- `coordination/progress/codex.md`
- `docs/operations/orca-comparison-and-roadmap.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/worker-assignment-policy.md`
- `phase7-worktree-03`

## Artifact Expectations

- delivery_report (required)
- code_changes
- docs

## Task Packet Decomposition

### Task 1: phase8-profile-01

- **Objective**: Define the first profile schema and core-vs-project boundary
- **Priority**: high
- **Dependencies**: `phase7-worktree-03`
- **Allowed Scope**: `docs/operations/**`, `profiles/**`, `scripts/**`, `coordination/templates/**`, `tests/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: profile schema is explicit; global defaults are separated from project policy; validator/script impact is identified even if partially deferred

### Task 2: phase8-profile-02

- **Objective**: Create the first `rental-rebuild` profile instance using the approved schema
- **Priority**: high
- **Dependencies**: `phase8-profile-01`
- **Allowed Scope**: `profiles/**`, `docs/operations/**`, `coordination/templates/**`, `tests/** if needed`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: rental-rebuild rules are expressed as profile data/docs instead of global defaults; role/artifact/task-format mapping is concrete and reviewable

### Task 3: phase8-profile-03

- **Objective**: Create live profile-driven examples and operator sample flows
- **Priority**: medium
- **Dependencies**: `phase7-worktree-03`, `phase8-profile-01`
- **Allowed Scope**: `docs/operations/**`, `profiles/**`, `coordination/task-board/**`, `coordination/templates/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: operators can see default-vs-profile examples; examples align with the schema; live usage guidance is concrete enough for dispatch and review

## Review and Acceptance

Review this phase in order:

1. accept the schema
2. accept the first real profile instance
3. accept the examples and operator flow

`phase8-profile-02` and `phase8-profile-03` may run in parallel only after `phase8-profile-01` is accepted or at least backbone-frozen with no unresolved schema ambiguity.
