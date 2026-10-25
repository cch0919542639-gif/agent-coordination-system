---
task_id: acs-memory-preflight-01
phase: acs-memory-pilot
status: REVIEW
owner: codex-memory-implementation
reviewer: user
priority: high
dependencies: []
allowed_scope:
  - scripts/curated_memory.py
  - tests/scripts/test_curated_memory.py
  - docs/operations/curated-memory-guide.md
  - docs/specs/acs-agentmemory-integration.md
  - docs/specs/acs-agentmemory-plan.md
  - docs/specs/acs-agentmemory-context.md
  - coordination/evidence/acs-memory-preflight-01/**
  - coordination/delivery/acs-memory-preflight-01-delivery-report.md
  - coordination/progress/codex-memory-implementation.md
  - coordination/task-board/in_progress/2026-10-26_acs-memory-preflight-01_curated-memory-integration.md
  - coordination/task-board/review/2026-10-26_acs-memory-preflight-01_curated-memory-integration.md
  - PROGRESS.md
forbidden_scope:
  - worker launchers controllers and formal acceptance logic
  - NAS persistent deployment live accounts credentials and real memory data
  - real provider processing before endpoint and source authorization
  - external publication and merge without task authorization
acceptance:
  - Pin and validate curated source cards against their actual Git blobs and repository identity before any network or receipt writes.
  - Bind operator approval to exact batch content and explicitly declared processing scope; preview is offline and side-effect free.
  - Support official conversation import and read verification with durable per-card receipts and safe ambiguous-delivery handling.
  - Return only verified active curated cards with exact provenance; exclude unverified model text and shared persona from query output.
  - Exercise duplicate replay source tampering scope mismatch timeouts supersession withdrawal and unavailable service using synthetic fixtures only.
  - Prepare ten source candidates and frozen question expectations without self-approving real document processing.
expected_artifacts:
  - implementation_and_tests
  - operator_guide_and_scope_contract
  - validation_evidence_and_delivery
---
# Task Packet

## Objective

Implement the approved planning scope as a bounded offline-first adapter. The user approved implementation on 2026-10-26. Local code, documentation, synthetic tests and reviewable source candidates are authorized. Model/provider and real document processing remain unresolved; do not invent their approval or equate fixture results with live AgentMemory acceptance.

## Context

The approved local spec is the 2026-10-25 ACS/NAS plan. Git remains formal authority; AgentMemory is an optional derived memory. NAS 0.4.3 smoke tests proved only manual persona context and were cleaned up. Main-based isolated clone preserves previous evidence branches.

## Constraints

Use Python standard library and existing repo conventions. Add one CLI seam; do not alter task dispatch, hooks, acceptance or the AgentMemory server. Runtime receipts remain outside Git. Authentication secrets come only from environment. No live credentials or provider calls during development.

## Validation Steps

Run focused tests against synthetic temporary Git repositories and a loopback contract fixture; run coordination validation and diff checks. Preserve native exit and JUnit. Document the difference between local contract tests and upstream server/model proof. Submit REVIEW, never self-accept.

## Implementation Notes

Use exact Git blobs instead of working-tree Markdown. Persist delivery intent before HTTP; verify extracted atoms before activating a batch. The query adapter returns approved source cards only and excludes unverified L2/L3 context. No task dispatch or controller behavior is changed.

## Escalation Rules

If current upstream cannot preserve source markers or return verifiable L1 records, hold the deployment gate. Unknown delivery is reconciled read-only or held, never blindly retried. Ask for explicit model/source decisions after safe implementation and a concrete preview exist.
