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

The launch boundary materializes one enabled, unexpired, one-shot approval ID
from the exact current draft; a pre-filled ID is not approval evidence. It is bound to
`phase14.5-six-agent-pilot-08` and its exact run ID. It must name six distinct
registered local worker identities; the exact project-relative worktree root
and six allocated worktree references; fixed runtime/argv allowlist,
adapter/version, run-window start/end, timeout, stop authority, and expected
manifest/allocation digests. Unknown fields, malformed values, mismatched
run/task IDs, expired windows, duplicate identities, and unsafe references
deny the preflight.

The default approval must state that credential access, merge, push,
destructive cleanup, and network activation are not approved by this pilot.
The operator may enable one exact network/provider exception for the approved
run only: local OpenCode may use caller-supplied existing provider
configuration roots to contact its configured model service. The approval
contains only named environment keys, never values, credentials, or endpoints;
all other network and credential behavior remains prohibited. Each worker
record must exactly bind one approved agent ID to its corresponding worktree,
runtime/argv allowlist, timeout, and stop authority; missing, duplicate, or
cross-wired provenance denies. Every allocated worktree reference must be a
component-safe child of the declared worktree root; an independently safe but
cross-root path denies. Relative references reject `.` and `..` components at
every depth. Each binding declares a heartbeat interval, missed-heartbeat
threshold, and finite hard ceiling. The caller-driven supervisor checks the
matching child after a missed report, safely stops it, and returns one terminal
incident category without retry. Project context is only the allocated relative
worktree reference, never a provider configuration root. L1 evidence must
carry the `best_effort` label and show the fixed
runtime/argv, process-tree timeout/stop handling, and durable
scheduler/lease/review evidence. It is not evidence of enforced restricted
writes, independent OS process identity, or denied network egress.

L2 platform-enforced isolation is optional hardening, not an L1 prerequisite.
Only an L2 record may assert restricted writes, process identity, or denied
network egress, and it must independently verify each asserted property.
The existing accepted effectful adapter and connector provisioner are L2-only:
they require those attestations and cannot start an L1 worker. Until the
separately reviewed `phase14.5-local-control-adapter-12` is accepted, an L1
one-shot approval remains preflight evidence only and cannot enable a launch.

## Supervised acceptance procedure

1. Freeze reviewed allocations, context snapshots, manifests, approval, and
   review targets; verify hashes and expiry immediately before each launch
   boundary.
2. Run deterministic fake-clock evidence first: six lease identities, acknowledgement and heartbeat evidence, a fenced lease-expiry retry, and retry exhaustion that routes exactly one incident and approval-queue projection.
3. Only after `phase14.5-local-control-adapter-12`, the OpenCode executor,
   and the reviewed live runner are accepted and preflight passes, the
   separately approved local-control adapter may start at most the six approved
   workers in allocated worktrees. The live runner uses only its pinned
   PowerShell wrapper and must reject any request not exactly bound to identity,
   manifest, approval, worktree, fixed runtime/argv, timeout/stop handling, and
   run window. The shared pilot admission is consumed once; each of the six
   exact bindings is then fenced and consumed separately before its own launch.
   A duplicate, foreign, stale, or second-pilot request denies before a child
   boundary. Before those acceptances, do not launch.
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
