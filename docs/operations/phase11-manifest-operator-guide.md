# Phase 11 Manifest — Operator Guide

## Purpose

The `orchestrate manifest` command writes an immutable run manifest after
an operator has approved an execution wave. It bridges read-only planning
(`doctor` + `waves`) to later dispatch and worktree preparation.

## Quick Start

```bash
# 1. Diagnose environment
python scripts/orchestrate.py doctor

# 2. Propose waves
python scripts/orchestrate.py waves

# 3. Create manifest for approved tasks
python scripts/orchestrate.py manifest \
  --tasks task-a task-b \
  --owner my-agent \
  --reviewer ORCHESTRATOR

# 4. Optionally with profile
python scripts/orchestrate.py manifest \
  --tasks task-a task-b \
  --owner my-agent \
  --profile rental-rebuild
```

## What It Does

- Records repository identity (remote, SHA, branch)
- Records selected tasks and the full wave plan
- Records explicit owner, reviewer, and profile
- Records creation timestamp and command context
- Writes a JSON manifest to `coordination/manifests/`

## What It Does NOT Do

- Does **not** claim, dispatch, move, or edit task cards
- Does **not** create branches, worktrees, or commits
- Does **not** automatically select profiles or phases
- Does **not** overwrite existing manifests

## Manifest Schema

```json
{
  "manifest_id": "a1b2c3d4e5f6",
  "created_at": "2026-07-16T12:00:00Z",
  "repo": {
    "remote": "https://github.com/...",
    "sha": "abc123...",
    "branch": "main"
  },
  "wave": {
    "tasks": ["task-a", "task-b"],
    "waves": [["task-a"], ["task-b"]],
    "blocked": [],
    "errors": []
  },
  "tasks": [
    {
      "task_id": "task-a",
      "status": "READY",
      "owner": "UNASSIGNED",
      "reviewer": "ORCHESTRATOR",
      "phase": "...",
      "file": "coordination/task-board/ready/...",
      "dependencies": []
    }
  ],
  "owner": "my-agent",
  "reviewer": "ORCHESTRATOR",
  "profile": { "profile_name": "rental-rebuild", "path": "..." },
  "command_context": { "command": "orchestrate manifest", "args": {...} }
}
```

## Naming Convention

Manifest files: `YYYY-MM-DDTHH-MM-SS_<manifest-id>.json`

The `manifest_id` is either:
- Auto-generated (SHA256 of task IDs + owner + repo SHA, truncated to 12 chars)
- Explicit via `--manifest-id`

## Duplicate Protection

If a manifest with the same ID already exists, the command fails with an
error and does not overwrite. This ensures immutable evidence.

## Exit Codes

- **0**: manifest created successfully
- **1**: validation failure (unknown tasks, invalid profile, duplicate ID)

## Approval Boundary

```
orchestrate waves       → see what CAN run (read-only)
orchestrate manifest    → record WHAT the operator approved
orchestrate dispatch    → assign and send to workers
```

The manifest is the audit trail between planning and dispatch. It captures
the operator's decision but does not execute it.
