# Coordination System Implementation Plan

## Purpose

This document turns the existing coordination architecture and API spec into a concrete build plan.

It is intended to answer one practical question:

How do we move from today's repo-first semi-automation into a real coordination service where agents can self-serve assigned work, report progress, raise incidents, submit for review, and only stop for blockers or decisions?

## Current State

The project already has a strong repo-first operating model:

- phase intake and task packet templates
- progress, incident, review, and delivery-report templates
- task-board folder conventions
- validator enforcement
- orchestration scripts through `scripts/orchestrate.py`
- GitHub-backed artifact recovery

This is a strong base.

The main bottleneck is no longer process definition.

The main bottleneck is transport:

- no shared claimable task service
- no agent polling endpoint
- no claim lease / heartbeat authority
- no event-backed state store
- no automatic callback path from agent execution back to orchestrator

## Target State

The target system is a coordination control plane with three responsibilities:

1. operational state authority
2. event-backed audit trail
3. repo-artifact linkage

In the target model:

- orchestrator creates or assigns tasks through the control plane
- agents poll only their assigned or fix-required tasks
- agents claim tasks through the service
- the service enforces leases and valid state transitions
- agents write code and reports in the repo as before
- orchestrator reviews through structured service-backed state
- repo files remain the recovery and evidence layer

## Non-Goals For The First Build

The first implementation should not try to solve:

- full auth platform integration
- complex multi-tenant access control
- distributed job execution
- real-time push notifications as a hard requirement
- replacing the repo as evidence storage

The first build only needs to make the orchestration loop reliable and self-serve.

## Recommended Rollout Strategy

Build this in five stages.

### Stage 0: Freeze The Existing Contract

Goal:

- treat the current markdown protocol as the compatibility contract

Required outcome:

- task packet front matter is stable
- progress / incident / review / delivery schemas are stable
- validator remains the repo-side enforcement mechanism

Why this matters:

- the control plane should mirror the existing model, not invent a second workflow

### Stage 1: Control Plane MVP

Goal:

- create the smallest useful coordination API and database

Build:

- API service
- relational database
- core tables: `tasks`, `task_assignments`, `task_events`, `incidents`, `reviews`, `artifacts`, `agents`
- API key auth for orchestrator and agents

Must-have endpoints:

- `POST /tasks/{taskId}/assign`
- `GET /tasks?agent_id=<id>&status=assigned`
- `POST /tasks/{taskId}/claim`
- `POST /tasks/{taskId}/progress`
- `POST /tasks/{taskId}/incidents`
- `POST /tasks/{taskId}/submit`
- `POST /tasks/{taskId}/review`
- `POST /tasks/{taskId}/reassign`

Minimum behaviors:

- state transition validation
- assignment ownership checks
- append-only event creation on every state change
- simple artifact registration

Success condition:

- an external agent can complete one full assigned-task loop without you manually relaying each state transition

### Stage 2: Claim Lease And Heartbeat

Goal:

- prevent ghost owners and duplicate execution

Build:

- `POST /tasks/{taskId}/heartbeat`
- claim lease expiry fields
- stale-claim release worker
- timeout detection for in-progress tasks

Required rules:

- only assigned agent may claim
- claim creates lease
- heartbeat extends lease
- expired lease returns task to `assigned` or flags it for orchestrator action

Success condition:

- if an agent disappears mid-task, the system can recover ownership without manual repo archaeology

### Stage 3: Repo Sync Layer

Goal:

- preserve the repo as evidence while moving operational truth into the control plane

Build:

- export or projection worker from DB state into `coordination/`
- import or reconciliation command for bootstrapping from repo state
- deterministic file rendering for:
  - task board entries
  - progress files
  - incidents
  - reviews

Recommended rule:

- control plane is operational truth
- repo is delivery truth and recovery surface

Success condition:

- the dashboard/API and repo no longer drift apart

### Stage 4: Agent Client

Goal:

- remove hand-built agent instructions for routine operations

Build:

- standard CLI client for external agents
- commands such as:
  - `agent poll`
  - `agent claim`
  - `agent heartbeat`
  - `agent progress`
  - `agent incident`
  - `agent submit`

The client should still:

- read task details
- write repo artifacts
- attach delivery evidence

