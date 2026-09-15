# Phase 14.5 Worktree Context Contract

`scripts/worktree_context.py` is a deterministic, in-memory planning helper.
It never invokes Git, creates a worktree, reads credentials, launches a
connector, writes runtime state, or uses a network.

## Allocation

`plan_worktree_allocations()` accepts exact identity mappings of `task_id`,
`owner`, `branch`, and `worktree_path`.  The branch and worktree references
must be project-relative, collision-free, and under `agent/<owner>/` and
`worktrees/<owner>/` respectively.  The result is sorted by task ID and binds
each identity to a stable SHA-256 allocation ID.  It is a dry-run result, not
a provisioning request.

## Context

`build_bounded_context_snapshot()` accepts only an allowlisted task-card
projection, project-relative dependency-evidence references, and an approved
allocation.  It returns canonical-hash metadata plus the immutable fixture
projection with a schema version, byte bound, sensitivity label, and expiry.
Forbidden keys, absolute paths, unsafe references, allocation/task mismatch,
expired snapshots, and oversize input fail closed.

Task-card body text is not an input.  Extra harmless metadata is ignored;
prompt, command, credential, transcript, source-body, and similar material is
rejected rather than interpreted as configuration.  No returned record carries
credentials, prompts, source bodies, transcripts, or absolute paths.
