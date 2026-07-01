# Phase Intake: Coordination API MVP Wave 2

## Phase ID

phase4-coordination-api-wave2

## Objective

Close the first real agent execution loop in the coordination API so an assigned agent can report progress, raise blockers, attach delivery evidence, submit for review, and receive a structured review decision without manual state relaying.

## Entry Criteria

List the conditions that must be true before the phase can begin:

- Wave 1 is accepted and pushed to the repo
- `assign`, `poll`, and `claim` endpoints exist and are covered by tests
- `docs/specs/coordination-api-v1.md` remains the contract baseline
- Repo-first delivery artifacts remain the evidence source of truth

## Exit Criteria

List the measurable conditions that define phase completion:

- Progress update endpoint exists and records structured task progress
- Incident endpoint exists and records blockers plus blocked-task events
- Artifact registration and submit-for-review endpoints exist
- Review endpoint exists and maps valid decisions to task-state transitions
- Wave 2 delivery reports are accepted and filed for all opened tasks

## Scope

### In Scope

- `services/coordination_api/**`
- `tests/coordination_api/**`
- `docs/specs/coordination-api-v1.md`
- `docs/operations/**` when API usage or review guidance changes
- `coordination/**` for task, progress, delivery, incident, and review artifacts

### Out Of Scope

- heartbeat and lease expiry recovery
- repo-sync worker
- dashboard UI
- notification or webhook layer
- full external agent CLI

## Dependencies

List external dependencies, backbone references, or prerequisite phases:

- `docs/specs/coordination-api-v1.md`
- `docs/roadmap/coordination-system-implementation-plan.md`
- `coordination/completed/2026-07-01_phase4-coordination-api-wave1-intake.md`
- `coordination/task-board/done/2026-07-01_phase4-coordination-api-03_assignment-claim-api.md`

## Artifact Expectations

Define what delivery artifacts every task in this phase must produce:

- delivery_report (required)
- code_changes
- tests or validation notes
- docs if API behavior, examples, or review expectations change

## Task Packet Decomposition

List the candidate task packets that decompose this phase into executable work.

### Task 1: phase4-coordination-api-04

- **Objective**: Implement the progress update endpoint and progress event persistence
- **Priority**: high
- **Dependencies**: `phase4-coordination-api-03`
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/specs/coordination-api-v1.md`, `coordination/**`
- **Forbidden Scope**: dashboard UI, repo-sync worker, unrelated application domains
- **Acceptance Criteria**: `POST /tasks/{taskId}/progress` exists; ownership and task-state checks are enforced; progress updates produce task events; tests cover valid and invalid update paths

### Task 2: phase4-coordination-api-05

- **Objective**: Implement the incident endpoint and blocked-task handling
- **Priority**: high
- **Dependencies**: `phase4-coordination-api-03`
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/specs/coordination-api-v1.md`, `coordination/**`
- **Forbidden Scope**: heartbeat workers, dashboard UI, unrelated domains
- **Acceptance Criteria**: `POST /tasks/{taskId}/incidents` exists; structured incident records are created; blocked-task transitions are validated; tests cover success and invalid ownership or state paths

### Task 3: phase4-coordination-api-06

- **Objective**: Implement artifact registration and submit-for-review endpoints
- **Priority**: high
- **Dependencies**: `phase4-coordination-api-03`
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/specs/coordination-api-v1.md`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: dashboard UI, repo-sync worker, notification layer
- **Acceptance Criteria**: `POST /tasks/{taskId}/artifacts` and `POST /tasks/{taskId}/submit` exist; submission requires minimum evidence; submit transitions to `review`; tests cover success and invalid submission cases

### Task 4: phase4-coordination-api-07

- **Objective**: Implement the review endpoint and decision-driven task-state transitions
- **Priority**: high
- **Dependencies**: `phase4-coordination-api-06`
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/specs/coordination-api-v1.md`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: reassignment API, heartbeat recovery, dashboard UI
- **Acceptance Criteria**: `POST /tasks/{taskId}/review` exists; valid decisions map to valid task states; review events are recorded; tests cover accepted, needs_fix, reassign-style rejection, and invalid-decision paths

## Review and Acceptance

Describe how the orchestrator will validate phase completion:

- run `python scripts/orchestrate.py validate`
- run the coordination API test suite
- inspect event creation, task-state transitions, and ownership rules against `docs/specs/coordination-api-v1.md`
- accept each task individually before opening heartbeat, reassign, or repo-sync work
