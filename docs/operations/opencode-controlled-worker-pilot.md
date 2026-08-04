# OpenCode Controlled-Worker Pilot

## Scope

OpenCode is an explicitly launched, local worker runtime. It reuses the
repository's owner-strict `worker activate --json` handoff and does not use
OpenCode as a second task board or dispatcher.

## Runtime Isolation

The global OpenCode config directory currently fails OpenCode initialization
when it already exists. The controlled launcher sets `XDG_CONFIG_HOME` to the
local, Git-ignored runtime directory `coordination/monitor/runtime/opencode`.
It does not delete, move, or change `C:\Users\angel\.config\opencode`.

## Commands

Verify only, without a model call:

```powershell
.\integrations\opencode-coordination-worker\run-controlled-worker.ps1
```

Run one supervised task only after explicit user authorization for that task's
model data transfer:

```powershell
.\integrations\opencode-coordination-worker\run-controlled-worker.ps1 -Run
```

The `-Run` path activates exactly one delivery for
`opencode-coordination-pilot`. It stops when none is eligible; otherwise it
may claim and submit exactly that one assigned task for repository review.
It never enables `--auto`, accepts, reviews, merges, commits, pushes, starts
another agent, or selects an unassigned task.

The default model is OpenCode's built-in
`opencode/deepseek-v4-flash-free`. Before `-Run`, an operator must make the
required runtime credential available without recording it in this repository.

## Rollback

Do not invoke `-Run`. To remove setup-only state, delete the launcher and the
Git-ignored local runtime directory after verifying their paths. This does not
alter task cards or the global OpenCode config directory.

## Windows Task Scheduler Policy

The native wake-up mechanism is the Windows task `OpenCode Controlled Worker`.
It runs the controlled launcher every 10 minutes as the interactive `angel`
user. It is currently **Disabled** after the supervised test. When enabled,
each invocation may handle at most one pending `ready_assigned` delivery for
`opencode-coordination-pilot`, with no retry, auto-approval, or lifecycle
authority. Disable the task to stop future polling; ending an in-flight task
does not alter task cards or OpenCode configuration.
