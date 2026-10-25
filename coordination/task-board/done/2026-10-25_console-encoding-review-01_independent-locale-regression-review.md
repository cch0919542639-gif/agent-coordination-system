---
task_id: console-encoding-review-01
phase: console-delivery-01
status: DONE
owner: console-encoding-review-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/evidence/console-encoding-review-01/**
  - coordination/delivery/console-encoding-review-01-delivery-report.md
  - coordination/progress/console-encoding-review-01.md
forbidden_scope:
  - implementation source edits
  - private live identities credentials permissions or databases
  - publication or merge
acceptance:
  - Review after console-encoding-fix-01 enters REVIEW with exact fixed commit and captured red/final execution evidence.
  - Verify SID extraction never decodes account-name text and validates only the correct single CSV SID field, with malformed/empty/oversized/failure output refused safely.
  - Independently verify non-ASCII UTF8 and CP950 cases and isolated -I regression, and preserve permission checks rather than assuming one locale.
  - Verify scoped diff and final tests, report limitations and exact-commit recommendation without claiming full second-host acceptance.
expected_artifacts:
  - independent_review
  - verification_evidence
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Independently assess the locale-sensitive Windows SID initialization repair. Source REVIEW must precede substantive review; old published failure and UTF8 workaround remain historical evidence.

## Context

Authoritative source board integration-context-01; candidate console-download-candidate branch codex/console-bootstrap-01 startingc7f7dee. Read source card and original external evidence at origin/docs/console-download-verification-20261024 commit4a0f61d. Original report114pass/1fail is an acceptance blocker, not success.

## Constraints

No source fixes or live private state/identity disclosure. Use synthetic username bytes and disposable state. One focused independent pytest invocation up to300seconds, with observed child exit and logs/JUnit; one bounded Python3.13 isolated-child smoke if locally available. No wrapper interruption while children run except actual timeout. No new installed dependency, global locale change, browser or provider activity. Do not accept own/source task.

## Implementation Notes

Claim and submit through board scripts as console-encoding-review-01. Assess parser boundary/trust assumptions and all callers, rejection behavior, default-encoding independence, and actual emitted bytes rather than only a forcedUTF8 path. Compare original source regression result to repaired source hashes. Publication manifest intentionally still old until separate metadata refresh; do not mistake stale release pins for a reason to edit source in review. Code review recommendation should identify the need for exact repaired release pins and rerun on the failed acceptance environment.

## Token And Resource Impact (If Applicable)

One independent reviewer after source delivery; one bounded focused suite and optional bounded existing Python3.13 smoke. No provider calls or new services beyond disposable fixture listeners.

## Validation Steps

Read source/old failure and tests; inspect exact diff; run focused checks with output/exit captured; inspect Python3.13 -I evidence and rejection-path cases. Record exact reviewed SHA and hashes, remaining acceptance gate, and coordination validator result. Submit review to REVIEW for orchestrator.

## Escalation Rules

Report concrete parser, output, identity, ACL or evidence issue rather than patching code. Never weaken permission validation or overwrite existing real credentials/state to make a check pass.
