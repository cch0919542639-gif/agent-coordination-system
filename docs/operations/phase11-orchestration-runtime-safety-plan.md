# Phase 11 Orchestration Runtime Safety Plan

## Purpose

Phase 11 makes the lead-agent workflow safer to run across computers and
external agents. It turns the recurring setup failures into explicit,
machine-readable preflight checks before any task is dispatched or claimed.

## Runtime Contract

1. Safety checks are read-only unless an operator explicitly requests a
   provisioning command.
2. A failed preflight reports the exact failed check and a practical recovery
   action; it must not mutate task cards, profiles, branches, or worktrees.
3. Every dispatchable run has immutable evidence of its repo, revision,
   profile choice, owner, reviewer, and selected tasks.
4. A worker receives work only after the lead agent has verified repository
   identity, runtime availability, and the task packet's prerequisites.
5. Worktree creation remains opt-in and profile policy never silently creates
   a worktree, branch, or remote assignment.

## Delivery Sequence

1. Add `orchestrate doctor` for repository and runtime preflight diagnostics.
2. Add a dependency-aware wave planner that proposes, but never claims, ready
   tasks.
3. Add an immutable run manifest for a dispatched wave.
4. Add an opt-in worktree preflight/provisioning boundary using the manifest.
5. Add cross-machine handoff and end-to-end regression coverage.

Each later task depends on the preceding safety contract. Planning and
diagnostics may not change lifecycle state by themselves.

## Deliberately Deferred

- autonomous agent launching or direct agent-to-agent messaging
- automatic task claiming or review acceptance
- profile artifact-path remapping or inheritance
- remote secret distribution, hosted queues, and dashboard work
- automatic merge, pull-request approval, or deployment actions

## Acceptance Gate

Phase 11 is complete only when a lead agent can diagnose an incorrect clone or
missing runtime before dispatch, preserve reproducible evidence for a wave,
and prepare isolated work safely without hidden lifecycle mutations.
