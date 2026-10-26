---
task_id: console-handoff-review-01
phase: console-handoff-01
status: DONE
owner: console-handoff-review-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/evidence/console-handoff-review-01/**
  - coordination/delivery/console-handoff-review-01-delivery-report.md
  - coordination/progress/console-handoff-review-01.md
forbidden_scope:
  - implementation source edits
  - live accounts credentials databases or provider activity
  - push merge or external activation
acceptance:
  - Start substantive review only after both source tasks enter REVIEW and parent supplies exact integrated commit.
  - Independently verify frozen contract integration and inspect source diff, immutable claim before launch, replay and UNKNOWN behavior, bounded Git and worker containment.
  - Verify evidence hash and exact revision validation, cached-only console reads, safe role preview confirmation and backward compatibility.
  - Run proportionate isolated local Git and harmless runner plus API checks; record exact commit evidence and any blocking findings without accepting own task.
expected_artifacts:
  - independent_review
  - verification_evidence
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Independently review the integrated handoff MVP at the exact parent-supplied commit. The source tasks must first submit REVIEW. Existing PR6 remains unchanged; this is a separate unpublished feature candidate.

## Context

Read PLAN.md, PROGRESS.md, TASKS.md, both console-github-transport-01 and console-handoff-ui-01 cards and deliveries, and docs/operations/github-handoff-mvp-contract.md. Code worktree is console-download-candidate on codex/console-handoff-sync-01; authoritative evidence and lifecycle stay in integration-context-01.

## Constraints

No source edits, provider calls, remote GitHub writes, real identities/state or background service activation. Use disposable local bare Git and synthetic runner only. Preserve failures; never label an interrupted wrapper as a passing native test exit. Do not accept own or source tasks.

## Implementation Notes

Review code before choosing focused independent checks. Prioritize actual cross-clone safety, stale/foreign assignment refusal, receipt retry without reexecution, runner binding and JobProcess cleanup. Runtime FINISHED must not imply formal DONE. Evidence failures and stale/fetch errors must remain visible. Release manifest pins intentionally remain old until later metadata refresh.

## Token And Resource Impact (If Applicable)

At most two focused pytest invocations of up to300seconds each and one bounded local integration probe if justified by an untested concern. No full repository suite or dependency installs. Capture native exits, logs, JUnit and exact tested source hashes.

## Validation Steps

Claim after dispatcher authorizes substantive review; inspect exact source and delivery evidence, run focused verification, write canonical review/delivery and validate board. Submit REVIEW with recommendation or concrete findings.

## Escalation Rules

Report defects with exact paths and reproducible triggers to orchestrator. Do not silently patch source or weaken a contract check. Missing live deployment proof is a stated pilot limitation, not a request to activate services.


## Authorized independent delta review

Initial91a review preserved as initial-* and source fixes now await new exactcommit. Reopen same review owner for one additional focused invocation <=300seconds using original independent four cases plus final invalid-evidence path and API maximumglob boundary where justified. Inspect exact source delta and current source pins. No broad repeat or source edits; record native exit and final recommendation. Root completed source after original worker credit failure; independent delta reviewer remains distinct.


## Authorized bounded HTTP integration probe

Delta pytest6passed/1review-fixturefailed/native1 at86.80s. HTTP fakeParallel SimpleNamespace lacks controller on consumed-plan replay, also present in initial log: original executed-scope-repro claim was inaccurate, static scope defect remains valid. Preserve original evidence and correct current canonical report. Authorize one unused standalone integration probe <=90seconds with real HandoffService HTTP, scope preview/confirmed execute and cached reads; omit unrelated fixture replay or provide proper fixture. No further pytest/source changes.
