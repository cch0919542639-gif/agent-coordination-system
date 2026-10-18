# Antigravity and Reasonix controlled workers

Antigravity and Reasonix now join the existing finite local controller. A task
selects either `structured_artifacts` (the compatibility default) or
`worker_execution: native_tools`. Native tasks use the provider's own file and
terminal tools to read, edit and execute an explicitly authorized Python test.
The runner submits REVIEW; the controller independently accepts and dispatches
the next dependency. Execution workers never accept, dispatch, merge or push.

## Prerequisites

Use the existing [download/bootstrap guide](github-download-verification.md) for
Python, OpenCode and Hermes. Install and authenticate `agy`, `reasonix` and
`node` on PATH using your own provider configuration. The Reasonix adapter
expects the npm installation's `node_modules/reasonix/bin/reasonix.js` beside
its executable shim. Provider credentials stay outside this repository.

Native tool traces were tested on Windows with agy 1.4.2 and Reasonix 2.43.0.
The Antigravity model defaults to `gemini-3.8-flash-low`; override it with
`COORDINATION_ANTIGRAVITY_MODEL`. Reasonix uses its existing configuration.
These CLIs and configured model access are separate installation prerequisites.

## Prepare, preview and execute

Run from the repository root, with a fresh run ID:

```powershell
.\scripts\run_python.ps1 scripts/prepare_native_tools_loop.py --run-id native-demo-01
.\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/native-demo-01.json
.\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/native-demo-01.json --run
```

Preparation launches no models. Execution follows OpenCode -> Hermes ->
Antigravity -> Reasonix -> OpenCode. Antigravity and Reasonix repair seeded
Python functions and execute pinned pytest checks; the expected result is 44.
To resume the same bounded plan, add `--resume` to the execution command.
Completed replay starts no workers. To prepare the compatibility manifest
example, use `scripts/prepare_four_agent_loop.py` instead. The original
`prepare_local_loop.py` still defaults to only OpenCode and Hermes.

The new PowerShell launchers require `-Run -ResumePayload <exact ACK>`; direct
invocations cannot select another task. Use controller-issued payloads only.

## Contract and acceptance

Native task cards require explicit `external_processing_authorized: true`,
`native_tool_contract`, `native_tool_contract_sha256`, `native_tool_evidence`
and the existing owner, ACK, allowed/forbidden scopes and LOCAL_LOOP checks.
The reviewer-owned JSON contract declares `read_paths`, `artifacts`, and
`commands`. Each command has an argv beginning with `$PYTHON` and hash-pinned
test sources that the worker cannot edit. One to ten plain argv commands are
allowed; shell composition, substitution and redirects are rejected. Paths
containing spaces are currently unsupported by the plain-token command grant.

Acceptance requires observed successful native reads, edits and every exact
test command after the last edit, unchanged test/contract hashes, scoped
artifact hashes and canonical REVIEW receipts. Narration and CLI exit zero
alone cannot pass. Antigravity's current stream parser recognizes pytest
success summaries; general shell/build commands require a separately tested
parser and contract extension. Logs retain sanitized tool provenance rather
than prompts or file contents.

Reasonix uses session grants and `--permission-mode dontAsk`. Antigravity
temporarily adds exact file/command grants while retaining existing deny/ask
rules and holding a per-user lock. Original settings bytes are restored on
normal exit; concurrent settings edits are preserved while the runner removes
its own grants. A private crash-recovery lease remains beside user settings
if a process dies. The next worker recovers it, or use:

```powershell
.\scripts\run_python.ps1 scripts/recover_native_permissions.py
```

Recovery refuses an active lock and launches no model. Never commit or share
the private lease: it contains the original settings snapshot. Provider tool
permissions and post-run scope checks are not an operating-system sandbox.
No schedules are enabled by this change. Product tasks still need explicit
scope, inputs, checks, permissions and finite limits from the orchestrator.

## Verification scope

The local Windows provider trial completed all five stages with accepted DONE
receipts and empty scope violations. Reasonix required one bounded retry after
attempting an extra command. Both providers denied a separate unapproved
sentinel command; neither sentinel was created. Completed replay launched zero
workers. Machine-specific receipts, raw runtime data, provider settings and
local OpenCode/Hermes compatibility changes are deliberately excluded from
this publication. Those live trial results are distinct from the isolated
publication regression results recorded in PROGRESS.md.
