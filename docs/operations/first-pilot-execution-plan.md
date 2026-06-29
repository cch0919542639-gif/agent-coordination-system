# First Pilot Execution Plan

## Purpose

This document defines the first real execution wave for external agents.

It is the operational bridge between:

- the repo-first coordination system
- the first live task cards
- the orchestrator's actual dispatch sequence

The goal is to complete one clean end-to-end pilot loop before expanding parallel work.

## Pilot Objective

Validate that external agents can execute assigned repo-backed tasks with minimal chat support and produce reviewable outcomes through the standard coordination workflow.

## Success Criteria

The first pilot is successful if all of the following happen:

1. at least one task moves cleanly from `ready` to `in_progress` to `review`
2. the assigned agent updates `coordination/progress/` correctly
3. any blocker is reported through `coordination/incidents/`
4. review can be completed from repo evidence alone
5. the accepted result becomes a reusable reference for later agents

## First Wave Scope

Use only the existing first-wave live task cards:

- `phase1-live-01`
- `phase1-live-02`
- `phase1-live-03`

Do not open all three at once.

## Recommended Dispatch Order

### Wave 1A

Dispatch first:

- `phase1-live-01`
  - owner: `external-agent-docs-01`
  - purpose: verify new-agent onboarding flow works from repo context alone

Why this one first:

- low technical risk
- easy to review
- directly improves future onboarding for the next agents

### Wave 1B

After `phase1-live-01` reaches a healthy `in_progress` state, dispatch one of:

- `phase1-live-02`
  - owner: `external-agent-tools-01`
  - purpose: validate small tooling improvements with code review and validator usage

or

- `phase1-live-03`
  - owner: `external-agent-docs-02`
  - purpose: validate reviewer guidance and make future reviews faster

Recommendation:

- choose `phase1-live-02` if you want to test code/tool changes early
- choose `phase1-live-03` if you want to strengthen review discipline first

### Wave 1C

Dispatch the remaining third task only after:

- the first task has reached `review`, or
- the second task has shown correct progress behavior without confusion

## Recommended Agent Assignment

- `phase1-live-01` -> `external-agent-docs-01`
- `phase1-live-02` -> `external-agent-tools-01`
- `phase1-live-03` -> `external-agent-docs-02`

If you only want to run with one external agent first:

1. start `phase1-live-01`
2. wait for review
3. then assign `phase1-live-02`
4. hold `phase1-live-03` for later

If you want to run with two agents:

1. start `phase1-live-01`
2. confirm correct progress update
3. then start `phase1-live-02`
4. hold `phase1-live-03` until one of the first two is stable

## Exact Work To Be Executed

### Task 1: Onboarding Quickstart

Task ID:

- `phase1-live-01`

Expected result:

- a short onboarding guide for new external agents

What this validates:

- task packet clarity
- documentation-only execution
- progress reporting quality
- review from repo evidence

### Task 2: Validator Enhancement

Task ID:

- `phase1-live-02`

Expected result:

- one or two small improvements to `scripts/validate_coordination_files.py`

What this validates:

- tooling changes inside allowed scope
- command-based verification
- small code task collaboration

### Task 3: Reviewer Playbook

Task ID:

- `phase1-live-03`

Expected result:

- a compact reviewer guide for triaging agent submissions

What this validates:

- reviewer support material
- documentation consistency with the protocol
- decision discipline for later waves

## Orchestrator Execution Steps

### Step 1: Pre-Flight Check

Before dispatching anything:

1. confirm all three tasks remain in `coordination/task-board/ready/`
2. run `python scripts/validate_coordination_files.py`
3. confirm the external agent has repo access
4. confirm you are available to inspect the first progress update

### Step 2: Send First Dispatch

Send the ready-made message for `phase1-live-01` from:

- `docs/operations/first-wave-dispatch-pack.md`

### Step 3: Wait For First Progress Evidence

Do not dispatch the next task immediately.

Wait until you see:

- task card moved to `in_progress/`
- `coordination/progress/external-agent-docs-01.md` created or updated
- progress entry is understandable and relevant

### Step 4: Evaluate Early Signal

If the first agent does the above correctly:

- continue to Wave 1B

If not:

- stop expansion
- patch the protocol or task wording first

### Step 5: Send Second Dispatch

Choose one:

- `phase1-live-02` if you want to test tool/code collaboration
- `phase1-live-03` if you want to strengthen review behavior first

### Step 6: Review Every Submission Manually

For this first pilot:

- do not batch reviews
- do not delay review too long
- do not accept chat-only completion claims

### Step 7: Decide Whether To Open The Third Task

Only open the third task if:

- first progress updates were clean
- no major scope confusion happened
- review workload stayed manageable

## Early Checkpoints

These are the three most important checkpoints.

### Checkpoint A: Start Correctly

Verify:

- task moved to `in_progress/`
- progress file exists
- no immediate process confusion

### Checkpoint B: Report Correctly

Verify:

- progress mentions actual current step
- changed files are listed
- next step is clear
- blockers are reported instead of hidden

### Checkpoint C: Submit Correctly

Verify:

- task moved to `review/`
- delivery evidence exists
- validation notes exist
- review can be completed from repo files

## Stop / Pause Conditions

Pause the pilot if any of these happens:

- agent cannot tell where to report progress
- task scope is misunderstood in a repeated way
- completion is declared without repo evidence
- blocker is handled by improvisation instead of incident
- review depends heavily on chat reconstruction

If paused:

1. patch the relevant doc or template
2. commit the protocol improvement
3. restart only after the rule is clearer

## Recommended Review Rhythm

For the first pilot:

- check within a short time after the first `in_progress` update
- check again when the task reaches `review`
- write a review report immediately after inspection

Do not let the first live tasks sit in `review` too long. Fast feedback is part of validating the system.

## What To Capture After The Pilot

After the first two or three tasks complete, create a short retrospective with:

- what agents understood immediately
- what still required chat clarification
- which task fields were most helpful
- which reporting rules were ignored or misunderstood
- what must change before scaling to more agents

## Practical Recommendation

The most stable starting sequence is:

1. dispatch `phase1-live-01`
2. wait for correct `in_progress` + progress update
3. dispatch `phase1-live-02`
4. review both
5. dispatch `phase1-live-03` only after the first two are stable

That gives you one docs task, one tooling task, and one reviewer-support task without overloading the first live wave.

