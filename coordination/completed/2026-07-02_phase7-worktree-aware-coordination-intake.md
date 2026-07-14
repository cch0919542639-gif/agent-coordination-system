# Phase Intake: phase7-worktree-aware-coordination

## Phase ID

phase7-worktree-aware-coordination

## Objective

Add the first practical layer of worktree-aware execution to the coordination system so dispatched tasks can carry branch and worktree provenance, and the lead agent can isolate worker execution more reliably across parallel agents and multiple computers.

## Entry Criteria

- Phase 6 lead-agent automation wave is accepted and committed
- `orchestrate.py intake` and `orchestrate.py dispatch` exist and validate cleanly
- The current repo-first task lifecycle remains the source of truth

## Exit Criteria

- Task metadata can represent branch and worktree assignment for dispatched work
- Dispatch flow can create or attach worktree-aware metadata without breaking current repo-first operation
- Validator and review artifacts understand the required worktree provenance fields for tasks that opt into this mode
- Operator-facing docs explain how to use worktree-aware dispatch safely

## Scope

### In Scope

- `scripts/**`
- `coordination/task-board/**`
- `coordination/templates/**`
- `coordination/reviews/**`
- `docs/operations/**`
- `tests/**` for focused validation and script coverage

### Out Of Scope

- full UI dashboard work
- SSH remote execution
- mobile orchestration
- non-git execution isolation
- application-domain feature work outside coordination

## Dependencies

- `docs/operations/orca-comparison-and-roadmap.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/worker-assignment-policy.md`
- existing `dispatch_task.py`, `review_task.py`, and validator behavior

## Artifact Expectations

- delivery_report (required)
- code_changes
- docs

## Task Packet Decomposition

### Task 1: phase7-worktree-01

- **Objective**: Add task and template metadata for branch/worktree provenance
- **Priority**: high
- **Dependencies**: none
- **Allowed Scope**: `coordination/templates/**`, `coordination/task-board/**`, `scripts/**`, `docs/operations/**`, `tests/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: task packet conventions define branch/worktree fields; existing repo-first workflow remains valid for tasks that do not use the new fields; validator behavior is documented

### Task 2: phase7-worktree-02

- **Objective**: Extend dispatch flow to support worktree-aware assignment metadata
- **Priority**: high
- **Dependencies**: `phase7-worktree-01`
- **Allowed Scope**: `scripts/**`, `coordination/task-board/**`, `docs/operations/**`, `tests/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: dispatch can assign branch/worktree metadata safely; message output includes provenance when present; existing non-worktree dispatch still works

### Task 3: phase7-worktree-03

- **Objective**: Extend validator, review guidance, and operator docs for worktree-aware execution
- **Priority**: medium
- **Dependencies**: `phase7-worktree-01`, `phase7-worktree-02`
- **Allowed Scope**: `scripts/**`, `docs/operations/**`, `coordination/templates/**`, `coordination/task-board/**`, `tests/**`
- **Forbidden Scope**: `services/coordination_api/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: validator can enforce required worktree provenance when a task opts in; reviewer and operator docs explain the new fields and safe usage; examples are consistent

## Review and Acceptance

Run `python scripts/orchestrate.py validate` after each wave. Review all delivery reports and confirm that worktree-aware metadata improves isolation without weakening the repo-first evidence model. Phase completion requires all three task packets to be accepted.
