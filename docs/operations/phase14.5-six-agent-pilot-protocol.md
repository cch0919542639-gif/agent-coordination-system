# Phase 14.5 Supervised Six-Agent Pilot Protocol

## Purpose and boundary

This protocol is the Phase H acceptance procedure for the architecture's L1
Six-Agent Acceptance Scenario. L1 is `best_effort` local controlled
collaboration, not a security sandbox. This protocol is a preflight and
evidence procedure, not a runtime launcher. It does not authorize or perform
connector launch, credential access, network activation, Git worktree
provisioning, merge, push, or cleanup.

The live pilot is fail-closed. It may begin only when every preflight input below is recorded, current, and independently checkable. Missing or unverifiable evidence produces an incident and ends the attempt; it is never replaced by a mock, a second route, or an interactive fallback.

## Exact approval preflight

The operator must record one enabled, unexpired, one-shot approval bound to
`phase14.5-six-agent-pilot-08` and its exact run ID. It must name six distinct
registered local worker identities; the exact project-relative worktree root
and six allocated worktree references; fixed runtime/argv allowlist,
adapter/version, run-window start/end, timeout, stop authority, and expected
manifest/allocation digests. Unknown fields, malformed values, mismatched
run/task IDs, expired windows, duplicate identities, and unsafe references
deny the preflight.

The approval must state that credential access, merge, push, destructive
cleanup, and network activation are not approved by this pilot. Each worker
record must exactly bind one approved agent ID to its corresponding worktree,
runtime/argv allowlist, timeout, and stop authority; missing, duplicate, or
cross-wired provenance denies. Every allocated worktree reference must be a
component-safe child of the declared worktree root; an independently safe but
cross-root path denies. Relative references reject `.` and `..` components at
every depth. L1 evidence must carry the `best_effort` label and show the fixed
runtime/argv, process-tree timeout/stop handling, and durable
scheduler/lease/review evidence. It is not evidence of enforced restricted
writes, independent OS process identity, or denied network egress.

L2 platform-enforced isolation is optional hardening, not an L1 prerequisite.
Only an L2 record may assert restricted writes, process identity, or denied
network egress, and it must independently verify each asserted property.

## Supervised acceptance procedure

1. Freeze reviewed allocations, context snapshots, manifests, approval, and
   review targets; verify hashes and expiry immediately before each launch
   boundary.
2. Run deterministic fake-clock evidence first: six lease identities, acknowledgement and heartbeat evidence, a fenced lease-expiry retry, and retry exhaustion that routes exactly one incident and approval-queue projection.
3. Only after preflight passes, a separately approved local-control adapter may
   start at most the six approved workers in allocated worktrees. It must reject
   any request not exactly bound to identity, manifest, approval, worktree,
   fixed runtime/argv, timeout/stop handling, and run window.
4. Collect safe references only: dispatch, acknowledgement, lease, review-queue, incident, validation, and delivery. Never record prompts, source bodies, credentials, raw logs, transcripts, or absolute paths.
5. Verify all seven architecture conditions: eight-task mixed graph; worker
   context/acknowledgement/lease/review evidence; one dependency unlock;
   bounded restart and expiry recovery; review queued with merge/push blocked;
   restart-safe non-duplicate dispatch; and six actual registered local workers
   with `best_effort` local-control evidence.
6. Send evidence to an independent reviewer. Review submission is not acceptance and cannot merge or push.

## Current gate

No real pilot has run. Phase H remains at the L1 preflight gate until a
concrete one-shot approval, six real registered local workers, and supervised
run evidence exist. L1 does not claim an enforced filesystem or network
boundary. L2 remains optional; it requires separate platform enforcement
evidence before making any such claim.
