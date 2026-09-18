# Phase 14.5 L1 Local OpenCode Executor Contract

`scripts/local_opencode_executor.py` is a minimal, injected-spawn boundary for
the operator-selected local `opencode` executable. It is L1 `best_effort`
local control, not a sandbox or a network/filesystem/process-isolation claim.

## Preconditions

`run_opencode_once()` accepts only one current exact projection already
validated by the accepted L1 adapter and provisioner: one of six records,
its matching request, and the enabled unexpired one-shot approval for
`phase14.5-six-agent-pilot-08`. It accepts only `runtime_id: opencode`, maps
that ID to the fixed local executable `opencode.exe`, and passes only the
approved argv tokens to its injected spawn function.

The approval ID is materialized only at the immediate launch boundary from the
exact current draft and launch timestamp; a manually pre-filled ID or changed
record denies. The run ID is consumed before spawn. Invalid, expired, consumed, cross-wired,
credential-bearing, or network-activating input returns a redacted denial
before spawn. No shell is requested. The default child environment is empty.
Only an enabled, exact `network_provider_exception` can pass the one supplied
project-context mapping: `OPENCODE_PROJECT_WORKTREE` exactly equals the
allocated relative worktree reference. No arbitrary provider/configuration
root is forwarded. It is never read from the host, serialized, returned,
logged, or persisted. Cross-wired, absolute, traversal, or unknown input
denies before spawn.

## Completion and stop

The injected process is waited only for the approved bounded timeout. A timeout
calls only that process's `terminate_tree()` method. Results contain terminal
category, safe IDs, timeout, and the `best_effort` label—never executable,
argv, environment, raw output, prompts, source, credentials, or transcripts.

The boundary also supports a finite caller-driven lease check loop: each
binding declares heartbeat interval, missed-heartbeat threshold, and hard
ceiling. A missed heartbeat checks the matching child, terminates it, and
returns one terminal safety category; it never retries by another route.

This module has no CLI or real spawn implementation. Tests use fake spawn and
fake process objects only. A future live call still needs a concrete one-shot
operator approval and the Phase H protocol; it cannot claim denied network
egress or any sandbox enforcement.

## Reviewed live runner

`local_opencode_live_runner.py` is the separate, minimal L1 live seam. It
accepts the same already-validated request, approval, record set, and opaque
caller-supplied environment as the executor, plus the exact reviewed launcher
mapping. That mapping pins the system PowerShell executable, request
approval/run IDs, and its absolute OpenCode `.ps1` input against one opaque
SHA-256 wrapper-path digest. The raw wrapper path is not held in source; it
invokes only `-NoProfile -NonInteractive -File` with the approved argv, no
shell, no inherited environment, and no output capture. The absolute launcher
path is input-only and never appears in a result or evidence record.

The runner consumes the run through the executor before the first Popen call.
On an approved timeout it invokes only the fixed task-tree termination command
for that child PID. Tests inject every Popen call. This is still `best_effort`
local control, not a sandbox or a claim of host enforcement.
