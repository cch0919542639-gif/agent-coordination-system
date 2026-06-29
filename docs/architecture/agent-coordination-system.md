# Agent Coordination System Architecture

## 1. Purpose

This document defines a repeatable multi-agent collaboration system for software delivery.

The goal is not just to show tasks on a board. The goal is to let a lead orchestrator decompose work, assign task packets to execution agents, collect structured progress and incidents, review results, reassign blocked work, and move phase by phase until a project is complete.

This design follows the direction already discussed:

- single orchestrator as dispatcher and final reviewer
- task packets with strict scope and acceptance rules
- repo-backed artifacts and recovery
- agents do not self-promote or self-advance phase gates
- blocked work is escalated instead of silently drifting

## 2. Core Design Decision

The system should be built as a **coordination control plane**, not just a kanban UI.

The previous `localhost:8080/kanban` approach likely failed because it visualized tasks without enforcing:

- assignment ownership
- claim locks
- artifact linkage
- incident escalation
- review outcomes
- phase gate control
- repo synchronization

The new system should treat the board UI as a view layer only. The real system should be:

1. an orchestration workflow
2. a task state machine
3. an event log
4. a repo-integrated artifact trail
5. a structured review and reassign loop

## 3. High-Level Architecture

The recommended architecture has three layers.

### 3.1 Layer A: Control Plane

This is the system of record for operational state.

Responsibilities:

- store tasks, assignments, incidents, reviews, and phase status
- expose task claim and reporting APIs
- enforce valid state transitions
- record who changed what and when
- drive notifications and polling responses

Suggested components:

- API service
- relational database
- event table or append-only event stream
- background worker for timeout detection, reminders, and stuck-task escalation

### 3.2 Layer B: Delivery Plane

This is where real work happens.

Responsibilities:

- code changes
- spec updates
- reports
- test outputs
- PRs / branches / commits

Primary medium:

- Git repository

This keeps the system recoverable. If the UI disappears or an agent crashes, the repo still contains the delivery artifacts.

### 3.3 Layer C: Interaction Plane

This is how humans and agents observe and interact with the system.

Examples:

- web dashboard
- kanban view
- CLI
- agent polling client
- Slack / Discord / email notifications

Important rule:

The interaction plane must never become the source of truth. It reads and writes through the control plane.

## 4. Role Model

### 4.1 Orchestrator

The orchestrator is the only authority that can:

- create phase goals
- freeze specifications
- split work into task packets
- assign or reassign owners
- approve or reject delivery
- open the next phase

This can be a human, a lead agent, or a hybrid human-plus-agent workflow.

### 4.2 Execution Agent

Execution agents do implementation work under constrained instructions.

They may:

- claim an assigned task
- update progress
- report incidents
- attach commits, reports, and artifacts
- mark work ready for review

They may not:

- change project phase
- self-assign random tasks unless explicitly allowed
- mark final acceptance
- bypass review outcomes

### 4.3 Reviewer

Reviewer can be the orchestrator or a dedicated review agent.

Reviewer performs:

- scope compliance check
- acceptance check
- regression check
- artifact completeness check
- decision: accept, needs_fix, reassign, blocked, withdrawn

## 5. System Principles

### 5.1 Single Dispatcher

Agents should not guess when to take work. Work begins when the orchestrator assigns it.

### 5.2 Explicit Task Packets

Every task must include:

- objective
- allowed files or areas
- forbidden changes
- dependencies
- acceptance criteria
- expected outputs
- escalation rules

### 5.3 Repo-Backed Delivery

A task is not complete unless repo artifacts exist.

Minimum delivery should include at least one of:

- commit or branch reference
- changed files
- report file
- test result
- review note

### 5.4 Event-Sourced Traceability

All important actions should produce an event:

- task_created
- assigned
- claimed
- progress_reported
- incident_opened
- artifact_attached
- submitted_for_review
- review_completed
- accepted
- reassign_requested
- blocked

### 5.5 Recoverability

Any agent or human should be able to reconstruct status after a crash by reading:

- control plane state
- repo artifacts
- event log

### 5.6 Phase Gate Discipline

The project should move phase by phase. A new phase opens only after required tasks from the current phase pass review or are explicitly waived.

## 6. Recommended Workflow

### 6.1 Phase Initialization

The orchestrator defines:

- phase name
- phase objective
- freeze boundaries
- delivery target
- review gate
- exit criteria

Output:

- phase record
- backbone/spec package
- task packet drafts

### 6.2 Task Packet Generation

