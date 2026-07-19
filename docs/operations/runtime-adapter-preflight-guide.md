# OpenCode and MiMo Runtime-Adapter Preflight

## Purpose

This command reports whether the optional OpenCode and MiMo CLI names are
discoverable on PATH. It prepares no agent session and does not change either
runtime's configuration, the task board, delivery state, Git state, or network
state.

```powershell
python scripts/orchestrate.py runtime-preflight --json
python scripts/orchestrate.py runtime-preflight --runtime mimo --worker-id external-agent-platform-33
```

The output status is one of `unavailable`, `discoverable_unverified`,
`available`, or `probe_failed`. The default is `discoverable_unverified` even
when a command is found, because discovery does not prove configuration,
credentials, or a healthy runtime.

## Optional Probe

Use `--probe` only during supervised diagnosis. It invokes `<command>
--version` with a fifteen-second timeout and retains only the safe category; on
Windows it invokes the resolved CLI wrapper through a noninteractive,
no-profile PowerShell host so a discovered `.cmd` wrapper such as MiMo's can
be checked correctly. It
does not print a path, version text, configuration, prompt, or error output.

This is the sole exception to the default discovery-only boundary: it may
execute the already-discovered runtime executable with the fixed `--version`
argument. It is not a session launch, and it must not be represented as proof
of credentials, model access, task execution, or launch readiness.

```powershell
python scripts/orchestrate.py runtime-preflight --runtime opencode --probe
```

## Handoff Boundary

The adapter never invokes `opencode run`, `opencode serve`, or an unparameterized
`mimo` command. Except for the explicit bounded `mimo --version` probe above,
the only supported same-machine handoff remains the owner-strict bounded poll:

```powershell
python scripts/orchestrate.py worker activate <worker-id> --json
```

An already-running runtime may consume that durable local handoff and then
independently follow the task protocol. Starting an external agent is an
explicit operator action, not a side effect of preflight or activation.

## Disable and Rollback

Do not invoke `runtime-preflight`; no background process, registry entry, or
runtime setting is created. Removing this optional CLI entry and its tests
fully reverts the integration without touching OpenCode or MiMo installations.
