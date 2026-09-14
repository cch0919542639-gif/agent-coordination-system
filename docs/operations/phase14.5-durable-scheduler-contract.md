# Durable Scheduler Contract

`scripts/durable_scheduler.py` is the sole task-card lifecycle writer for
the Phase C control plane. Connectors never move cards: they emit signed
envelopes, and only the scheduler validates them and applies one
revision-guarded transition per accepted message.

## Envelope

Every outbox/inbox record carries exactly the immutable fields
`message_id`, `idempotency_key`, `type`, `project_id`, `task_id`, `run_id`,
`attempt`, `lease_epoch`, `sender_agent_id`, `issued_at`, `expires_at`,
`context_snapshot_ref`, `context_snapshot_hash`, `payload_ref`,
`capability_token_ref`, and `auth_tag`. `message_id` is immutable,
`idempotency_key` is a hex digest unique per logical action, and a new
attempt increments `lease_epoch`. Message types are `dispatch`,
`acknowledge`, `heartbeat`, `submit`, and `cancel`.

## Scheduler Guarantees

- Authenticates every envelope with the scheduler-owned secret for its
  `sender_agent_id`: `auth_tag` is an HMAC over the canonical envelope
  data excluding the tag itself. Public reference equality on
  `sender_agent_id`/`capability_token_ref` alone never authenticates; a
  copied reference without a valid tag is denied as unauthenticated.
  Secrets never enter envelopes, delivery records, or events.
- Rejects expired, unauthenticated, duplicated, stale-epoch, and
  revision-conflicted messages with fail-closed denial categories.
- Applies at most one lifecycle transition per accepted message through
  the single scheduler-owned `TaskCardStore` (`{task_id}.json` holding
  `status` plus `revision`) and only when the caller-supplied expected
  revision matches the stored revision; a conflict yields a
  `reconciliation_required` incident projection without overwriting state.
- Persists each accepted delivery with a temporary-file plus atomic rename;
  rewriting a `message_id` with different bytes is refused.
- Appends only sanitized event projections (safe IDs, refs, hashes,
  decision, timestamp) under an exclusive lock with one `O_APPEND` write
  plus fsync; an interrupted write leaves a torn tail that is ignored on
  load and repaired on the next append. The feed rebuilds the derived run
  view via `rebuild_run_view()` and is never a second lifecycle authority.
- Restarts hydrate idempotency, epoch, and revision state from inbox files,
  the task-card store, plus events (healing the store forward when events
  are ahead), then replay pending outbox files: accepted dispatches are
  denied as duplicates, interrupted inbox-only commits complete exactly
  once, never re-applied.

## Sanitization

No envelope, delivery record, event, or snapshot stores credentials,
source bodies, prompts, transcripts, absolute paths, or raw runtime
output. References must be project-relative; hashes are hex digests.

## Non-Goals

No runtime launch, credential access, connector-grant creation, network
transport, Git mutation, merge, or push. Worktree provisioning, lease
timers, review bundling, and operator commands remain later Phase D–G
tasks.
