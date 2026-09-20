# Phase 14.5 L1 Local OpenCode Executor Contract

`scripts/local_opencode_executor.py` is a minimal, injected-spawn boundary for
the operator-selected local `opencode` executable. It is L1 `best_effort`
local control, not a sandbox or a network/filesystem/process-isolation claim.

## Preconditions

`run_opencode_once()` accepts only one current exact projection already
validated by the accepted L1 adapter and provisioner: one of six records,
its matching request, and the enabled unexpired one-shot approval for
`phase14.5-six-agent-pilot-08`. It accepts only `runtime_id: opencode`, maps
that ID to the reviewed local `opencode` binding, and passes only the approved
argv tokens to its injected spawn function.

The approval ID is materialized only at the immediate launch boundary from the
exact current draft and launch timestamp; a manually pre-filled ID or changed
record denies. One shared one-shot state contains both the exact pilot admission (run plus launch-time approval ID) and all six binding launch markers, so a binding fence cannot be reset independently. Each exact binding gets a separately fenced one-time launch marker. Invalid, expired, duplicate-binding, second-pilot, cross-wired,
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

## Non-secret launch projection

`local_opencode_launch_projection.py` is a pure, no-process preparation seam.
It validates a current six-binding approval draft against reviewed
manifest/allocation identities and returns only public binding/request
identities, a redacted approval draft, the named project-context key, and
launcher content identities. It never materializes an approval or launch ID,
emits argv values, raw locations, configuration, environment values, wrapper
content, credentials, prompts, output, or process identity. A later exact
operator packet must supply those immediate-boundary inputs without altering
this projection. The validator also requires the caller to supply the current
independently reviewed identity map; artifact self-consistency alone is not
provenance. The projection neither authorizes nor invokes a pilot.

## Reviewed live runner

`local_opencode_live_runner.py` is the separate, minimal L1 live seam. It
accepts the same already-validated request, approval, record set, and opaque
caller-supplied environment as the executor, plus the exact reviewed launcher
mapping. That mapping pins the system PowerShell executable, request
approval/run IDs, and an absolute `.ps1` input to the SHA-256 content digest
of the reviewed project-owned `scripts/opencode_pilot_wrapper.ps1`. Before
Popen, the runner checks that the sole local `opencode` command resolution has
the reviewed SHA-256 content identity. It passes that just-revalidated location
only as an internal wrapper parameter; the wrapper hashes exactly that supplied
location immediately before invocation and performs no command lookup. The
runner repeats both the wrapper and runtime checks immediately before Popen. A changed, missing,
oversized, malformed, nonmatching, or ambiguous binding denies without a
fallback or retry. The raw absolute input path, runtime path, wrapper source,
and runtime command never appear in a result or evidence record; invocation
remains only
`-NoProfile -NonInteractive -File` with no shell, inherited environment, or
output capture.

The runner consumes pilot admission through the executor before the first Popen call, then fences each exact binding independently.
On an approved timeout it invokes only the fixed task-tree termination command
for that child PID. Tests inject every Popen call. This is still `best_effort`
local control, not a sandbox or a claim of host enforcement.

After constrained Popen returns a currently live child with a valid internal
identity, the runner may emit a `phase14.5-start-v1` safe start attestation.
It contains only a deterministic exact-binding digest and monotonic launch
order. Its paired `phase14.5-concurrency-v1` projection contains only that
digest, order, overlap count, and prior active binding digests. It never
contains a PID, path, command, output, environment value, endpoint, or
credential. Popen failures and returned non-live children emit neither
projection. A caller shares the in-memory attestation state for the six
bindings of one pilot; no state is persisted or reused for another pilot.
