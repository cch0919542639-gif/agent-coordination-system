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

The run ID is consumed before spawn. Invalid, expired, consumed, cross-wired,
credential-bearing, or network-activating input returns a redacted denial
before spawn. No shell is requested. The child environment is an empty mapping;
no parent environment, credential-like variable, or user configuration root is
read, copied, logged, or returned.

## Completion and stop

The injected process is waited only for the approved bounded timeout. A timeout
calls only that process's `terminate_tree()` method. Results contain terminal
category, safe IDs, timeout, and the `best_effort` label—never executable,
argv, environment, raw output, prompts, source, credentials, or transcripts.

This module has no CLI or real spawn implementation. Tests use fake spawn and
fake process objects only. A future live call still needs a concrete one-shot
operator approval and the Phase H protocol; it cannot claim denied network
egress or any sandbox enforcement.
