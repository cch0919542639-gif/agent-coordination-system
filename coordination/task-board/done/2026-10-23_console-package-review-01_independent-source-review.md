---
task_id: console-package-review-01
phase: console-delivery-01
status: DONE
owner: console-review-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/evidence/console-package-review-01/**
  - coordination/delivery/console-package-review-01-delivery-report.md
  - coordination/progress/console-review-01.md
forbidden_scope:
  - candidate source changes
  - archive program changes
  - runtime databases and credentials
acceptance:
  - Start substantive review only after console-package-01 is submitted to REVIEW and its candidate commit and manifests are fixed.
  - Independently verify source/base identity, dependency and static closure, byte equality, baseline preservation, and submitted test evidence.
  - Perform one independent bounded focused check on candidate using Python3.12 and system temp; report remaining compatibility or publication gaps without overstating P1 completion.
  - Write an independent findings report and canonical delivery with explicit accepted or needs_fix recommendation and exact reviewed commit.
expected_artifacts:
  - independent_review
  - verification_evidence
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Independently review P1a console-package-01. This packet is a review dependency, not an implementation dependency: source must be REVIEW, not DONE, before review starts. Do not accept your own review task.

## Context

Read current compact context and the source task card, manifest, evidence and delivery in C:/Users/angel/.codex/worktrees/integration-context-01/codex work. Candidate is C:/Users/angel/.codex/worktrees/console-download-candidate/codex work on codex/console-package-01. Backbone is docs/roadmap/console-delivery-and-dispatch-plan.md.

## Constraints

Read candidate/source program files only; no fixes during independent review. Retain original evidence. Report issues as findings for the implementer. Scope does not include credentials, DB initialization, production listeners, provider calls, GitHub publication or changing other tasks. Review recommendation is evidence, and orchestrator will apply canonical source acceptance/needs_fix based on this independent report.

## Implementation Notes

Claim and submit through board scripts as console-review-01. Produce coordination/evidence/console-package-review-01/independent-review.md plus structured checks and canonical delivery. Include exact candidate HEAD and manifest hashes. Verify the inventory captures literal imports, runtime import risks, assets and selected tests rather than treating AST closure alone as sufficient.

## Token And Resource Impact (If Applicable)

One independent reviewer after implementation submission. One focused pytest invocation, hard timeout300seconds; no provider agents, recurring polling or browser install. Retain original logs/JUnit. Additional execution requires orchestrator direction.

## Validation Steps

Inspect candidate diff and imports, archive pins, closure and baseline assertions; run the single focused verification and authoritative coordination validator; submit evidence and recommendation to REVIEW.

## Escalation Rules

Do not repair code or silently widen checks; report source, manifest, baseline, scope or test-evidence conflicts. No remote or credential operations.
