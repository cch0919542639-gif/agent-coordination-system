# Coordination API v1

## Purpose

This document defines the first API surface for the coordination control plane.

The API is designed to support:

- orchestrator assignment
- agent claim and progress reporting
- blocker escalation
- artifact submission
- structured review

This API should mirror the repo-first workflow already established in markdown files.

## Design Principles

1. The control plane manages operational state.
2. The repo remains the evidence trail for delivery artifacts.
3. Every important state change should create an event record.
4. Agents should be simple clients: poll, claim, execute, report, submit.

## Core Entities

- `phase`
- `task`
- `assignment`
- `task_event`
- `artifact`
- `incident`
- `review`
- `agent`

## Authentication

MVP recommendation:

- API key per agent
- API key per orchestrator or reviewer client

Each request should identify:

- `actor_type`
- `actor_id`

## Status Enums

### Task Status

- `draft`
- `ready`
- `assigned`
- `claimed`
- `in_progress`
- `blocked`
- `review`
- `needs_fix`
- `accepted`
- `done`
- `reassigned`
- `cancelled`

### Phase Status

- `planning`
- `frozen`
- `active`
- `reviewing`
- `completed`
- `rolled_back`

### Review Decision

- `accepted`
- `needs_fix`
- `reassign`
- `rejected`

### Incident Severity

- `low`
- `medium`
- `high`

## API Endpoints

## 1. Create Phase

`POST /projects/{projectId}/phases`

Purpose:

- create a new project phase

Request body:

```json
{
  "name": "phase2-billing",
  "objective": "Implement billing create, generate, and batch flows",
  "status": "planning",
  "entry_criteria": [
    "phase1 accepted"
  ],
  "exit_criteria": [
    "billing task packets accepted"
  ],
  "frozen_spec_ref": "docs/specs/phase2-billing.md"
}
```

## 2. Create Task

`POST /phases/{phaseId}/tasks`

Purpose:

- create a task packet record

Request body:

```json
{
  "title": "Billing generate API",
  "objective": "Implement billing generate flow",
  "description": "Build the generate endpoint using the phase backbone",
  "priority": "high",
  "allowed_scope": [
    "src/billing/**",
    "tests/billing/**"
  ],
  "forbidden_scope": [
    "database/migrations/**"
  ],
  "dependencies": [
    "phase2-billing-create-01"
  ],
  "acceptance_criteria": [
    "returns valid invoice payload",
    "includes tests for success and failure paths"
  ],
  "expected_artifacts": [
    "code_changes",
    "test_summary",
    "delivery_report"
  ]
}
```

## 3. Assign Task

`POST /tasks/{taskId}/assign`

Purpose:

- assign a task to an execution agent

Request body:

```json
{
  "agent_id": "agent-backend-01",
  "assignment_reason": "Best fit for billing backend implementation"
}
```

Behavior:

- task status moves to `assigned`
- assignment event is recorded

## 4. Poll Assigned Work

`GET /tasks?agent_id={agentId}&status=assigned`

Purpose:

- let an agent discover work assigned to itself

## 5. Claim Task

`POST /tasks/{taskId}/claim`

Purpose:

- confirm the agent has taken responsibility for execution

Request body:

```json
{
  "agent_id": "agent-backend-01"
}
```

Behavior:

- validates assignment ownership
- creates a claim lease
- task status moves to `claimed` or `in_progress`
- claim event is recorded

## 6. Heartbeat

`POST /tasks/{taskId}/heartbeat`

Purpose:

- extend the claim lease during active execution

Request body:

```json
{
  "agent_id": "agent-backend-01",
  "status": "in_progress"
}
```

## 7. Progress Update

`POST /tasks/{taskId}/progress`

Purpose:

- record a checkpoint update

Request body:

```json
{
  "agent_id": "agent-backend-01",
  "current_step": "Implementing batch retry logic",
  "changed_files": [
    "src/billing/generate.ts",
    "tests/billing/generate.test.ts"
  ],
  "blocker_status": "none",
  "next_step": "Run billing test suite"
}
```

Behavior:

- appends a progress event
- may update task status to `in_progress`

## 8. Open Incident

`POST /tasks/{taskId}/incidents`

Purpose:

- raise a structured blocker

Request body:

