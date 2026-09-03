# Incident: OpenCode bootstrap runtime is not ready

- Incident ID: 20260903-01-opencode-bootstrap-probe-failed
- Task ID: phase14.5-bootstrap-01
- Phase: phase14.5-bootstrap-connector
- Agent: ORCHESTRATOR
- Severity: high
- Category: environment_failure
- Status: open
- Created At: 2026-09-03

## Summary

The local OpenCode candidate cannot yet receive the requested bootstrap task.

## Exact Blocker

The requested manual OpenCode bootstrap cannot start: its bounded runtime probe
returned the sanitized status `probe_failed`.

After the isolated worktree was provisioned and the operator explicitly
authorized the bounded B0 handoff, the direct OpenCode start attempt failed
before an agent session was created: Windows reported that the installed CLI
binary is not a valid application for this OS platform.

After the package entrypoint was repaired and an isolated temporary config root
was used, OpenCode started and read the assigned task and protocol files. Its
CLI version and startup diagnostic then succeeded. The session nevertheless
ended after its initial repository scan without claiming the task, writing a
progress report, changing code, or producing delivery evidence.

## Scope / Risk Impact

No OpenCode session, handoff activation, worktree creation, task-card
lifecycle transition, credential read, or network task execution was started.
Treating the generated dispatch text as delivered work would misrepresent the
task state.

## What Was Attempted

- Ran `python scripts/orchestrate.py runtime-preflight --runtime opencode --probe --json`.
- Provisioned the specified isolated worktree after operator authorization.
- Attempted the bounded `opencode run` B0 handoff after the operator explicitly
  authorized its transmission to the configured external model service.
- Repaired the locally installed OpenCode package entrypoint using its supplied
  postinstall script, then verified a version response through an isolated
  temporary config root.
- Started one bounded B0 OpenCode session. It read the task and protocol but
  ended without a task claim or repository delivery; no retry was started.
- Verified the repaired CLI version and startup diagnostic through the isolated
  config root. Did not inspect session logs, state, or transcripts because they
  may contain private task or provider data.

## Recommended Next Action

The OpenCode CLI entrypoint is repaired and the isolated worktree is
provisioned. Before any separately approved retry, inspect a privacy-bounded
diagnostic for why the started session ended before a task claim, or authorize
access to the relevant session diagnostics with an explicit redaction plan.

## Follow-up Diagnostic

The authorized redacted diagnostic found that the session predominantly waited
for tool-permission approval (525 classified prompt/request events). It did
not show an interactive-input requirement or a tool-execution failure. This is
consistent with a headless `opencode run` session being unable to answer its
own permission requests. A small number of provider/authentication-classified
events also occurred, but the session had already successfully performed its
initial repository reads.

## Safe Recovery Options

Use the OpenCode desktop UI to run B0 and approve only the task-scoped actions,
or define a separately reviewed, least-privilege project permission profile for
the isolated B0 worktree. Do not use the global `--auto` option: it would grant
broader approval than this one task allows.
