# Phase 14.5 External Runtime Launcher Safety Contract

## Status and scope

This is the frozen contract for the later dry-run launcher and a single
supervised pilot. It authorizes no runtime invocation. A launcher built from
this contract must default to dry run; a real invocation requires a separate,
one-shot operator approval recorded in an immutable run manifest.

The contract covers one prospective pilot only:

| Field | Bound value |
| --- | --- |
| Runtime | `opencode` |
| Worker | `external-agent-platform-33` |
| Project | this coordination repository |
| Reviewer / rollback owner | `ORCHESTRATOR` |
| Worker branch | `agent/external-agent-platform-33/phase14.5-pilot-01` |
| Worker worktree | `worktrees/phase14.5-pilot-01` |

This selection follows the approved bounded availability probe. It does not
prove credentials, model access, task execution, or permission to launch.

## Normative launcher rules

1. The launcher reads only an immutable manifest and the selected registered
   worker's safe inbox payload. It must reject missing, malformed, unsigned or
   unverifiable input; it must never infer a command from a task body, shell
   text, environment variable, prompt, or source file.
2. The manifest must bind one `run_id`, `task_id`, project identity, worker ID,
   reviewer, runtime ID, allowlisted executable ID, branch, worktree, inbox
   payload reference, approval reference, and a maximum timeout. Every bound
   value must match before dry run or launch.
3. Dry run is the default and emits only a deterministic decision record. Real
   launch requires `mode=supervised_one_shot`, a non-expired operator approval
   for the exact manifest ID, the `opencode` allowlist entry, and a timeout no
   greater than 900 seconds. No fallback runtime, repository, branch, or
   worktree is permitted.
4. Command data is an immutable argv array in the manifest, not a shell string.
   The launcher must invoke it without a shell and reject empty argv, shell
   metacharacter interpretation, unallowlisted executables, or extra arguments.
   This contract deliberately specifies no launch argv; Phase 14.5-04 must
   introduce one only with a separately approved manifest-bound design.
5. A disabled manifest, a global operator disable state, a stop request,
   non-zero exit, timeout, credential prompt signal, missing inbox, or monitor
   anomaly stops the run, records an incident category, and does not retry.
   Stop/disable must terminate only the process group associated with the
   matching `run_id`.
6. The launcher never claims, dispatches, submits, accepts, reassigns, merges,
   pushes, or edits task lifecycle state. The worker and reviewer retain those
   roles under the existing protocol.

## Required safe audit record

Each decision or attempted one-shot run records only: `run_id`, manifest ID and
digest, runtime ID, task ID, worker ID, project ID, branch/worktree digest,
decision category, exit category, timestamps, timeout category, and safe
artifact references. It must not record credentials, tokens, account IDs,
prompts, task bodies, source content, executable paths, argv values, runtime
output, error output, or session transcripts.

## Threat and residual-risk table

| Threat or failure | Required control | Reject / recovery behavior |
| --- | --- | --- |
| Task text or environment attempts to supply a command | Manifest-only argv and executable allowlist | Reject before process creation; audit `untrusted_command_input`; open incident. |
| Missing, altered, or mismatched manifest/inbox provenance | Immutable IDs and full binding comparison | Fail closed; no fallback lookup; audit safe mismatch category. |
| Wrong worker, project, branch, or worktree | Exact equality against manifest and registered worker | Reject; do not write an inbox or start a process. |
| Credential prompt or interactive request | Noninteractive execution policy and prompt detector | Stop matching process group; redact details; incident `credential_prompt`. |
| Timeout, non-zero exit, or monitor anomaly | One-shot timeout and monitored exit categories | Stop; record category; no automatic retry or busy loop. |
| Sensitive data in observability | Allowlisted audit schema and redaction tests | Drop unsafe field; treat schema violation as a failed run. |
| Operator error or unsafe rollout | Default dry run, explicit approval, global disable | Deny launch without exact approval; rollback owner disables future runs. |

Residual risk remains: a successful version probe does not establish provider
authorization or safe model behavior. This phase remains supervised and
single-worker until the later pilot and independent review provide evidence.

## Deterministic reject-path test matrix for Phase 14.5-03

| Case | Input condition | Expected deterministic outcome |
| --- | --- | --- |
| Missing manifest | No manifest reference | `deny_missing_manifest`; no process or inbox write. |
| Malformed manifest | Invalid schema, digest, or argv structure | `deny_invalid_manifest`; no process. |
| Disabled | Manifest or global disable state is false | `deny_disabled`; no process. |
| Missing/malformed inbox | Safe inbox artifact absent or invalid | `deny_inbox`; no process. |
| Wrong worker/project/task | Any identity differs from manifest | `deny_provenance_mismatch`; no process. |
| Wrong branch/worktree | Resolved location differs from binding | `deny_worktree_mismatch`; no process. |
| Unallowlisted runtime/executable | Runtime is not `opencode` or executable ID differs | `deny_allowlist`; no process. |
| No one-shot approval | Launch mode lacks exact approval reference | `deny_approval`; dry-run decision only. |
| Timeout | Bound timeout expires | `stopped_timeout`; terminate matching process group; incident. |
| Non-zero exit | Process reports non-zero | `stopped_nonzero_exit`; no retry; incident. |
| Credential prompt / monitor anomaly | Detector raises either signal | `stopped_safety_signal`; redact data; incident. |

Phase 14.5-03 must make every row executable as a deterministic test. It may
not add a path that starts a runtime.
