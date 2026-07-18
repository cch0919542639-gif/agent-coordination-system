# Decisions

| Date | Decision | Rationale | Consequence |
| --- | --- | --- | --- |
| 2026-07 | Keep task lifecycle in repository files. | Git provides recoverable, reviewable evidence. | Chat is notification only. |
| 2026-07 | Route local worker deliveries owner-strict and fail-closed. | A missing owner must not leak work to another worker. | Ownerless delivery requires orchestration attention. |
| 2026-07 | Complete same-machine automation before cross-machine transport. | Shared local runtime lowers risk and validates the loop first. | Cross-machine support is deliberately deferred. |
| 2026-07 | Use progressive context files as entry points. | New threads need stable orientation without loading all documents. | Detailed specs remain the source for scoped work. |
