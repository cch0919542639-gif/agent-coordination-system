# Agent Task Execution Protocol

## Purpose

This document defines the standard operating protocol for multi-agent execution inside the project collaboration system.

It exists to answer five operational questions:

1. How does an agent know it should start work?
2. What must an agent read before touching files?
3. How must an agent report progress?
4. What must happen when an agent is blocked?
5. What counts as complete delivery?

This protocol is intentionally strict. The goal is not maximum freedom. The goal is reliable delegation, recoverability, and repeatable review.

## Core Rules

### Rule 1: Single Dispatcher

The orchestrator is the only authority that assigns, reassigns, or closes work.

Agents must not:

- self-assign high-risk work
- self-promote tasks across phase gates
- declare final acceptance

### Rule 2: Repo Evidence Required

Chat-only updates do not count as delivery.

A task is not complete unless the repo contains the required evidence, such as:

- code changes
- task card state update
- progress update
- incident report when blocked
- review or completion report

### Rule 3: Stay Inside Scope

Agents may only modify files and areas explicitly allowed by the task packet.

If the task requires changes outside `allowed_scope`, the agent must stop and raise an incident.

### Rule 4: Escalate Early

Blocked agents must not silently improvise around unclear specs, risky architecture, or forbidden areas.

When in doubt:

- stop
- report
- wait for orchestrator direction

### Rule 5: Review Before Done

An agent may submit work for review, but only the orchestrator or reviewer may mark it accepted and done.

## Task Lifecycle

The standard task lifecycle is:

`ready -> in_progress -> review -> done`

Possible exception states:

- `blocked`
- `needs_fix`
- `reassigned`
- `cancelled`

## Required Repo Structure

```text
coordination/
  task-board/
    ready/
    in_progress/
    review/
    done/
    blocked/
  progress/
  incidents/
  completed/
  reviews/
  templates/
```

## Agent Operating Loop

Every agent should follow the same execution loop.

### Step 1: Receive Assignment

An agent starts work only after one of these happens:

- the orchestrator explicitly assigns a task
- the system marks the task assigned to that agent

`ready/` means available for dispatch. It does not automatically mean any agent may take it.

### Step 2: Read Before Acting

Before changing anything, the agent must read:

1. the task packet
2. referenced specs or backbone docs
3. constraints and forbidden scope
4. acceptance criteria

If any of those are missing or contradictory, the agent must not start implementation.

### Step 3: Claim Work

Once the agent accepts the assignment:

- move the task card from `ready/` to `in_progress/`
- update task status to `IN_PROGRESS`
- update the owner field if needed
- create or update the agent progress file

### Step 4: Execute Within Scope

During execution, the agent must:

- stay inside the assigned scope
- keep changes focused on the task objective
- avoid unrelated cleanup unless explicitly allowed
- follow the current phase backbone and frozen rules

### Step 5: Report Progress

The agent must update `coordination/progress/<agent>.md` at meaningful checkpoints.

Minimum required fields:

- active task ID
- current step
- changed files so far
- blocker status
- next planned step

### Step 6: Escalate If Blocked

If the agent cannot proceed safely, it must:

1. stop implementation
2. create an incident report in `coordination/incidents/`
3. move the task card to `blocked/` if instructed by protocol or orchestrator
4. update progress with a blocked summary

Blocked means any of the following:

- missing or ambiguous spec
- required change falls outside allowed scope
- environment or dependency failure
- unexpected regression
- capability mismatch
- merge conflict that risks incorrect changes

### Step 7: Submit For Review

When implementation is complete, the agent must:

1. move the task card to `review/`
2. update progress status to waiting for review
3. write a completion report
4. attach changed file list, validation notes, and residual risks

### Step 8: Wait For Review Outcome

After submission, the agent must not keep editing the same task unless:

- reviewer requests `needs_fix`
- orchestrator reassigns the task back

## Task Packet Requirements

Every task packet must contain:

- `task_id`
- `phase`
- `status`
- `owner`
- `reviewer`
- `priority`
- `dependencies`
- `allowed_scope`
- `forbidden_scope`
- `acceptance`
- `expected_artifacts`

Task body must include:

- objective
- context
- constraints
- implementation notes
- validation steps
- escalation rules

If a task packet does not contain enough information to execute safely, the agent must raise an incident instead of guessing.

## Progress Reporting Standard

Each agent should maintain a single rolling progress file:

- `coordination/progress/<agent>.md`

This file should be updated whenever:

- a new task starts
- a significant checkpoint is reached
- the task becomes blocked
- the task is submitted for review

Progress is for operational visibility, not for final acceptance.

## Incident Protocol

An incident report is required when an agent is blocked or forced to choose between unsafe options.

Each incident should state:

- task ID
- agent name
- severity
- category
- concise summary
- what was attempted
- exact blocker
- recommended next action

Allowed incident categories:

- `spec_ambiguity`
- `scope_conflict`
- `environment_failure`
- `dependency_missing`
- `merge_conflict`
- `capability_mismatch`
- `regression_risk`

The orchestrator then decides whether to:

- clarify the task
- patch the backbone
- split the task
- reassign the task
- take the task back directly

## Submission Requirements

Before a task can enter review, the agent must provide:

- changed files list
- artifact paths
- validation steps performed
- test results or manual verification notes
- known residual risks
- recommended next handoff if any

If these are missing, the submission is incomplete.

## Review Outcomes

Reviewer may return one of the following:

- `accepted`
- `needs_fix`
- `reassign`
- `rejected`

Meaning:

- `accepted`: task satisfies requirements and may move to `done/`
- `needs_fix`: original agent should correct specific issues
- `reassign`: another agent or the orchestrator should continue
- `rejected`: delivery is not acceptable and should not be integrated

## Reassignment Rules

Reassignment is appropriate when:

- the current agent is blocked by capability limits
- the task was underspecified and must be re-scoped
- review reveals the work should continue with a different specialty

When reassigning:

- preserve the task ID
- preserve history
- add review notes or incident references
- clearly state what the next owner should continue from

## Definition Of Done

A task is considered done only when all of the following are true:

- implementation or report work is finished
- repo evidence exists
- required coordination files are updated
- validation is documented
- reviewer accepted the delivery
- task card has moved to `done/`

## Minimum Enforcement Rules

At minimum, every phase should enforce these checks:

1. No task starts without a task packet.
2. No task finishes without repo evidence.
3. No blocked task continues without incident or orchestrator override.
4. No task reaches `done` without review.
5. No agent edits outside scope without explicit authorization.

## Recommended Operating Pattern

For best results:

1. Orchestrator writes backbone and task packets first.
2. Agents execute only assigned packets.
3. Agents report through repo files, not memory or chat only.
4. Reviewer validates every review submission.
5. Orchestrator integrates accepted work and opens the next packet set.

## Short Version

If an agent remembers only one thing, it should be this:

Read the task packet, stay in scope, report progress in the repo, escalate blockers early, and never treat chat alone as completion.

