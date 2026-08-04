# Decisions

| Date | Decision | Rationale | Consequence |
| --- | --- | --- | --- |
| 2026-07 | Keep task lifecycle in repository files. | Git provides recoverable, reviewable evidence. | Chat is notification only. |
| 2026-07 | Route local worker deliveries owner-strict and fail-closed. | A missing owner must not leak work to another worker. | Ownerless delivery requires orchestration attention. |
| 2026-07 | Complete same-machine automation before cross-machine transport. | Shared local runtime lowers risk and validates the loop first. | Cross-machine support is deliberately deferred. |
| 2026-07 | Use progressive context files as entry points. | New threads need stable orientation without loading all documents. | Detailed specs remain the source for scoped work. |
| 2026-07 | Adopt a platform-neutral token and resource policy. | Cost control must preserve evidence and privacy across agent providers. | Provider-specific transcript tools remain opt-in and separately reviewed. |
| 2026-07 | Require explicit approval for local shared-resource Junction changes. | A Junction can affect multiple agent runtimes on one machine. | Agents must validate and plan first; only the approved plan may be applied. |
| 2026-08-01 | Hermes pilot reuses the existing owner-strict `worker activate --json` durable inbox instead of Hermes Kanban. | The repository task board remains the single lifecycle authority; Hermes Kanban would create a second dispatcher and state store. | Hermes may handle only a matching assigned task and submit it to review; it must not auto-accept, merge, push, or select unassigned work. |
| 2026-08-04 | OpenCode polling uses the Windows Task Scheduler task `OpenCode Controlled Worker` at a 10-minute cadence. | It directly wakes the accepted OpenCode launcher; Codex app automation did not trigger reliably. | The task is disabled by default; when enabled, each turn handles at most one owner-matching delivery with no retry, auto-approval, or lifecycle authority. |
| 2026-07-19 | Require a docs-agent phase summary after every evidence-backed phase or material segment acceptance. | Durable project memory must be updated from repository evidence rather than chat recollection. | The orchestrator opens a bounded summary task after acceptance; it updates the designated Master Plan with completion, integration state, residual risks, and next action. |
