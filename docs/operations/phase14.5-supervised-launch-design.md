# Phase 14.5 Supervised One-Shot Launch Design

## Status And Boundary

This is a design-only companion to the frozen
`phase14.5-launcher-safety-contract.md`. It does not authorize, implement, or
invoke a runtime. It defines the inputs and terminal controls a later,
separately approved implementation must satisfy for one supervised pilot.

The only candidate remains the contract-bound OpenCode pilot:

| Binding | Required value |
| --- | --- |
| Runtime ID | `opencode` |
| Worker ID | `external-agent-platform-33` |
| Project ID | `agent-coordination-system` |
| Reviewer and rollback owner | `ORCHESTRATOR` |
| Worker branch | `agent/external-agent-platform-33/phase14.5-pilot-01` |
| Worker worktree reference | `worktrees/phase14.5-pilot-01` |

No other runtime, worker, project, branch, worktree, or retry policy is in
scope. The dry-run-only preflight remains the default behavior.

## Immutable Manifest Schema

An implementation may read one immutable manifest document only after it
passes schema, integrity, and binding validation. It must reject unknown
executable identities and must not obtain command data from task text,
environment variables, prompts, source files, or shell input.

| Field | Required rule |
| --- | --- |
| `manifest_id`, `manifest_digest` | Non-empty immutable identifiers; digest is verified before any decision. |
| `run_id`, `task_id`, `project_id`, `worker_id`, `reviewer_id`, `runtime_id` | Non-empty exact bindings; project, worker, reviewer, and runtime match the single pilot. |
| `branch`, `worktree_ref`, `inbox_payload_ref` | Exact provenance bindings; the implementation verifies them without emitting their raw values. |
| `executable_id` | Allowlisted identifier only; no path is stored or accepted in this design. |
| `argv` | Immutable array in a later approved manifest format only. This design deliberately defines no values, no executable, and no real argument list. |
| `mode` | `dry_run` by default; `supervised_one_shot` is eligible only after all approval gates pass. |
| `approval_ref`, `timeout_seconds` | Required for supervised mode; approval binds this manifest ID and timeout is an integer from 1 through 900. |
| `enabled` | Explicit boolean; false is terminal denial. |

The manifest is invalid if a required field is absent, malformed, altered,
unverifiable, mismatched, disabled, over its timeout limit, or contains a
shell string, unallowlisted executable identity, unapproved argv structure,
or extra arguments outside the later approved format.

## Approval Reference Schema

An approval reference is immutable and verifies authorization for exactly one
manifest. It contains only safe identifiers and timestamps:

| Field | Required rule |
| --- | --- |
| `approval_id`, `manifest_id`, `manifest_digest`, `run_id` | Exact equality with the manifest. |
| `approver_role` | Explicit operator authority recorded before execution. |
| `issued_at`, `expires_at` | Verifiable timestamps; expiry is checked before launch and cannot be extended in place. |
| `mode` | Exactly `supervised_one_shot`. |
| `enabled` | Explicit true value; false or absent denies the run. |

Approval never authorizes a different manifest, task, runtime, branch,
worktree, timeout, executable, or argument list. It is not reusable after a
terminal outcome.

## Fail-Closed State Machine

```text
receive immutable inputs
  -> validate manifest, inbox provenance, bindings, allowlist, and timeout
  -> dry_run_ready (default) OR terminal deny_*

supervised_one_shot requested
  -> validate exact non-expired approval and global enable state
  -> start-once eligibility only in a later approved implementation
  -> terminal completed OR stopped_*
```

Every failure is terminal for the matching `run_id`; there is no fallback
runtime, inferred command, automatic retry, or mutation of task lifecycle.
Before any later process creation, that implementation must recheck global
disable and stop-request state. It must associate any process group solely
with the matching `run_id`; stop or disable affects no other run.

Terminal categories are `deny_missing_manifest`, `deny_invalid_manifest`,
`deny_disabled`, `deny_inbox`, `deny_provenance_mismatch`,
`deny_worktree_mismatch`, `deny_allowlist`, `deny_approval`,
`stopped_timeout`, `stopped_nonzero_exit`, and `stopped_safety_signal`.

## Safe Audit And Incident Rules

Each decision records only `run_id`, manifest ID and digest, runtime ID, task
ID, worker ID, project ID, branch/worktree digest, decision category, exit
category, safe timestamps, timeout category, and safe artifact references.

Audit and incident records must exclude credentials, tokens, account IDs,
prompts, task bodies, source content, executable paths, argv values, runtime
output, error output, and session transcripts. An attempted unsafe audit field
is a terminal schema violation and must be redacted rather than stored.

Credential prompt, interactive request, monitor anomaly, timeout, non-zero
exit, global disable, or stop request requires one terminal incident category
and no retry. An implementation must stop the matching process group only;
this design does not define the mechanism.

## Deterministic Design Test Matrix

| Case | Required result | Process creation |
| --- | --- | --- |
| Missing, malformed, altered, or unverifiable manifest | `deny_missing_manifest` or `deny_invalid_manifest` | Never |
| Disabled manifest or global disable | `deny_disabled` | Never or stop matching run before start |
| Missing or malformed inbox | `deny_inbox` | Never |
| Mismatched worker, project, task, branch, or worktree | Provenance or worktree denial | Never |
| Unallowlisted runtime/executable or unsupported argv structure | `deny_allowlist` or invalid-manifest denial | Never |
| Dry run without supervised approval | `dry_run_ready` or `deny_approval` as applicable | Never |
| Missing, expired, altered, or mismatched approval | `deny_approval` | Never |
| Timeout, non-zero exit, credential prompt, or monitor anomaly | Matching `stopped_*` result and one incident category | Later implementation stops matching run; no retry |
| Unsafe audit field | Safe schema violation and redaction | Never continue |
| Exact fully bound supervised request | Eligible for a later separate implementation test only | Not authorized by this design |

## Preconditions For A Later Implementation Task

An implementation task may be opened only after all of the following are
separately recorded and accepted:

1. this design has independent review acceptance;
2. an operator gives one-shot approval for the exact immutable manifest;
3. the manifest-bound argv and allowlisted executable design receive separate
   approval without exposing its values in broad records;
4. a safe implementation, test, audit, incident, stop, and rollback plan is
   independently reviewed; and
5. the operator confirms the external runtime, provider, credential, and
   data-handling risk is acceptable for this single run.

Until then, the only permitted runtime-facing behavior is the existing
dry-run-only decision preflight. This document grants no launch permission.
