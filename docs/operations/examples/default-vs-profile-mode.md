# Default Mode vs Profile-Driven Mode: Operator Guide

## Overview

This document compares how task dispatch and review work under two modes:

1. **Default Mode** — uses global coordination defaults, no project profile active
2. **Profile-Driven Mode** — a project profile overrides specific behaviors

> **Runtime Status**: Profile validation and `--profile` dispatch context ARE implemented. Profile-aware path remapping, auto-activation, and profile-specific task-card validation are NOT implemented — those remain future hooks or manual operator steps. Each section below marks what is currently supported vs manual.

The comparison is organized by operational phase.

---

## Pre-Dispatch: What the Lead Agent Must Read

### Default Mode

| Step | Action |
|------|--------|
| 1 | Read the task packet |
| 2 | Verify allowed_scope and forbidden_scope |
| 3 | Check task dependencies |
| 4 | Assign to available agent |

**No profile lookup required.** Global defaults apply.

### Profile-Driven Mode

| Step | Action | Runtime Support |
|------|--------|-----------------|
| 1 | Read the task packet | Manual |
| 2 | **Load the project profile via `--profile <name>`** | ✅ Script-supported — dispatch context includes name, description, defaults, naming, paths, worktree policy |
| 3 | Check profile's artifact_mapping for correct paths | Informational — paths are NOT remapped |
| 4 | Check profile's worktree_policy for execution mode | Informational — must pass `--execution-mode WORKTREE` explicitly |
| 5 | Check profile's branch_pr_policy for naming | Informational — must pass `--branch` explicitly |
| 6 | Verify worktree availability if WORKTREE mode | Manual |
| 7 | Assign with project-specific context (`--owner`, `--reviewer`, etc.) | ✅ Script-supported — all flags passed explicitly |

**Profile context is informational** — the operator must still set all explicit flags.

---

## Task Card Structure

### Default Mode

Front matter uses standard fields only:

```yaml
task_id: phase9-docs-01
phase: phase9-documentation
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
execution_mode: REPO_FIRST  # or omitted for default
```

No `branch`, `worktree_path`, or `machine_id` needed.

### Profile-Driven Mode

Front matter includes profile-specific fields:

```yaml
task_id: rental-rebuild-backend-03
phase: phase4-api
status: READY
owner: UNASSIGNED
reviewer: project-lead  # profile-defined role
execution_mode: WORKTREE  # profile default
branch: feat/rental-rebuild/rental-rebuild-backend-03-tenant-search
worktree_path: worktrees/rental-rebuild/rental-rebuild-backend-03
machine_id: dev-machine-01  # if required by profile
```

---

## Artifact Locations

### Default Mode (Currently Supported)

```
coordination/
  task-board/ready/
  task-board/in_progress/
  task-board/review/
  task-board/done/
  progress/external-agent-docs-01.md
  incidents/
  delivery/
  reviews/
```

### Profile-Driven Mode — Current State

> Profile-aware path remapping is NOT implemented. All coordination files use the default `coordination/` paths regardless of profile settings.

```
coordination/   # ← ALL files use default paths, even with a profile active
  task-board/ready/
  task-board/in_progress/
  task-board/review/
  task-board/done/
  progress/external-agent-XX.md   # ← NOT remapped to project-specific path
  incidents/
  delivery/
  reviews/
```

Profile `artifact_mapping` paths are documented in the dispatch message but are **manual conventions only**. The operator must place project-specific coordination files at the profile-defined paths by hand if needed.

---

## Worker Execution

### Default Mode

| Aspect | Behavior |
|--------|----------|
| Work location | Main worktree (repo root) |
| Branch | Optional, follows global convention |
| Scope | Global allowed_scope paths |
| Role | Free-form agent name |

### Profile-Driven Mode

| Aspect | Behavior |
|--------|----------|
| Work location | Dedicated worktree under project prefix — manual convention; operator sets `--worktree-path` explicitly |
| Branch | Follows project naming — manual convention; operator sets `--branch` explicitly |
| Scope | Project-specific allowed_scope paths (set on task card) |
| Role | Project-defined role names — manual convention; operator assigns via `--owner`/`--reviewer` explicitly |

---

## Progress Reporting

### Default Mode (Currently Supported)

File: `coordination/progress/<agent-name>.md`

```markdown
# Progress Report

- Agent: external-agent-docs-01
- Active Task: phase9-docs-01
- Phase: phase9-documentation
- Status: IN_PROGRESS
```

### Profile-Driven Mode — Not Yet Automated

> Profile-specific progress paths are NOT automated. All progress files go to `coordination/progress/` regardless of profile settings.

File: `coordination/progress/backend-engineer-01.md` (default path)

