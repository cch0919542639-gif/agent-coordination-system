# Phase 11 Operator Runbook — Cross-Machine Safety Flow

## Purpose

This runbook documents the complete Phase 11 preparation flow for dispatching
work to external agents. It covers every checkpoint, stop condition, recovery
action, and cleanup boundary.

## Prerequisites

- Python 3.12+ installed
- Git installed with `origin` remote configured
- Repository cloned at the correct location
- Task cards in `coordination/task-board/ready/`

## Complete Command Sequence

### Step 1: Diagnose Environment

```bash
python scripts/orchestrate.py doctor
```

**Expected**: All checks PASS. Exit code 0.

**If FAIL**: See Recovery section below.

### Step 2: Propose Execution Waves

```bash
python scripts/orchestrate.py waves
# or JSON output:
python scripts/orchestrate.py waves --json
```

**Expected**: Waves listed with ready tasks. Exit code 0.

**Stop condition**: If `errors` is non-empty, fix dependency issues before
proceeding. Do not dispatch tasks with unresolved graph errors.

### Step 3: Operator Approves Task Selection

Review the wave output. Choose which tasks to dispatch. This is a **manual
decision** — no command selects tasks automatically.

### Step 4: Create Immutable Manifest

```bash
python scripts/orchestrate.py manifest \
  --tasks <task-id-1> <task-id-2> \
  --owner <agent-name> \
  --reviewer ORCHESTRATOR
```

**Optional**: `--profile <profile-name>` if profile constraints apply.

**Expected**: Manifest written to `coordination/manifests/`. Exit code 0.

**Stop condition**: If manifest creation fails, do not proceed to worktree
provisioning.

### Step 5: Worktree Dry-Run

```bash
python scripts/orchestrate.py worktree \
  --manifest <manifest-id> \
  --task <task-id> \
  --worktree-root <approved-root> \
  --dry-run
```

**Expected**: All preflight checks PASS. Exit code 0. No files created.

**Stop condition**: If dry-run fails, fix the issue before provisioning.

### Step 6: Provision Worktree (Optional)

```bash
python scripts/orchestrate.py worktree \
  --manifest <manifest-id> \
  --task <task-id> \
  --worktree-root <approved-root>
```

**Expected**: Worktree created at `<approved-root>/worktrees/<task-id>`. Exit
code 0.

**This is the only step that creates filesystem artifacts.**

### Step 7: Send Dispatch Message (Manual)

```bash
python scripts/orchestrate.py dispatch \
  --task-id <task-id> \
  --owner <agent-name>
```

**This is a manual handoff.** The operator sends the dispatch message to the
external agent through the repo's coordination files. There is no autonomous
agent messaging.

### Step 8: Worker Claims and Delivers

The external agent:
1. Pulls the repo
2. Reads the task card
3. Moves task to `in_progress/`
4. Implements the change
5. Moves task to `review/`
6. Writes delivery evidence

### Step 9: Reviewer Accepts

The reviewer:
1. Reads the delivery report
2. Validates against acceptance criteria
3. Moves task to `done/`

## Checkpoints

| Step | Command | Expected Exit | Artifact |
|---|---|---|---|
| 1. Doctor | `orchestrate doctor` | 0 | Diagnostic report |
| 2. Waves | `orchestrate waves` | 0 | Wave proposal |
| 3. Approve | (manual) | — | Operator decision |
| 4. Manifest | `orchestrate manifest` | 0 | `coordination/manifests/*.json` |
| 5. Dry-run | `orchestrate worktree --dry-run` | 0 | Validation report |
| 6. Provision | `orchestrate worktree` | 0 | `worktrees/<task-id>/` |
| 7. Dispatch | `orchestrate dispatch` | 0 | Dispatch message |
| 8. Worker | (external agent) | — | Task in `review/` |
| 9. Review | (reviewer) | — | Task in `done/` |

## Stop Conditions

Stop and investigate if:

- Doctor reports FAIL on any required check
- Wave planner reports graph errors (cycles, missing deps)
- Manifest creation fails (duplicate ID, unknown task, invalid profile)
- Worktree dry-run fails (revision mismatch, path collision, unsafe path)
- Worktree provisioning fails (git error, permission denied)

**Never proceed to dispatch if any preparation step fails.**

## Recovery Actions

### Wrong Repository

```
Symptom: doctor FAIL on repository-root
Fix: cd to the correct clone, or re-clone from the correct URL
```

### Missing Runtime

```
Symptom: doctor FAIL on git-available or python-runtime
Fix: Install Git/Python, ensure they are on PATH
```

### Missing Task Reference

```
Symptom: doctor FAIL on task-reference, or manifest rejects unknown task
Fix: Verify task ID exists in coordination/task-board/ready/
```

### Invalid Dependency Graph

```
Symptom: waves reports errors (cycle, missing_dependency)
Fix: Resolve the dependency — complete the blocking task or remove the edge
```

### Duplicate Manifest

```
Symptom: manifest rejects ID with "already exists"
Fix: Use a different --manifest-id, or the manifest was already created
```

### Revision Mismatch

```
Symptom: worktree rejects manifest with "revision mismatch"
Fix: git pull to update HEAD, then recreate the manifest at the new revision
```

### Path Collision

```
Symptom: worktree rejects with "collision" or "already exists"
Fix: Remove the existing worktree manually, or choose a different root
```

### Unsafe Path

```
Symptom: worktree rejects with "path traversal"
Fix: Use an absolute path under the approved worktree root
```

## Cleanup

Worktrees are not automatically cleaned up. To remove:

```bash
# Remove a specific worktree
git worktree remove <path>

# Clean up stale tracking
git worktree prune

# Remove all test worktrees
rm -rf test-*/
```

To remove manifests:

```bash
rm coordination/manifests/*.json
```

## Cross-Machine Handoff

When dispatching to an external agent on a different machine:

1. The operator runs Steps 1–6 on the preparation machine
2. The manifest records the repo SHA — the worker must use the same revision
3. The worktree is local to the preparation machine — the worker clones fresh
4. The dispatch message is sent through the repo (coordination files), not
   through autonomous agent messaging
5. The worker pulls, reads the task card, and begins work

**There is no automatic agent launch, message sending, or remote provisioning.
All external-agent communication is manual through the repo.**

## What Phase 11 Does NOT Do

- Does not launch agents automatically
- Does not send messages to external agents
- Does not create remote branches or push commits
- Does not claim, dispatch, review, or merge tasks
- Does not clean up worktrees automatically
- Does not remap artifact paths or inherit profiles
- Does not provide dashboards, APIs, or hosted services