```json
{
  "agent_id": "agent-backend-01",
  "severity": "medium",
  "category": "scope_conflict",
  "summary": "Required migration is outside allowed scope",
  "details": "Generate flow depends on a schema change that the task forbids",
  "proposed_resolution": "Split migration into prerequisite task or expand scope explicitly"
}
```

Behavior:

- incident record is created
- task status may move to `blocked`
- orchestrator notification is triggered

## 9. Attach Artifact

`POST /tasks/{taskId}/artifacts`

Purpose:

- register repo artifacts or related outputs

Request body:

```json
{
  "artifact_type": "repo_file",
  "path_or_url": "coordination/completed/agent-backend-01_phase2-billing-generate-01.md",
  "repo_ref": "feature/phase2-billing-generate",
  "commit_hash": "abc123def456"
}
```

## 10. Submit For Review

`POST /tasks/{taskId}/submit`

Purpose:

- mark work ready for review

Request body:

```json
{
  "agent_id": "agent-backend-01",
  "artifact_ids": [
    "artifact-01",
    "artifact-02"
  ],
  "summary": "Implementation complete with tests added",
  "validation_notes": [
    "unit tests passed locally",
    "manual payload validation completed"
  ],
  "residual_risks": [
    "batch concurrency behavior not load tested"
  ]
}
```

Behavior:

- task status moves to `review`
- submission event is recorded

## 11. Review Task

`POST /tasks/{taskId}/review`

Purpose:

- record structured review decision

Request body:

```json
{
  "reviewer_id": "orchestrator-01",
  "decision": "needs_fix",
  "summary": "Core flow works but retry handling is incomplete",
  "findings": [
    {
      "severity": "medium",
      "title": "Retry path lacks idempotency assertion",
      "detail": "Acceptance requires idempotent retries but no test covers duplicate execution"
    }
  ],
  "required_changes": [
    "Add idempotency test coverage for batch retry"
  ],
  "accepted_artifact_ids": [
    "artifact-01"
  ]
}
```

Behavior:

- review record is created
- task status changes according to decision
- review event is recorded

## 12. Reassign Task

`POST /tasks/{taskId}/reassign`

Purpose:

- move continuation responsibility to another agent

Request body:

```json
{
  "from_agent_id": "agent-backend-01",
  "to_agent_id": "agent-backend-02",
  "reason": "Capability mismatch on retry architecture refinement"
}
```

Behavior:

- previous assignment is closed
- new assignment is created
- task status moves to `assigned`

## 13. Resolve Incident

`POST /incidents/{incidentId}/resolve`

Purpose:

- close an incident after orchestrator action

Request body:

```json
{
  "resolver_id": "orchestrator-01",
  "resolution_summary": "Split migration into prerequisite task and kept original task scope unchanged"
}
```

## Event Model

Every endpoint that changes state should append a `task_event`.

Recommended event types:

- `phase_created`
- `task_created`
- `task_assigned`
- `task_claimed`
- `progress_reported`
- `incident_opened`
- `artifact_attached`
- `submitted_for_review`
- `review_completed`
- `task_reassigned`
- `incident_resolved`
- `task_done`

## Suggested Response Shape

For state-changing endpoints, return:

```json
{
  "ok": true,
  "task_id": "phase2-billing-generate-01",
  "status": "review",
  "event_id": "event-123",
  "updated_at": "2026-06-29T04:00:00Z"
}
```

## Validation Rules

Minimum server-side checks:

1. Only orchestrator or reviewer may mark `accepted` or `done`.
2. Agent may claim only tasks assigned to itself.
3. Submission requires at least one artifact or delivery summary.
4. Review decisions must map to valid task status transitions.
5. Reassign preserves task history and references prior review or incident context.

## MVP Build Order

Recommended implementation order:

1. `POST /tasks/{taskId}/assign`
2. `GET /tasks?agent_id=...&status=assigned`
3. `POST /tasks/{taskId}/claim`
4. `POST /tasks/{taskId}/progress`
5. `POST /tasks/{taskId}/incidents`
6. `POST /tasks/{taskId}/submit`
7. `POST /tasks/{taskId}/review`
8. `POST /tasks/{taskId}/reassign`

This order is enough to support a first real coordination loop before building a richer dashboard.

