# Phase Intake: phase11-orchestration-runtime-safety

## Phase ID

phase11-orchestration-runtime-safety

## Objective

Add safe, reproducible runtime preflight and run-evidence capabilities to the
lead-agent workflow so cross-machine and external-agent dispatch fails early
with actionable diagnostics.

## Entry Criteria

- Phase 10 profile enforcement is accepted.
- `scripts/orchestrate.py` is the unified script entrypoint.
- The repo-first task lifecycle and coordination validator pass on `main`.

## Exit Criteria

- An operator can run a read-only diagnosis before dispatch and see exact
  failures for repository, runtime, task, and explicit profile prerequisites.
- A dependency-aware wave can be proposed without changing task ownership.
- A dispatched wave has immutable run evidence.
- Worktree preparation is explicit, preflighted, and regression-tested.

## Scope

### In Scope

- `scripts/**` and focused `tests/scripts/**`
- `docs/operations/**`
- `coordination/**` task, progress, review, and delivery evidence

### Out Of Scope

- automatic agent launch, claim, review, merge, or deployment
- API/database changes and dashboard work
- profile path remapping, inheritance, or automatic activation
- modification of application source under `src/**` or `services/**`

## Dependencies

- `docs/operations/phase11-orchestration-runtime-safety-plan.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/agent-task-execution-protocol.md`
- Phase 10 accepted task cards and review reports

## Artifact Expectations

- delivery_report (required)
- code_changes
- focused_tests
- operator_docs for every new command contract

## Task Packet Decomposition

### Task 1: phase11-runtime-safety-01

- **Objective**: Add read-only `orchestrate doctor` preflight diagnostics.
- **Priority**: high
- **Dependencies**: Phase 10 accepted
- **Allowed Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: deterministic diagnostic result; no mutation; actionable failure messages; focused tests and docs.

### Task 2: phase11-runtime-safety-02

- **Objective**: Propose dependency-aware execution waves without lifecycle mutation.
- **Priority**: high
- **Dependencies**: `phase11-runtime-safety-01`
- **Allowed Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: detects satisfied and unsatisfied dependencies; proposes waves deterministically; produces no task mutations.

### Task 3: phase11-runtime-safety-03

- **Objective**: Record immutable evidence for an operator-approved dispatch wave.
- **Priority**: medium
- **Dependencies**: `phase11-runtime-safety-01`, `phase11-runtime-safety-02`
- **Allowed Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: records revision, tasks, owner/reviewer, profile, and command context; validates schema; does not claim tasks.

### Task 4: phase11-runtime-safety-04

- **Objective**: Add opt-in worktree preflight/provisioning from approved run evidence.
- **Priority**: medium
- **Dependencies**: `phase11-runtime-safety-03`
- **Allowed Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: dry-run support; collision and machine-affinity checks; no implicit remote or lifecycle mutation.

### Task 5: phase11-runtime-safety-05

- **Objective**: Verify the full cross-machine safety flow and document recovery actions.
- **Priority**: medium
- **Dependencies**: `phase11-runtime-safety-01`, `phase11-runtime-safety-02`, `phase11-runtime-safety-03`, `phase11-runtime-safety-04`
- **Allowed Scope**: `tests/**`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: `scripts/**`, `services/**`, `src/**`, `database/**`, `cloud/infra/**`
- **Acceptance Criteria**: regression matrix covers wrong repo, missing runtime, invalid task/profile, wave evidence, and worktree refusal; operator guide is truthful.

## Review and Acceptance

Accept in dependency order. Every code task requires focused tests, the full
coordination validator, and an inspection that a diagnostic or planning command
did not mutate task cards or assignments unexpectedly.
