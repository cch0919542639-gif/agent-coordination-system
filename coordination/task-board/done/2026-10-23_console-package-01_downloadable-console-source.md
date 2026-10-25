---
task_id: console-package-01
phase: console-delivery-01
status: DONE
owner: console-platform-01
reviewer: console-review-01
priority: high
dependencies: []
allowed_scope:
  - .gitattributes
  - web/**
  - coordination_runtime/**
  - scripts/**
  - tests/**
  - docs/**
  - coordination_common.py
  - coordination/evidence/console-package-01/**
  - coordination/delivery/console-package-01-delivery-report.md
  - coordination/progress/console-platform-01.md
forbidden_scope:
  - .git/**
  - data/**
  - integrations/**
  - credentials
  - unrelated baseline files
acceptance:
  - Freeze archive b31267f source and main bfc5163 candidate base; record full commits and exact raw and Git source hashes.
  - Derive the transitive local import and static-asset closure required by web.api and select proportionate existing tests and operator contracts.
  - Prepare an additive candidate from main in the designated clean worktree; preserve accepted source bytes and report any baseline collisions rather than overwriting them.
  - Verify isolated imports and existing console-focused checks using Python3.12 and a fresh temp directory; retain original failures and exact commands/results.
  - Produce an inventory manifest, changed-file list, delivery report, source provenance, baseline non-regression evidence and bounded P1b follow-up scope.
  - No runtime or credential setup, provider call, remote publication, worker runtime launch or task acceptance occurs in this packet.
expected_artifacts:
  - candidate_source
  - source_manifest
  - dependency_inventory
  - verification_evidence
  - delivery_report
execution_mode: WORKTREE
branch: codex/console-package-01
worktree_path: C:/Users/angel/.codex/worktrees/console-download-candidate/codex work
machine_id: angeline
---
# Task Packet

## Objective

Deliver P1a: a minimal, pinned, locally verified console candidate from main plus a complete dependency inventory. P1b bootstrap is a later packet. A local candidate commit is authorized after validation to make clean clone checks reproducible; push/merge/publication is not authorized.

## Context

Read AGENTS.md, PLAN.md, PROGRESS.md, TASKS.md and docs/roadmap/console-delivery-and-dispatch-plan.md in the authoritative board repository. User selected this console sequence on 2026-10-23 and explicitly requested execution through the collaboration system. Earlier no-next-task and old pytest3/3 entries apply to historical packets only.

Board/source: C:/Users/angel/.codex/worktrees/integration-context-01/codex work at b31267f before this new orchestration metadata. Candidate: C:/Users/angel/.codex/worktrees/console-download-candidate/codex work, branch codex/console-package-01, baseline origin/main bfc5163. The candidate is a separate checkout; read its context and preserve its existing baseline. Follow ponytail skill already active in parent session.

## Constraints

Authoritative lifecycle and worker reports live ONLY in the board/source checkout. Candidate source changes live ONLY in the candidate checkout. allowed_scope source paths refer to candidate; coordination evidence/progress/delivery paths refer to board/source. Do not edit source archive program bytes or root D:/codex work. Do not copy live DBs, ACKs, accounts, secrets or ignored runtime state. No changes to historical completed task cards. If an existing tracked source conflicts, report the exact collision and propose the narrowest safe resolution to the orchestrator before replacing it.

## Implementation Notes

Use existing board scripts for claim and submit from the board checkout. Claim as console-platform-01. Analyze AST imports, runtime imports, static files and existing tests rather than copying the whole archive. Use only additive source unless explicitly authorized for a demonstrated collision. Candidate-only metadata documents may be added if needed. A deterministic inventory script is appropriate if it makes manifests and checks repeatable; keep it small and stdlib-only. No dependencies may be installed. Do not create accounts or launch the web server for this inventory task. HTTP fixture tests may use their existing synthetic accounts and ephemeral test listeners.

## Token And Resource Impact (If Applicable)

One implementation agent, then a separate review agent. No provider workers, recurring polling or production services. This new task permits at most three pytest invocations for the implementer (focused then affected, only repair-driven repeat), each bounded by 300 seconds with system-temp basetemp. Use concise stdout and retain JUnit/logs for review. Any additional suite needs orchestrator direction. Independent reviewer has its own one focused check budget.

## Validation Steps

1. Record source/base/branch and before status; build and verify local dependency/static closure and source hashes.
2. Verify isolated imports load candidate files, not archive/original paths.
3. Run existing focused console checks and proportionate affected checks with timeout and logs, preserving failures. No full repository suite by default.
4. Verify the candidate diff is additive and copied source/test bytes match the pinned archive; run diff checks and authoritative coordination validation before submission.
5. Write evidence under coordination/evidence/console-package-01 and canonical delivery/progress reports, then submit through orchestrate.py submit. Stop editing after REVIEW.

## Escalation Rules

Record and report missing dependencies, source/base conflicts, unexpected source modifications, required out-of-scope changes, secrets or destructive/external activation requirements. Continue safe dependency analysis while awaiting a specific collision resolution. Never fake completion or weaken acceptance to pass.

## Orchestrator Scope Clarification (2026-10-23)

Narrow baseline collision authorized: candidate scripts/coordination_common.py may be replaced with exact pinned b31267f source bytes. Orchestrator inspected the whitespace-normalized diff: parallel_marker/require_serial/guard_shared_write and guards in write_text/move_task are the semantic additions. Record before/after raw and blob hashes, preserve all other baseline tracked program files, and verify serial writes still work without marker while marker-protected writes refuse. This exception satisfies the collision escalation requirement; it does not authorize broad baseline replacement.

## Orchestrator Byte-Pinning Clarification (2026-10-23)

Additive candidate .gitattributes is authorized with explicit path -text entries only for imported pinned source/test/doc files. No wildcard or global Git configuration changes. Initial local 5415bd9 normalized some CRLF Git blobs despite identical tested working bytes; retain that history and make a new correction commit. Recheck final raw/blob pins and fresh clone with core.autocrlf=true; do not repeat passing pytest unless raw bytes change.
