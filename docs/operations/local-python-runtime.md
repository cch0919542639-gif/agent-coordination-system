# Local Python Runtime

The coordination engine needs Python3.11+ on Windows. `run_python.ps1` and both
controlled-worker prompts use `Get-CoordinationPython` from resolve-python.ps1.
Resolution order is explicit COORDINATION_PYTHON, this checkout's
.venv/Scripts/python.exe, PATH Python, then the Windows py launcher. A supplied
override must exist and meet the version requirement; it never silently falls
back to another interpreter. No account-specific runtime path is required.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_python.ps1 scripts/orchestrate.py validate
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1
```

The execution-policy override is process-only. To select a specific installed
Python, set COORDINATION_PYTHON to its actual executable for this shell. The
repo wrapper changes no installation, credentials or global configuration.
Hermes's SDK uses its own installed Python beside the Hermes executable;
the controller/lifecycle helpers use the resolved coordination runtime.

If discovery fails, install Python3.11+ or set the explicit executable path.
Do not assume a PATH alias or launcher has a usable interpreter. Confirm the
selected runtime before a model run; the wrapper reports a missing or older
runtime instead of dispatching work. Provider/agent prerequisites are in
[the download guide](github-download-verification.md).
