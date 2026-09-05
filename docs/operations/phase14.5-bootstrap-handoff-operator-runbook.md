# Phase 14.5 Bootstrap Handoff Operator Runbook

## Purpose

This runbook describes the manual, operator-invoked steps to produce one
bounded, immutable, single-use task-context envelope for a manually started
OpenCode worker.  The bootstrap handoff does not launch a runtime and does not
authorise an automatic retry.

## Prerequisites

- The approved task card `phase14.5-bootstrap-01` is in `in_progress/` and its
  dependency `phase14.5-architecture-01` is accepted.
- The operator has verified that the OpenCode runtime is available and that a
  one-shot manual invocation is intended.
- A worktree provisioned at the project-relative reference
  `worktrees/external-agent-platform-33/phase14.5-bootstrap-01`.

## Step 1: Prepare the Operator Approval Record

Create an in-memory or file-backed JSON approval record with the following
fields:

| Field | Rule |
| --- | --- |
| `approval_id` | Unique identifier for this one-shot approval. |
| `task_id` | Must exactly match the task card: `phase14.5-bootstrap-01`. |
| `worker_id` | Must exactly match the worker: `external-agent-platform-33`. |
| `worktree_ref` | Project-relative worktree path. |
| `issued_at` | ISO-8601 timestamp with timezone; the approval is not valid before this time. |
| `expires_at` | ISO-8601 timestamp with timezone; the approval is not valid at or after this time. |
| `approver_role` | Must be `ORCHESTRATOR`. |
| `one_shot` | Must be `true`. |
| `enabled` | Must be `true`. |

The approval record is not a connector grant.  It does not authorise a runtime
launch by itself.

## Step 2: Prepare the Task Card Projection

Provide the task card front matter as a JSON object with only the allowlisted
fields: `task_id`, `phase`, `status`, `owner`, `reviewer`, `priority`,
`dependencies`, `allowed_scope`, `forbidden_scope`, `acceptance`.  No
credentials, prompts, source bodies, or raw logs are included.

## Step 3: Generate the Handoff Envelope

Call `build_handoff()` from `scripts/bootstrap_handoff.py` with the approval
record, task card projection, and project-relative worktree reference:

```python
from bootstrap_handoff import build_handoff

result = build_handoff(
    approval=approval_record,
    task_card=task_card_projection,
    worktree_ref="worktrees/external-agent-platform-33/phase14.5-bootstrap-01",
    now=current_time,
)
```

If the decision is `handoff_prepared`, the envelope is safe to supply to the
manually started OpenCode worker.  Any other decision is terminal; do not retry.

## Step 4: Manually Start the OpenCode Runtime

The operator, not this module, starts the OpenCode runtime.  Supply the
handoff envelope (or its safe reference) to the worker session.  The envelope
is not a credential and must not be stored in Git.

## Step 5: Worker Submits Repository Evidence

After the worker completes its task, the operator or the worker submits
repository evidence for review following the standard task lifecycle.  No
automatic retry, merge, or push is performed by this handoff module.

## Terminal Denial Categories

| Category | Meaning |
| --- | --- |
| `deny_missing_approval` | The approval record is absent or not a mapping. |
| `deny_invalid_approval` | Required fields are missing, the approver role is wrong, or one-shot/enabled flags are not set. |
| `deny_disabled` | The approval is explicitly disabled. |
| `deny_approval_expired` | The current time is outside the issued_at/expires_at window. |
| `deny_task_mismatch` | The task ID in the approval does not match the task card. |
| `deny_worktree_mismatch` | The worktree reference does not match the approval. |
| `deny_unsafe_path` | A project-relative path contains `..`, starts with `/`, or starts with `./`. |
| `deny_replay` | The idempotency key has already been consumed in this session. |
| `deny_invalid_task` | The task card projection is missing or lacks a task_id. |

## Safety Guarantees

- No code path in `bootstrap_handoff.py` calls a process, shell, network API,
  credential store, or Git command.
- No code path creates files, directories, or modifies task-card state.
- The handoff envelope contains only safe identifiers, digests, and
  project-relative paths.
- Every denial is terminal; no fallback delivery or automatic retry is provided.

## Related Documents

- `docs/architecture/controlled-orchestration-architecture.md`
- `docs/operations/phase14.5-supervised-launch-design.md`
- `docs/operations/phase14.5-launcher-safety-contract.md`
- `docs/operations/agent-task-execution-protocol.md`
