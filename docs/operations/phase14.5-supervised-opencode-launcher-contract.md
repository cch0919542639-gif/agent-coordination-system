# Phase 14.5 B.1 Supervised OpenCode Launcher Contract

## Boundary

`scripts/supervised_opencode_launcher.py` accepts in-memory, immutable values.
It does not load files, resolve an executable, provide a CLI, access an
environment or credential store, write lifecycle records, or start a process
by itself. Its single effectful boundary is an injected process factory after
all checks have returned `launch_ready`; tests inject only fake processes.

The production caller is responsible for obtaining a separately recorded,
non-expired operator approval for the exact manifest immediately before it
supplies a local process factory. This code task does not authorize or perform
that pilot.

## Required Exact Bindings

The immutable manifest is digest-bound and contains only safe identifiers,
the fixed pilot provenance, an allowlisted `opencode` executable ID, an argv
array of one through eight safe opaque tokens, a timeout from 1 through 900
seconds, and `supervised_one_shot` mode. It rejects unknown or sensitive
fields, shell-like argument tokens, unallowlisted identities, altered digests,
and mismatched project, worker, reviewer, branch, or worktree values.
The admitted task must also exactly match the manifest's task ID, project,
worker owner, branch, and worktree; a same-capability but different task is a
terminal provenance denial.

The approval exactly binds manifest ID/digest and run ID, is enabled, has the
`ORCHESTRATOR` role, begins before the call, is at most five minutes old, and
is valid only within its issued/expiry window. The
grant is digest-bound, enabled, unrevoked, one-shot, deny-network, scoped to
the same worker/project/adapter/task class, and must pass the B admission
planner. A used run ID, capacity exhaustion, unfinished dependency, or prior
owner denies before the process factory is called.

## Outcomes And Data Handling

Only one factory call is possible per accepted run. Its bounded wait returns
`completed`, `stopped_timeout`, or `stopped_nonzero_exit`; timeout terminates
only that injected process. A factory or wait failure is `stopped_safety_signal`
and consumes the one-shot run without exposing its detail. There is no retry,
task-card mutation, Git action,
network operation, captured runtime output, or persisted transcript.

Every result is limited to safe IDs, digest, runtime ID, timeout, and terminal
category. It never returns argv, worktree value, executable path, environment,
credentials, task content, or process output.
An invalid manifest returns only its denial category and `dry_run`; none of its
unverified fields are echoed.

## Remaining Enforcement Gap

This is a policy and call-boundary implementation, not a Windows security
sandbox. Restricted filesystem writes, process identity, and denied network
egress require a later platform enforcement adapter and independent review.
