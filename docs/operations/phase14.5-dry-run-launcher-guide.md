# Phase 14.5 Dry-Run Launcher Preflight

`launcher-dry-run` reads JSON artifacts and returns a safe decision only. It
never starts a process, creates a manifest or inbox, or changes task state.

```powershell
python scripts/orchestrate.py launcher-dry-run --manifest-json manifest.json --inbox-json inbox.json
```

Only `dry_run_ready` permits later planning. Every `deny_*` or `stopped_*`
result is fail closed and must not retry automatically. It is not launch approval.
