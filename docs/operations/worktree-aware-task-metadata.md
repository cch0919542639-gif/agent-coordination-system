# Worktree-Aware Task Metadata

## Purpose

This document defines the optional task metadata used when a task opts into worktree-aware execution.

The goal is to let the coordination system attach branch and worktree provenance to a task without breaking the existing repo-first workflow.

## Design Principles

- existing task cards must remain valid without migration
- worktree-aware execution is opt-in
- branch and worktree provenance should be explicit when used
- machine affinity should be optional, not assumed

## Front Matter Fields

These fields are optional additions to the standard task packet front matter.

### `execution_mode`

Allowed values:

- `REPO_FIRST`
- `WORKTREE`

Meaning:

- `REPO_FIRST` means the task uses the existing coordination model with no required worktree provenance
- `WORKTREE` means the task is expected to carry explicit branch and worktree metadata

### `branch`

The expected git branch name for the task.

Required when:

- `execution_mode` is `WORKTREE`

Optional when:

- the task remains `REPO_FIRST`

### `worktree_path`

The expected local worktree path for the task.

Required when:

- `execution_mode` is `WORKTREE`

Optional when:

- the task remains `REPO_FIRST`

### `machine_id`

An optional identifier for the machine, runner, or workstation intended to host the worktree.

Use this when:

- the task is tied to a specific development machine
- the orchestrator needs cross-computer clarity
- the project profile later requires machine-aware routing

Do not require it by default.

## Validation Rules

The current validator applies these rules:

- ordinary tasks may omit all worktree provenance fields
- if worktree provenance fields are present, `execution_mode` must also be present
- `execution_mode` must be either `REPO_FIRST` or `WORKTREE`
- when `execution_mode` is `WORKTREE`, both `branch` and `worktree_path` are required

This keeps the system backward-compatible while allowing richer dispatch and review behavior later.

## Recommended Usage

### Ordinary repo-first task

```yaml
execution_mode: REPO_FIRST
```

You may also omit the field entirely for legacy-compatible tasks.

### Worktree-aware task

```yaml
execution_mode: WORKTREE
branch: agent/external-agent-platform-16-phase7-worktree-02-r1
worktree_path: worktrees/external-agent-platform-16/phase7-worktree-02
machine_id: workstation-a
```

## Ownership vs Provenance

These fields do not replace task ownership.

- `owner` still means the responsible agent
- `reviewer` still means the assigned reviewer
- `branch`, `worktree_path`, and `machine_id` describe execution provenance

Do not confuse:

- who owns the task
- where the task is expected to run

## What This Enables Later

This metadata foundation prepares for later phases:

- worktree-aware dispatch
- provenance-aware review
- machine-aware routing
- better parallel isolation

It does not yet require automatic worktree creation or remote execution.

## Related References

- `coordination/templates/task-packet.md`
- `docs/operations/orca-comparison-and-roadmap.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
