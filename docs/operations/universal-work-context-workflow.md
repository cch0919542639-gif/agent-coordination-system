# Universal Work Context Workflow

## Purpose

This workflow turns any work item, not only software delivery, into a small,
recoverable operating loop. It combines progressive context disclosure with a
production-first delivery standard: an agent loads only the context needed for
the current decision, but every meaningful outcome remains documented and
verifiable.

For recurring agent workflows, also apply
`docs/operations/token-efficiency-policy.md`. Efficiency work must preserve
validation evidence, privacy boundaries, and a recovery path.

## Context Kit

Every active project keeps these top-level entry files. They are a navigation
layer, not a replacement for detailed specifications, code, or task evidence.

| File | Purpose | Update trigger |
| --- | --- | --- |
| `AGENTS.md` | Operating rules, safety limits, and required reading order. | Rules or tooling change. |
| `PLAN.md` | Objectives, milestones, dependencies, and exit criteria. | Milestone starts, ends, or is replanned. |
| `PROGRESS.md` | Current factual state, active work, blockers, and next action. | Start/end of a work session or material status change. |
| `DECISIONS.md` | Decision, rationale, alternatives, and consequences. | Non-trivial decision or reversal. |
| `TASKS.md` | Index to the authoritative task system and active task groups. | Task grouping or priority changes. |
| `MEMORY.md` | Durable facts, constraints, references, and lessons worth reusing. | A fact should survive a new thread. |
| `CHANGELOG.md` | Human-readable accepted changes. | A milestone, release, or accepted change. |
| `ARCHITECTURE.md` | System/work breakdown, boundaries, and deep-document links. | Architecture or operating boundary changes. |

## Progressive Disclosure

Do not load every document by default. Use this order:

1. Read `AGENTS.md`, `PLAN.md`, and `PROGRESS.md` to orient.
2. Read `DECISIONS.md` only when a current choice or constraint matters.
3. Read `TASKS.md` and the assigned task packet before acting.
4. Read `ARCHITECTURE.md`, specifications, research, or source code only for
   the scoped implementation or review question.
5. Read `MEMORY.md` when a prior fact, learned limitation, or external
   reference could change the decision.

## Delivery Loop

```text
intake -> orient -> plan -> task packet -> execute -> verify/review
       -> operate/release -> learn -> next milestone
```

### 1. Intake

Record the outcome, owner, constraints, risk, and evidence of success. Decide
whether the work is a quick operational action, a task packet, or a new phase.

### 2. Orient

Load the minimum context kit. Confirm repository, current milestone, active
task, decisions, and the authoritative task board before editing.

### 3. Plan

Define the smallest useful milestone, exit criteria, dependencies, non-goals,
and a verification approach. Put stable decisions in `DECISIONS.md`, not chat.

### 4. Execute

Work only in the task's approved scope. Keep progress current. Escalate a
blocker as an incident instead of guessing across a safety or scope boundary.

### 5. Verify And Review

Use objective evidence: tests, validation, deliverables, and scope checks.
Review decides accepted, needs-fix, reassign, or rejected. A chat claim alone
is never completion.

### 6. Operate Or Release

For a live workflow, verify safe configuration, rollback/stop conditions,
resource cost, ownership, and monitoring before declaring it usable.

### 7. Learn

Update `PROGRESS.md`, `CHANGELOG.md`, and only the durable parts of
`MEMORY.md`. Update `PLAN.md` when the milestone changes.

## Production-First Quality Gate

Before accepting a production-facing change, check:

- correctness and an explicit acceptance criterion
- safe failure behavior and rollback/stop condition
- privacy, credential, and sensitive-data boundaries
- resource, cost, and polling/concurrency impact
- conventions and compatibility with the existing system
- observability or evidence needed to diagnose a failure
- tests or a proportionate reproducible verification procedure

## New Thread Or Agent Handoff

Use this compact handoff sequence:

1. Pull the correct repository and confirm its branch/worktree.
2. Read `AGENTS.md`, `PLAN.md`, `PROGRESS.md`, and the assigned task card.
3. Read linked decision, architecture, and evidence files only as needed.
4. Execute the scoped task and update progress/evidence in the repository.
5. On completion, update the context kit entries affected by the work.

## Relationship To Coordination

For coordinated projects, `coordination/task-board/` remains authoritative for
task lifecycle. `TASKS.md` is only an index and grouping aid. The context kit
does not override task-card status, incident handling, review decisions, or
repository-specific profiles.
