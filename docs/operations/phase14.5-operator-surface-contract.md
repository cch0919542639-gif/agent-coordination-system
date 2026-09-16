# Phase 14.5 Operator Surface Contract

`scripts/operator_surface.py` is a pure, JSON-ready projection helper. It
never reads or writes repository state, starts a runtime, contacts a network,
accesses credentials, invokes Git, merges, pushes, or cleans up worktrees.

`project_operation(operation, record)` accepts exact, safe records for
`plan`, `admit`, `dispatch`, `run-status`, `review-bundle`, and
`approval-queue`. It returns a stable allowlisted projection or
`deny_unsafe_operator_record`. Inputs reject prompt, source, transcript,
credential, raw-output, absolute-path, traversal, and unknown fields.

`critical_action_decision(action, task_id, approval, now)` is an approval
record validator, not an executor. Every critical action (external runtime
launch, network transport, credential access, destructive Git, merge, push,
or destructive cleanup) returns `deny_missing_approval` when no exact,
enabled, task-bound, unexpired record is supplied. A valid record returns
`operator_approval_recorded`; a separate admitted adapter still needs explicit
operator authorization to perform any effect.

The JSON-first operator flow is: project safe evidence, show exceptions in
`approval-queue`, record a human approval for a critical action, then pass the
record to a separately approved effectful adapter. No dashboard, UI, network
API, interactive fallback, or automatic approval is present in Phase G.