Success condition:

- agent instructions become short: authenticate, poll, claim, execute, submit

### Stage 5: Dashboard And Notification Layer

Goal:

- improve operator efficiency, not redefine system behavior

Build:

- review queue view
- blocked task panel
- assignment panel
- phase summary view
- optional webhook or chat notifications

Important rule:

- dashboard is a projection over API state, not the source of truth

Success condition:

- orchestrator time spent on queue inspection and state reconstruction drops sharply

## MVP Scope Recommendation

If you want the fastest path to useful automation, do not build all five stages now.

Build only this MVP slice:

1. FastAPI service
2. PostgreSQL database
3. task / assignment / event / incident / review / artifact tables
4. eight core endpoints from `coordination-api-v1`
5. API-key auth
6. one small CLI client for agent polling and progress submission
7. manual repo sync at first

This is enough to prove the model.

## Why Polling First

Use polling before push notifications.

Polling is the best MVP transport because:

- agents can self-serve with minimal assumptions
- it avoids webhook and queue complexity
- it works across different external agent environments
- it is easier to reason about during debugging

Recommended first loop:

- agent polls every 30 to 90 seconds for:
  - `assigned`
  - `needs_fix`

Push notifications can come later.

## Database Model For MVP

Use these tables first:

- `agents`
- `tasks`
- `task_assignments`
- `task_events`
- `incidents`
- `reviews`
- `artifacts`

Optional in MVP:

- `phases`

Useful compromise:

- include `phases` early if you want the API to stay aligned with the current repo operating model

## Tech Stack Recommendation

Recommended stack:

- backend: FastAPI
- database: PostgreSQL
- ORM / migrations: SQLAlchemy + Alembic or SQLModel + Alembic
- auth: API keys per client
- background work: lightweight worker or cron loop
- CLI client: Python to match the current script stack

Why this stack:

- it matches the repo's current script ecosystem
- it is easy to iterate locally
- it is enough for MVP without heavy platform overhead

## Suggested Repository Layout

If you build this inside the same repo, a pragmatic layout is:

```text
services/
  coordination_api/
    app/
      api/
      models/
      schemas/
      services/
      auth/
      workers/
    alembic/
    tests/
clients/
  coordination_agent/
    coordination_agent/
    tests/
docs/
  specs/
  roadmap/
```

This keeps the control plane separate from the billing module while still allowing coordinated evolution.

## First Real Engineering Tasks To Open

Once you want to execute this plan, the first practical implementation wave should be:

### Task A: Service Skeleton

- scaffold FastAPI app
- add health endpoint
- add config and API-key auth skeleton
- add DB connection

### Task B: Core Data Model

- create DB schema for agents, tasks, assignments, events, incidents, reviews, artifacts
- add initial migrations

### Task C: Assignment / Claim API

- implement assign, poll, claim endpoints
- enforce ownership and status transitions

### Task D: Progress / Incident / Submit API

- implement progress, incident, artifact, submit endpoints

### Task E: Review / Reassign API

- implement review and reassign endpoints

### Task F: Agent CLI MVP

- implement polling, claim, progress, incident, submit commands

## Success Metrics

You should consider the coordination API MVP successful when all of the following are true:

- an external agent can poll assigned work without you forwarding task details manually
- an agent can claim and heartbeat a task
- an agent can submit progress and incidents into a shared service
- orchestrator can review and reassign through structured state
- repo artifacts remain linked to task records
- a task can be reconstructed from service state plus repo evidence after an interrupted run

## Risks To Watch

The most likely failure modes are:

- building the UI too early
- letting repo and DB drift
- over-designing auth before the workflow is proven
- introducing a control plane that does not match the markdown protocol already in use
- skipping claim leases and then rediscovering duplicate-work problems later

## My Recommendation

Do not treat this as a greenfield platform project.

Treat it as a thin control plane wrapped around an already-working repo-first workflow.

That means:

- reuse the current task model
- reuse current naming and evidence rules
- reuse current validator logic where possible
- add only the smallest stateful service needed to remove you as the message relay

That is the fastest route from today's semi-automation to the behavior you actually want:

- agents act on their own
- the system keeps state
- you intervene only on blockers, review decisions, or policy questions
