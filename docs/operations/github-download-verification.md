# GitHub Download And Local Verification

## Download the integrated completion loop

The integration places the completion loop on the default `main` branch.
The original provider-tested publication remains available on
`codex/local-agent-completion-loop`; historical evidence names its exact source
commit. Credentials and machine runtime state remain local.

```powershell
git clone --branch main --single-branch https://github.com/cch0919542639-gif/agent-coordination-system.git
cd agent-coordination-system
```

## Prepare this computer

Install Git, PowerShell and Python 3.11+; this path was verified with Windows
and Python 3.12. OpenCode and Hermes must already be installed, reachable on PATH,
and configured with their providers. Hermes's SDK runner was verified onv0.19.1;
its Python must sit beside the installed Hermes executable. Provider credentials
remain local. No credentials, installs, schedules or recurring jobs are supplied
by a GitHub download. The examples use a process-only execution-policy bypass; no global policy is changed. Keep any existing automatic worker schedules disabled
during foreground runs.

`scripts/run_python.ps1` tries the explicit `COORDINATION_PYTHON` executable,
this checkout's `.venv/Scripts/python.exe`, PATH Python, then the Windows `py`
launcher. If automatic discovery fails, set your actual executable:

```powershell
$env:COORDINATION_PYTHON = 'C:\path\to\python.exe'
```

Create new local registrations and a finite three-worker demonstration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_python.ps1 scripts/prepare_local_loop.py --run-id download-check-01
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_python.ps1 scripts/orchestrate.py validate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/download-check-01.json
```

Preparation launches no worker or model. It registers this exact checkout,
two workers and required local routes under Git-ignored `coordination/monitor/`,
then writes new scoped READY cards and a pinned plan. Existing conflicting or
disabled registrations and duplicate run IDs fail without being replaced.
Other registrations are preserved. Never copy the original computer's ACKs,
inboxes, runtime state or credentials.

## Execute and verify

Reserve this checkout while the controller runs. The following command makes
bounded provider calls for the explicit finite plan:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/download-check-01.json --run
```

OpenCode intentionally submits6, receives needs_fix and repairs it to7.
Hermes reads7 and produces21. After independent receipt/scope/JSON checks,
the controller dispatches OpenCode to write the final completed artifact and
stops. Success requires exit0, all three cards in DONE with accepted reviews,
and the actual final JSON under `coordination/evidence/download-check-01/`.
Neither model narration nor a copied historical report counts as completion.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/download-check-01.json --run --resume
```

Replay checks the new run's original evidence and launches zero workers. For a
failed run, --resume preserves the same plan/ACK within its two-attempt limit;
provider failure, missing receipts or scope changes stop continuation. Do not
change attempts or delete state. After investigating an exhausted run, use a
fresh ID only when the cause has been fixed or provider capacity recovered.

## Verification scope

The publication report records the exact remote source commit, file equality,
focused tests and actual newly downloaded worker execution. This is a clean
GitHub clone tested on the same physical computer with installed runtimes and
existing providers. It verifies that GitHub code/data can recreate the local
loop; it does not claim a second physical computer or different OS was tested.
Model availability, quotas and local installation still affect execution.

General tasks need their own scoped cards and explicit acceptance checks. This
demonstration does not grant workers qualitative acceptance, merge authority,
unbounded queue draining or cross-machine task transport.

## Verified result (2026-10-12)

The fresh GitHub clone of source commit `ca7cdf1` passed97 focused tests and
completed the new OpenCode -> Hermes -> OpenCode chain. OpenCode automatically
repaired its first submission; Hermes required an explicit same-ACK retry after
a provider HTTP400, then was accepted and automatically triggered OpenCode's
final task. The controller stopped at COMPLETED, and replay launched zero
workers. All worker scope checks were clean. Exact source hashes, reports,
reviews and sanitized events are in `coordination/evidence/github-download-check-01/`.
Original runtime state and private transcripts were not published.