The orchestrator decomposes the phase into task packets.

Each packet should be small enough that one agent can finish it with minimal ambiguity, but large enough to produce a meaningful artifact.

### 6.3 Assignment

The orchestrator assigns the task to a specific agent profile.

Examples of agent profiles:

- backend generator
- UI repair agent
- testing agent
- documentation agent
- regression reviewer

### 6.4 Claim

Assigned agent claims task through the control plane.

On claim:

- state moves from `ready` to `claimed`
- ownership lock is recorded
- lease or heartbeat timer starts

### 6.5 Execution

Agent works in branch / worktree / isolated context and periodically reports:

- current step
- changed files
- blocker status
- confidence level
- next checkpoint

### 6.6 Incident Escalation

If blocked, the agent opens an incident instead of continuing blindly.

Incident should capture:

- what was attempted
- exact blocker
- likely root cause
- whether the problem is spec, environment, dependency, or capability
- recommended next action

### 6.7 Submission

When done, the agent submits:

- artifact paths
- commit hash or branch
- changed files
- verification steps
- test results
- residual risks
- follow-up recommendations

State moves to `review`.

### 6.8 Review

Reviewer validates:

- scope compliance
- acceptance criteria
- correctness
- no forbidden changes
- proof of validation

Review outcome:

- `accepted`
- `needs_fix`
- `reassign`
- `blocked`
- `rejected`

### 6.9 Integration

Accepted tasks are integrated into the phase summary.

The orchestrator then decides:

- open more packets in same phase
- patch backbone/spec
- close phase
- open next phase

## 7. Task State Machine

Recommended task states:

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

Suggested transition rules:

- `draft -> ready`
- `ready -> assigned`
- `assigned -> claimed`
- `claimed -> in_progress`
- `in_progress -> review`
- `in_progress -> blocked`
- `review -> needs_fix`
- `review -> accepted`
- `needs_fix -> assigned`
- `blocked -> assigned`
- `accepted -> done`
- any non-terminal state -> cancelled by orchestrator

Important rule:

Only orchestrator or reviewer can finalize `accepted`, `done`, `reassigned`, or `cancelled`.

## 8. Phase State Machine

Recommended phase states:

- `planning`
- `frozen`
- `active`
- `reviewing`
- `completed`
- `rolled_back`

Rules:

- only one active implementation phase at a time unless parallel phases are intentionally enabled
- phase exits only when required task packets are accepted or explicitly waived
- incidents that affect the backbone can force the phase back into `planning` or `frozen`

## 9. Data Model

The following is a practical minimum schema.

### 9.1 `phases`

- `id`
- `project_id`
- `name`
- `objective`
- `status`
- `entry_criteria`
- `exit_criteria`
- `frozen_spec_ref`
- `created_by`
- `created_at`
- `closed_at`

### 9.2 `tasks`

- `id`
- `phase_id`
- `title`
- `objective`
- `description`
- `status`
- `priority`
- `owner_agent_id`
- `reviewer_agent_id`
- `allowed_scope`
- `forbidden_scope`
- `dependencies`
- `acceptance_criteria`
- `expected_artifacts`
- `reassign_count`
- `created_at`
- `updated_at`

### 9.3 `task_assignments`

- `id`
- `task_id`
- `agent_id`
- `assigned_by`
- `assignment_reason`
- `lease_expires_at`
- `claimed_at`
- `released_at`

### 9.4 `task_events`

- `id`
- `task_id`
- `event_type`
- `actor_type`
- `actor_id`
- `payload_json`
- `created_at`

This table is critical. It becomes the audit trail and replay source.

### 9.5 `artifacts`

- `id`
- `task_id`
- `artifact_type`
- `path_or_url`
- `repo_ref`
- `commit_hash`
- `checksum`
- `created_by`
- `created_at`

### 9.6 `incidents`

- `id`
- `task_id`
- `agent_id`
- `severity`
- `category`
- `summary`
- `details`
- `proposed_resolution`
- `status`
- `opened_at`
- `resolved_at`

### 9.7 `reviews`

- `id`
- `task_id`
- `reviewer_id`
- `decision`
- `findings_json`
- `required_changes`
- `accepted_artifacts_json`
- `created_at`

### 9.8 `agents`

- `id`
- `name`
- `agent_type`
- `capabilities_json`
- `limitations_json`
- `status`
- `default_poll_interval_sec`
- `concurrency_limit`

## 10. API Design

This is the minimum useful API set.

### 10.1 Task APIs

