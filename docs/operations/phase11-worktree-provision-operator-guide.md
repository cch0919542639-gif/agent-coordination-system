# Phase 11 Worktree Provision — Operator Guide

## Purpose

The `orchestrate worktree` command preflights and optionally provisions a
local Git worktree from an immutable run manifest. It bridges manifest
approval to isolated worker environments.

## Quick Start

```bash
# 1. Dry-run: validate everything, create nothing
python scripts/orchestrate.py worktree \
  --manifest <manifest-id> \
  --task <task-id> \
  --worktree-root /path/to/worktrees \
  --dry-run

# 2. Provision: create the worktree after preflight passes
python scripts/orchestrate.py worktree \
  --manifest <manifest-id> \
  --task <task-id> \
  --worktree-root /path/to/worktrees
```

## What It Does

- Validates manifest exists and has required fields
- Validates task is in the manifest's task list
- Validates repo revision matches (manifest SHA == current HEAD)
- Validates worktree path is safe (no traversal outside approved root)
- Detects existing path collisions
- Checks machine affinity when declared
- In non-dry-run: creates one local Git worktree (detached HEAD)

## What It Does NOT Do

- Does **not** claim, dispatch, push, or create remote branches
- Does **not** change task-card lifecycle or assignments
- Does **not** automatically select profiles or phases
- Does **not** implement automatic cleanup

## Arguments

| Argument | Required | Description |
|---|---|---|
| `--manifest` | Yes | Manifest ID or explicit file path |
| `--task` | Yes | Task ID to provision |
| `--worktree-root` | No | Approved root directory (default: repo root) |
| `--machine-id` | No | Machine identifier for affinity checks |
| `--dry-run` | No | Validate only, create nothing |
| `--json` | No | Output as JSON |

## Exit Codes

- **0**: preflight passed (dry-run) or worktree provisioned
- **1**: validation failure

## Preflight Checks

| Check | Description |
|---|---|
| Manifest structure | Required fields present |
| Task in manifest | Task ID exists in manifest's task list |
| Revision match | Manifest SHA == current HEAD |
| Path safety | Worktree path under approved root, no traversal |
| No collision | Target path does not already exist |
| Machine affinity | Matches when declared |

## Cleanup

Worktrees are not automatically cleaned up. To remove a provisioned worktree:

```bash
git worktree remove <path>
git worktree prune  # clean up stale tracking
```

## Approval Boundary

```
orchestrate waves       → see what CAN run (read-only)
orchestrate manifest    → record WHAT the operator approved
orchestrate worktree    → prepare WHERE the worker operates
orchestrate dispatch    → assign and send to workers
```

The worktree is the isolated checkout. Dispatch is still a separate step.