```markdown
# Progress Report

- Agent: backend-engineer-01
- Active Task: rental-rebuild-backend-03
- Phase: phase4-api
- Status: IN_PROGRESS
- Worktree: worktrees/rental-rebuild/rental-rebuild-backend-03
```

If the project requires progress files at a profile-specific path (e.g., `rental-rebuild/coordination/progress/`), the operator must place them there manually. Scripts do not remap paths.

---

## PR and Branch Naming

### Default Mode

Branch: `docs/phase9-docs-01-contributor-guide` (global convention)

PR title: `[phase9-docs-01] Contributor onboarding guide`

### Profile-Driven Mode

Branch: `feat/rental-rebuild/rental-rebuild-backend-03-tenant-search` (project convention)

PR title: `[rental-rebuild] [rental-rebuild-backend-03] Tenant search endpoint`

---

## Review Process

### Default Mode (Currently Supported)

Reviewer checks:

1. Standard task packet completeness
2. Scope compliance (global paths)
3. Validation passes
4. Delivery report if expected

Reviewer role: ORCHESTRATOR (global default)

**Script behavior** (`review_task.py`):
- `accepted` → task moves to `done/`
- `needs_fix` → status updated to `NEEDS_FIX`, stays in `review/`
- `reassign` → status updated to `REASSIGNED`, stays in `review/`
- `rejected` → status updated to `REJECTED`, stays in `review/`

### Profile-Driven Mode — Current State

> Profile-aware review routing is NOT implemented. `review_task.py` applies the same standard decisions regardless of profile. Profile-specific checks are manual reviewer steps.

Reviewer checks (manual steps marked with ✋):

1. Task packet + profile-specific fields (✋ manual check)
2. Scope compliance (default `coordination/` paths)
3. Worktree isolation (✋ manual check — not script-enforced)
4. Branch naming convention (✋ manual check — not script-enforced)
5. Project-specific tests pass (✋ manual step)
6. PR format compliance (✋ manual check)
7. Delivery report if expected

Reviewer role: set explicitly via `--reviewer` flag (not auto-populated from profile)

Script behavior (`review_task.py`): identical to default mode — no profile-aware routing.

---

## Decision Matrix

| Question | Default Mode | Profile-Driven Mode |
|----------|--------------|---------------------|
| Do I need to read a profile? | No | Yes (`--profile <name>` loads context into dispatch message) |
| Is the profile validated by `--profile`? | N/A | ❌ No — run `validate.ps1` separately |
| Does `--profile` auto-set fields? | N/A | ❌ No — informational only |
| Where are coordination files? | `coordination/` | `coordination/` (NOT remapped) |
| What execution mode? | REPO_FIRST | Must pass `--execution-mode` explicitly |
| How are branches named? | Global convention | Project convention (manual) |
| Who reviews? | ORCHESTRATOR | Set explicitly via `--reviewer` |
| What tests run? | Global suite | Project-specific suite (manual) |
| Do I need a worktree? | No | Usually yes (set manually) |

---

## Operator Quick Reference

### When to Use Default Mode

- Working on cross-project coordination docs
- Tasks that don't belong to a specific project
- Quick fixes that don't need project context

### When to Use Profile-Driven Mode

- Working on a project with an active profile
- Tasks requiring worktree isolation
- Projects with custom naming conventions
- Projects with specific reviewer routing

### How to Check if a Profile Should Be Used

1. Check `profiles/` for a profile matching your project (e.g., `rental-rebuild-profile.md`)
2. Verify the profile passes validation: `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1` (this is separate from `--profile`)
3. When dispatching, use `--profile <name>` to include profile context in the dispatch message
4. Profile context is informational — set all task fields explicitly via CLI flags
5. If no profile, use global defaults

> Note: `active: true/false` is a documented field but has no script-enforced effect. Profile activation is a manual operator decision — the operator chooses whether to pass `--profile` at dispatch time.

---

## Common Pitfalls

### Default Mode Mistakes

- Using profile-specific paths when no profile is active
- Setting WORKTREE mode without a worktree policy
- Referencing project-specific roles that don't exist

### Profile-Driven Mode Mistakes

- 🔴 **Assuming `--profile` auto-sets fields** — it does NOT. Owner, reviewer, execution_mode, branch, worktree_path, and machine_id must all be passed explicitly
- 🔴 **Assuming artifact paths are remapped** — all coordination files stay under `coordination/`. Profile `artifact_mapping` values are informational only
- 🔴 **Assuming profile activates automatically** — `active: true/false` has no script effect. The operator decides when to pass `--profile`
- 🔴 **Forgetting to set WORKTREE flags explicitly** — profile default_execution_mode is NOT auto-applied; pass `--execution-mode WORKTREE` at dispatch
- 🔴 **Using profile-defined reviewer name without passing `--reviewer`** — the profile does not set the reviewer field; pass it explicitly
