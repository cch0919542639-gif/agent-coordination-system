# Phase Intake: Coordination API MVP Wave 1

## Phase ID

phase4-coordination-api-wave1

## Objective

Build the first runnable slice of the coordination control plane so agents can eventually self-serve assigned work through a shared API instead of relying on manual message relaying.

## Entry Criteria

List the conditions that must be true before the phase can begin:

- Repo-first coordination workflow is stable and validated
- `docs/specs/coordination-api-v1.md` exists and is accepted as the first API contract baseline
- `docs/roadmap/coordination-system-implementation-plan.md` exists and defines the MVP rollout plan
- Phase 3 billing work is complete enough that the repo can support platform work without blocking the billing module

## Exit Criteria

List the measurable conditions that define phase completion:

- A runnable coordination API service skeleton exists
- Core database schema and initial migrations exist for the MVP entities
- Assignment and claim endpoints work end-to-end with ownership and task-state validation
- Wave 1 delivery reports are accepted and filed for all opened tasks

## Scope

### In Scope

- `services/coordination_api/**`
- `tests/coordination_api/**`
- `clients/coordination_agent/**` only if a task explicitly allows it
- `docs/specs/coordination-api-v1.md`
- `docs/roadmap/coordination-system-implementation-plan.md`
- `docs/operations/**` when service usage or rollout notes need documentation
- `coordination/**` for task, progress, delivery, incident, and review artifacts

### Out Of Scope

- dashboard UI
- webhook or push notification system
- repo-sync worker
- full agent CLI
- production deployment automation
- replacing the repo as the delivery-evidence layer

## Dependencies

List external dependencies, backbone references, or prerequisite phases:

- `docs/specs/coordination-api-v1.md`
- `docs/architecture/agent-coordination-system.md`
- `docs/roadmap/coordination-system-implementation-plan.md`
- existing repo-first coordination templates and validator

## Artifact Expectations

Define what delivery artifacts every task in this phase must produce:

- delivery_report (required)
- code_changes
- tests or validation notes
- docs if API behavior, setup, or usage assumptions change

## Task Packet Decomposition

List the candidate task packets that decompose this phase into executable work.

### Task 1: phase4-coordination-api-01

- **Objective**: Scaffold the coordination API service skeleton
- **Priority**: high
- **Dependencies**: none
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/roadmap/coordination-system-implementation-plan.md`, `docs/specs/coordination-api-v1.md`, `coordination/**`
- **Forbidden Scope**: billing domain implementation, dashboard UI, deployment infrastructure
- **Acceptance Criteria**: runnable service skeleton exists; health endpoint exists; config and API-key auth skeleton exist; basic test or startup validation is documented

### Task 2: phase4-coordination-api-02

- **Objective**: Implement the core data model and initial migrations for the MVP control plane
- **Priority**: high
- **Dependencies**: `phase4-coordination-api-01`
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/specs/coordination-api-v1.md`, `coordination/**`
- **Forbidden Scope**: dashboard UI, agent CLI, unrelated application domains
- **Acceptance Criteria**: initial schema exists for agents, tasks, assignments, events, incidents, reviews, and artifacts; migrations run cleanly; tests or validation notes cover schema creation

### Task 3: phase4-coordination-api-03

- **Objective**: Implement assignment and claim APIs with task-state and ownership validation
- **Priority**: high
- **Dependencies**: `phase4-coordination-api-02`
- **Allowed Scope**: `services/coordination_api/**`, `tests/coordination_api/**`, `docs/specs/coordination-api-v1.md`, `docs/operations/**`, `coordination/**`
- **Forbidden Scope**: dashboard UI, notification layer, repo-sync worker
- **Acceptance Criteria**: assign, poll-assigned-work, and claim endpoints exist; ownership rules and valid transitions are enforced; tests cover success and invalid-ownership paths

## Review and Acceptance

Describe how the orchestrator will validate phase completion:

- run `python scripts/orchestrate.py validate`
- review code and test coverage for the service skeleton, schema layer, and assignment/claim loop
- compare each task result against `coordination-api-v1` and the implementation plan
- accept tasks individually before opening progress, incident, submit, and review API tasks
