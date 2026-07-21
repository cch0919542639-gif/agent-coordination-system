#!/usr/bin/env python3
"""Fail-closed, dry-run-only launcher decision; it never starts a process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED = {
    "runtime": "opencode",
    "worker_id": "external-agent-platform-33",
    "project_id": "agent-coordination-system",
    "branch": "agent/external-agent-platform-33/phase14.5-pilot-01",
    "worktree": "worktrees/phase14.5-pilot-01",
}


def decide(manifest: object, inbox: object, *, disabled: bool = False) -> dict[str, object]:
    """Return a safe deterministic decision without reading commands or launching."""
    if not isinstance(manifest, dict):
        return {"decision": "deny_missing_manifest", "dry_run": True}
    if disabled or manifest.get("enabled") is False:
        return {"decision": "deny_disabled", "dry_run": True}
    signals = {"timeout": "stopped_timeout", "nonzero_exit": "stopped_nonzero_exit", "credential_prompt": "stopped_safety_signal", "monitor_anomaly": "stopped_safety_signal"}
    if manifest.get("safety_signal") in signals:
        return {"decision": signals[manifest["safety_signal"]], "dry_run": True}
    required = ("run_id", "task_id", "manifest_id", *EXPECTED)
    if any(not isinstance(manifest.get(key), str) or not manifest[key] for key in required):
        return {"decision": "deny_invalid_manifest", "dry_run": True}
    if not isinstance(inbox, dict) or not all(isinstance(inbox.get(key), str) and inbox[key] for key in ("worker_id", "task_id")):
        return {"decision": "deny_inbox", "dry_run": True}
    if any(manifest[key] != value for key, value in EXPECTED.items()):
        return {"decision": "deny_worktree_mismatch" if manifest.get("worktree") != EXPECTED["worktree"] else "deny_provenance_mismatch", "dry_run": True}
    if manifest.get("executable") != "opencode":
        return {"decision": "deny_allowlist", "dry_run": True}
    if manifest.get("mode") != "dry_run":
        return {"decision": "deny_approval", "dry_run": True}
    if inbox.get("worker_id") != manifest["worker_id"] or inbox.get("task_id") != manifest["task_id"]:
        return {"decision": "deny_provenance_mismatch", "dry_run": True}
    return {"decision": "dry_run_ready", "dry_run": True, "runtime": "opencode", "task_id": manifest["task_id"], "run_id": manifest["run_id"]}


def _load(path: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run-only launcher preflight; never launches a runtime.")
    parser.add_argument("--manifest-json", required=True)
    parser.add_argument("--inbox-json", required=True)
    parser.add_argument("--disabled", action="store_true")
    args = parser.parse_args()
    print(json.dumps(decide(_load(args.manifest_json), _load(args.inbox_json), disabled=args.disabled), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
