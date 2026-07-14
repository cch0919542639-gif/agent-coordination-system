# Local Python Runtime

## Purpose

This document defines the local Python runtime entrypoint for this repository on Windows machines where `python` or `py` may not be available directly in the current shell.

The goal is operational consistency:

- one known Python path
- one wrapper for arbitrary Python script execution
- one wrapper for coordination validation

## Current Python Runtime

Current known working path:

```text
C:\Users\angel\AppData\Local\Programs\Python\Python312\python.exe
```

This path should be treated as the preferred local runtime for this machine unless a future update replaces it.

## Recommended Entry Points

Prefer these repo wrappers over direct raw commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_python.ps1 scripts\orchestrate.py validate
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```

These wrappers are useful when:

- `python` is not in `PATH`
- `py` is present but does not resolve an installed runtime
- the shell environment changes across machines or sessions

## Direct Runtime Check

If you need to verify the runtime directly:

```powershell
& "C:\Users\angel\AppData\Local\Programs\Python\Python312\python.exe" --version
```

## Common Commands

Run coordination validation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```

Run orchestrate directly through the wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_python.ps1 scripts\orchestrate.py next
```

Run validator script directly through the wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_python.ps1 scripts\validate_coordination_files.py
```

## Failure Modes

### `python` not recognized

Use the wrapper scripts in `scripts/` instead of relying on `PATH`.

### `py` exists but says no installed Python found

This means the launcher is present but no usable runtime is registered for the current session. Use the fixed runtime path above or the wrapper scripts.

### Access denied from a restricted shell

If the current shell cannot execute the runtime directly, the orchestrator may need to run the wrapper or runtime through an elevated/approved command path.

## Maintenance Rule

If the Python installation path changes:

1. update `scripts/run_python.ps1`
2. update this document
3. verify `scripts/validate.ps1` still works

Do not assume that `python` in `PATH` is stable across all agent machines.