- `POST /projects/{projectId}/phases`
- `POST /phases/{phaseId}/tasks`
- `GET /tasks/{taskId}`
- `GET /tasks?status=ready&agent_id=...`
- `POST /tasks/{taskId}/assign`
- `POST /tasks/{taskId}/claim`
- `POST /tasks/{taskId}/release`
- `POST /tasks/{taskId}/submit`
- `POST /tasks/{taskId}/reassign`

### 10.2 Progress APIs

- `POST /tasks/{taskId}/progress`
- `POST /tasks/{taskId}/heartbeat`
- `GET /tasks/{taskId}/events`

### 10.3 Incident APIs

- `POST /tasks/{taskId}/incidents`
- `POST /incidents/{incidentId}/resolve`
- `POST /incidents/{incidentId}/escalate`

### 10.4 Review APIs

- `POST /tasks/{taskId}/review`
- `POST /reviews/{reviewId}/accept`
- `POST /reviews/{reviewId}/needs-fix`
- `POST /reviews/{reviewId}/reassign`

### 10.5 Artifact APIs

- `POST /tasks/{taskId}/artifacts`
- `GET /tasks/{taskId}/artifacts`

## 11. Repo Integration Strategy

Your current repo-first discipline is a strength and should be preserved.

Recommended rule:

- operational truth lives in the control plane
- delivery truth lives in the repo

The system should automatically mirror important task states into repo files for recoverability and human readability.

Suggested structure:

```text
coordination/
  task-board/
    draft/
    ready/
    assigned/
    in_progress/
    review/
    done/
    blocked/
    cancelled/
  progress/
  completed/
  incidents/
  reviews/
  phases/
```

The dashboard should not manually edit these files. Instead, the control plane writes them as rendered projections from database state, or a sync worker keeps them updated.

This avoids drift between the web UI and repo files.

## 12. Standard Task Packet Format

Use a structured front matter block so agents can parse it.

Example:

```md
---
task_id: phase2-billing-generate-01
phase: phase2-billing
status: ready
owner: unassigned
reviewer: orchestrator
priority: high
dependencies:
  - phase2-billing-create-01
allowed_scope:
  - src/billing/**
  - tests/billing/**
forbidden_scope:
  - database/migrations/**
acceptance:
  - generation API returns valid invoice payload
  - batch mode supports idempotent retries
  - tests added for success and failure paths
expected_artifacts:
  - code changes
  - test output summary
  - delivery report
---
```

Body sections:

- Objective
- Context
- Constraints
- Implementation Notes
- Validation Steps
- Escalation Rules

## 13. Agent Execution Contract

Each agent should follow a strict loop:

1. poll for assigned work
2. claim assignment
3. fetch task packet and referenced artifacts
4. execute within allowed scope
5. heartbeat periodically
6. write progress updates
7. raise incident immediately when blocked
8. submit artifacts for review
9. stop touching task after review unless reassigned

This is important: agents should not browse the whole board and freely pick work unless you intentionally enable a self-selection mode.

## 14. Claiming and Locking

This is one of the biggest missing pieces in weak kanban systems.

Recommended mechanism:

- assignment lock tied to `task_assignments`
- claim requires matching agent identity
- claim creates a time-bounded lease
- heartbeat extends lease
- expired lease returns task to `assigned` or `ready`
- orchestrator can force release

Without this, two agents may unknowingly work the same task or a dead agent may hold a task forever.

## 15. Incident Handling

Blocked work should be first-class, not an afterthought.

Incident categories:

- spec ambiguity
- missing dependency
- environment failure
- merge conflict
- capability mismatch
- flaky test
- architecture conflict

Escalation policy:

- low severity: agent continues with caution and reports
- medium severity: agent pauses task and waits for orchestrator action
- high severity: phase-level alert, possibly freeze related tasks

Resolution options:

- clarify spec
- patch backbone
- split task smaller
- swap agent
- cancel task
- convert blocker into separate prerequisite task

## 16. Review Model

Review should be formal and structured.

Required review checks:

- did the agent stay inside allowed scope
- were all expected artifacts attached
- do verification steps actually reproduce
- did any hidden regressions appear
- does the submission satisfy acceptance criteria

Possible decisions:

- `accepted`
- `needs_fix`
- `reassign`
- `rejected`

Review findings should be stored as machine-readable JSON plus human-readable markdown.

## 17. Notifications and Polling

To answer your practical question, this is how other agents know when to act:

### Option A: Polling

Each agent runs:

- `GET /tasks?agent_id=<self>&status=assigned`
- `GET /tasks?agent_id=<self>&status=needs_fix`

This is the simplest reliable model and likely best for MVP.

### Option B: Push Notifications

Later you can add:

- webhook
- message queue
- Slack bot
- email
- local desktop notification

But push is optional. Polling plus leases is enough to start.

## 18. Why This Is Better Than a Pure Kanban Board

A kanban board alone answers:

- what column is this task in

This system answers:

- who owns the task
- whether the owner actually claimed it
- what artifacts were produced
- what incident blocked it
- whether review passed
- whether it can move the phase forward
- whether the task can be replayed after failure

That is the difference between a board and a coordination system.

## 19. Recommended Build Strategy

Do not build everything at once. Build it in stages.

### Stage 1: Repo-First MVP

Keep your current file-based board, but formalize it.

Build:

- task packet schema
- progress report schema
- incident report schema
- review report schema
- CLI or script to validate file formats
- naming rules and status transition validator

Goal:

- make the current manual process reliable

### Stage 2: Control Plane API

Introduce:

- database
- task APIs
- claim / lease logic
- event log
- artifact registry

Goal:

- make assignment, progress, and review state machine reliable

### Stage 3: Sync Layer

Add:

- repo projection writer
- import/export between DB and markdown files
- PR / commit linkage

Goal:

- keep operational system and repo evidence aligned

### Stage 4: Dashboard

Add:

- board view
- task detail view
- incident panel
- review queue
- phase summary

Goal:

- improve operator efficiency without turning the UI into the source of truth

### Stage 5: Agent SDK / Worker Client

Add:

- standard agent polling client
- task parser
- report writer
- heartbeat helper
- submission helper

Goal:

- make outside agents easier to plug in with predictable behavior

## 20. Suggested Tech Stack

A pragmatic starting stack:

- backend: FastAPI or Node.js with NestJS / Express
- database: PostgreSQL
- queue or worker: Celery, RQ, BullMQ, or lightweight cron worker
- frontend: simple React dashboard
- auth: API key per agent for MVP
- repo integration: GitHub API plus local git hooks or sync worker

If you want minimal complexity, FastAPI + PostgreSQL is a strong first version.

## 21. Security and Governance

Because agents can modify code, you should enforce:

- per-agent identity
- capability profile
- scope restriction
- immutable event history
- review before final integration
- optional branch protection / PR gates

Long term, add:

- signed agent actions
- per-task credentials
- sandbox policy by task type

## 22. What I Recommend You Build First

If the goal is to get this working soon, the best next move is:

1. freeze the markdown protocol
2. define task packet front matter
3. define progress / incident / review schemas
4. add a validator CLI
5. add a small API that mirrors the same model

This avoids rebuilding from scratch while giving you a clean migration path from repo-only coordination to service-backed coordination.

## 23. Proposed MVP Deliverables

The first implementation milestone should produce:

- `docs/operations/agent-task-execution-protocol.md`
- `docs/architecture/agent-coordination-system.md`
- `coordination/templates/task-packet.md`
- `coordination/templates/progress-report.md`
- `coordination/templates/incident-report.md`
- `coordination/templates/review-report.md`
- `scripts/validate_coordination_files.*`
- minimal API spec for claim, progress, incident, submit, review

## 24. Discussion Questions

Before implementation, these are the most important decisions to settle:

1. Do you want the control plane to become the source of truth immediately, or only after the markdown protocol is stabilized?
2. Will external agents be able to poll an HTTP API, or do some of them only know how to read repo files?
3. Will review happen in the control plane, in PRs, or both?
4. Do you want self-selection mode for some low-risk tasks, or should all assignments remain orchestrator-only?
5. Is phase gating mandatory for every phase, or only for major milestones?

## 25. My Recommendation

Based on your current direction, I recommend a hybrid rollout:

- short term: formalize repo-first coordination so the current workflow stops drifting
- medium term: add a real control plane API with claim, heartbeat, incident, review, and event logging
- long term: keep the dashboard as a projection of system state, not the system itself

That gives you the strongest combination of:

- recoverability
- auditability
- controlled delegation
- predictable agent behavior
- future automation

## 26. Next Suggested Documents

The most useful follow-up documents would be:

1. `docs/operations/agent-task-execution-protocol.md`
2. `docs/specs/coordination-api-v1.md`
3. `docs/specs/task-packet-schema.md`
4. `docs/specs/review-decision-model.md`
5. `docs/roadmap/coordination-system-implementation-plan.md`

