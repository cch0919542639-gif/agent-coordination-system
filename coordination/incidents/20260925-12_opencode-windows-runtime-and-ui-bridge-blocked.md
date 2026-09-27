# OpenCode Windows Runtime and UI Bridge Blocked

## 2026-09-27 correction (supersedes current-blocker claims below)

The installed 1.18.32 binary was a 479-byte postinstall-error stub. Running
the package's own postinstall repaired it; native `--version` returned 1.18.32
with exit zero and no stderr, and `serve --help` also returned zero. The earlier
EEXIST observation is not established as an intrinsic OpenCode version defect.

The supported native Windows bridge enumerated, activated and interacted with
OpenCode Desktop. The browser-only automation inventory was not evidence of a
broken native bridge. Correct worker-project selection remains unverified.

The historical Impact paragraph is overbroad: installation/postinstall and CLI
diagnostic process execution did occur. No successful six-worker pilot follows
from those actions. Task 46 now owns the API compatibility check; the historical
CLI/UI blocker is recovered, while actual integration is still incomplete.

Historical observations follow unchanged for traceability.

- Incident ID: `20260925-12_opencode-windows-runtime-and-ui-bridge-blocked`
- Task ID: `phase14.5-opencode-live-integration-46`
- Created At: `2026-09-25`
- Agent: `ORCHESTRATOR`
- Phase: `phase14.5-phase-h-live-pilot`
- Category: `capability_mismatch`
- Severity: high
- Status: active

## Summary

The six Task 43 children were not blocked primarily by headless permission
prompts. The installed Windows CLI had an unrun postinstall shim that exits
nonzero. Repairing it exposed a second native Windows `EEXIST` startup failure
on an existing OpenCode config directory. The Desktop application is now
installed, but this session's approved Windows UI bridge cannot enumerate or
launch it.

## What Was Attempted

- Before repair, `opencode-ai 1.18.31`'s `bin/opencode.exe` was a 479-byte
  postinstall-error script that explicitly exits `1`.
- The package postinstall was repaired, then the CLI was moved to official
  `1.18.30` without reading or deleting existing user configuration.
- The native binary reports `EEXIST` for
  `C:\\Users\\angel\\.config\\opencode`; read-only inspection confirms that
  target is an existing directory.
- OpenCode Desktop `1.18.32` was installed from its already-downloaded official
  updater into `C:\\Users\\angel\\AppData\\Local\\Programs\\@opencode-aidesktop`.
- The current computer-use inventory reports `apps: []`; its documented
  `cua.computer.launch_app` member is absent at runtime, preventing compliant
  application launch or binding.

## Scope / Risk Impact

No new pilot, approval materialization, provider access, credential read,
network request, server start, runtime launch, merge, push, or destructive
configuration action occurred during this diagnosis.

## Exact Blocker

Historical runtime/UI blockers are superseded by the dated correction above.
Current integration is not yet proven against the installed server API.

## Recommended Next Action

Keep the accepted Task 44/45 API-controller layers. Recover the Windows UI
bridge or a healthy OpenCode Server executable before creating a fresh live
pilot task. Do not use `--auto`, global permission rules, or a terminal retry
to mask this environment failure.
