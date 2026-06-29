# Phase 1 Retrospective

## Purpose

This document captures what Phase 1 (the first live pilot) validated, what remained weak or ambiguous, and what should be tightened before broader scaling. It is based entirely on repo evidence from the three live pilot tasks and the sample foundation task.

## Pilot Summary

Phase 1 ran three live tasks through the full repo-first workflow:

| Task | Owner | Outcome |
|---|---|---|
| `phase1-live-01` — onboarding quickstart | external-agent-docs-01 | Accepted |
| `phase1-live-02` — validator enhancement | external-agent-tools-01 | Accepted (needs_fix once) |
| `phase1-live-03` — reviewer playbook | external-agent-docs-02 | Accepted |

All three completed the `ready -> in_progress -> review -> done` lifecycle. One sample scope-conflict incident was created and resolved during the foundation phase.

## What Worked Well

### 1. Repo-first dispatch works end to end

All three agents started from the task packet and protocol doc without needing pre-chat explanation. Each moved the task card, updated progress, and submitted for review independently.

### 2. Validator enforcement improves data quality

The validator caught front-matter issues during `phase1-live-02` development. The two new checks (valid task statuses, valid review decisions) will make future packets harder to misuse.

### 3. Progress files preserve operational context

Every agent's progress file records active task, changed files, blocker status, and next step. An orchestrator reading only the repo can reconstruct what happened.

### 4. Reviewer discipline is now documented

The reviewer playbook (`docs/operations/reviewer-playbook.md`) standardizes the four outcome decisions and the minimum checks required before accepting a submission.

### 5. Incident path exists and was used

The sample scope-conflict incident shows the escalation mechanism works. The agent stopped, wrote a report, and did not continue by guessing.

## What Remained Weak or Ambiguous

### 1. Delivery report gap

The `phase1-live-01` review notes explicitly flag that the task packet listed `delivery_report` under expected artifacts, but none of the three live tasks produced a separate delivery report. Progress updates and the final submission message served as delivery evidence, but the standard was informal.

This is the primary motivation for Phase 2 task `phase2-02`.

### 2. Scope boundary interpretation

The sample-agent incident revealed ambiguity about whether a "more realistic" demonstration could touch `src/`. While the incident was resolved cleanly, the line between documentation examples and actual implementation is not explicitly defined in the protocol.

### 3. No explicit completion report artifact

The protocol (Step 7) says the agent should "write a completion report" when submitting for review, but no template or standard exists for what a completion report must contain. In practice, the agent's final chat message and progress update served this role, but this is not captured as a formal repo artifact.

### 4. Needs-fix cycle not tested in live tasks

Only `phase1-live-02` went through a needs-fix cycle (missing documentation). The fix-and-resubmit path is documented but was exercised only once, late in the pilot. The mechanics (e.g. whether the card stays in `review/` or moves back to `in_progress/`) may need clarification.

### 5. Validator coverage is useful but narrow

The validator checks front matter, labels, status values, and decision values. It does not verify cross-references (e.g. that a progress file's task ID matches a real task card). It does not enforce the completion report standard because no such standard exists yet.

## Open Risks

### Risk 1: Artifact looseness will compound at scale

With 3 tasks, informal delivery evidence was manageable. With 10+ concurrent tasks, missing delivery reports and ad-hoc completion summaries will make review slower and more error-prone.

### Risk 2: Real project scope is wider than pilot scope

Pilot tasks were confined to `docs/**`, `coordination/**`, and `scripts/**`. Real engineering tasks will touch `src/**`, `database/**`, and `infra/**`. The scope compliance check will be harder when multiple agents modify overlapping areas.

### Risk 3: No CI enforcement yet

The validator must be run manually. There is no pre-commit hook or CI gate. A skipped validation step means incorrect packets can enter the workflow undetected.

### Risk 4: Needs-fix workflow is under-tested

The needs-fix path was exercised once. Ambiguities in card movement (stay in `review/` vs. move back to `in_progress/`) could cause confusion under pressure.

## Recommended Protocol Changes

### R1. Create a delivery report template and require it

Add a template at `coordination/templates/delivery-report.md`. The validator should warn when a task packet lists `delivery_report` under expected artifacts but no matching report file exists.

### R2. Clarify scope boundary rules for examples and demos

Add a note to the protocol or task packet template explaining that documentation examples are allowed inside `docs/` and `coordination/` by default. If source-code examples are needed, a separate packet with explicit scope changes must be created.

### R3. Standardize the completion report format

Add a short completion report standard to Step 7 of the protocol. The report must contain: changed files list, validation notes, residual risks, and recommended handoff. This can be part of the delivery report effort (`phase2-02`).

### R4. Formalize the needs-fix card movement rule

The protocol should state: when a reviewer returns `needs_fix`, the task card stays in `review/` with status `NEEDS_FIX`. The agent updates progress, makes the fix, and returns the card to `REVIEW` when done. No folder move is required.

### R5. Plan validator CI integration

The validator should be added as a pre-commit hook or CI check before Phase 3. This is out of scope for Phase 2 but should be documented as a dependency for scaling.

## Summary

Phase 1 proved the repo-first workflow is viable. All three pilot tasks completed with accepted reviews. The main gap is artifact discipline: delivery reports, completion reports, and scope boundary documentation are still informal. Phase 2 should harden these before opening real engineering work.
