# Decisions

| Date | Decision | Rationale | Consequence |
| --- | --- | --- | --- |
| 2026-07 | Keep task lifecycle in repository files. | Git provides recoverable, reviewable evidence. | Chat is notification only. |
| 2026-07 | Route local worker deliveries owner-strict and fail-closed. | A missing owner must not leak work to another worker. | Ownerless delivery requires orchestration attention. |
| 2026-07 | Complete same-machine automation before cross-machine transport. | Shared local runtime lowers risk and validates the loop first. | Cross-machine support is deliberately deferred. |
| 2026-07 | Use progressive context files as entry points. | New threads need stable orientation without loading all documents. | Detailed specs remain the source for scoped work. |
| 2026-07 | Adopt a platform-neutral token and resource policy. | Cost control must preserve evidence and privacy across agent providers. | Provider-specific transcript tools remain opt-in and separately reviewed. |
| 2026-07 | Require explicit approval for local shared-resource Junction changes. | A Junction can affect multiple agent runtimes on one machine. | Agents must validate and plan first; only the approved plan may be applied. |
| 2026-07-19 | Require a docs-agent phase summary after every evidence-backed phase or material segment acceptance. | Durable project memory must be updated from repository evidence rather than chat recollection. | The orchestrator opens a bounded summary task after acceptance; it updates the designated Master Plan with completion, integration state, residual risks, and next action. |
| 2026-07-20 | Use OpenCode for the first Phase 14.5 supervised-pilot candidate, with `external-agent-platform-33`, `ORCHESTRATOR` reviewer and rollback owner, and dedicated pilot provenance. | The bounded OpenCode availability probe returned `available`; the operator authorized the recommended configuration while preserving one-shot launch approval for a later task. | The launcher contract must bind only this selected provenance, default to dry run, and reject all other runtime, worker, project, branch, worktree, or run values. |
| 2026-07-21 | After clean validation and accepted review, commit, merge, and push without an additional confirmation. | The operator authorized a streamlined completion path while retaining exceptions for unresolved concerns, failed validation, conflicts, or unclear safety scope. | The orchestrator proceeds through normal integration automatically when those gates are clean; otherwise it pauses with evidence for a decision. |
