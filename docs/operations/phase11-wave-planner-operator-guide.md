# Phase 11 Wave Planner — Operator Guide

## Purpose

The `orchestrate waves` command proposes deterministic execution waves from
task-card dependencies without changing any task card or assignment.

## Quick Start

```bash
python scripts/orchestrate.py waves
python scripts/orchestrate.py waves --json
```

## What It Does

1. Scans all task cards across `task-board/{ready,in_progress,review,blocked,done}/`
2. Builds a dependency graph from each task's `dependencies` field
3. Detects missing dependencies, cycles, and tasks blocked by unfinished work
4. Proposes waves: wave 0 = no unsatisfied deps, wave 1 = deps on wave 0, etc.
5. Reports blocked tasks with actionable diagnostics

## What It Does NOT Do

- Does **not** claim, dispatch, move, or edit task cards
- Does **not** create run manifests, worktrees, or branches
- Does **not** automatically select profiles or phases
- Does **not** require network access

## Output Interpretation

### Human Output

```
  Execution Waves
  Wave 0: task-a, task-b       # can run immediately
  Wave 1: task-c               # depends on task-a or task-b
  Wave 2: task-d               # depends on task-c

  Blocked Tasks
  task-e [state=ready] — waiting on: task-f (in_progress)
```

### JSON Output (`--json`)

```json
{
  "waves": [["task-a", "task-b"], ["task-c"], ["task-d"]],
  "ready": ["task-a", "task-b"],
  "blocked": ["task-e"],
  "errors": [],
  "stats": {"total": 5, "ready": 2, "blocked": 1, "error_count": 0}
}
```

## Exit Codes

- **0**: no graph errors (cycles, missing deps)
- **1**: one or more graph errors detected

## Dependency Satisfaction

A dependency is satisfied when the referenced task exists in `task-board/done/`.

| Dep state | Status |
|---|---|
| `done/` | Satisfied |
| `ready/` | Plannable (later wave) |
| `in_progress/`, `review/`, `blocked/` | Blocked (unfinished) |
| Missing from task board | Error (missing dependency) |

## Filtering

All filtering is explicit. The command does not automatically select profiles
or phases — it scans every task card in the board.

## Boundary Between Planning and Dispatch

The wave planner **proposes** but never **claims**. After reviewing the wave
proposal, the lead agent uses `orchestrate dispatch` to assign tasks.

```
orchestrate waves          → see what can run
orchestrate dispatch ...   → assign and send
```
