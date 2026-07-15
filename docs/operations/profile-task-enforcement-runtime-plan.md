# Profile Task Enforcement Runtime Plan

## Purpose

Phase 10 turns an explicitly selected project profile into a safe task-level
constraint. It builds on Phase 9, where profiles can be validated and shown in
dispatch messages but do not affect task validation.

## Runtime Contract

1. A profile is selected explicitly by name or path. The `active` field is not
   a runtime selector.
2. A selected profile is parsed through one shared runtime module. Scripts must
   not maintain separate profile parsers.
3. Profile schema validation remains an explicit preflight check. Dispatch must
   never claim that parsing a profile proves it conforms to the schema.
4. Task-level enforcement is additive: core-required front matter, lifecycle,
   and default `coordination/` artifact paths remain valid for every task.
5. A profile may narrow core execution/status sets and require its declared
   additional task fields. It may not introduce unsupported lifecycle values.
6. A profile must be recorded on a task only when the operator intentionally
   chooses it. Existing unprofiled tasks remain valid.

## Deliberately Deferred

- profile-aware task-board, progress, delivery, and review path remapping
- automatic selection from `active: true`, repo name, or working directory
- automatic owner, reviewer, branch, or worktree field population
- profile inheritance and profile-specific review routing

These changes alter artifact discovery and lifecycle behavior. They need their
own migration and compatibility phase after task-level enforcement is stable.

## Delivery Sequence

1. Centralize profile loading and define a profile preflight result.
2. Validate an explicitly profiled task card against the selected profile.
3. Make dispatch record and preflight an explicitly selected profile.
4. Add focused regression coverage and refresh operator guidance.

Tasks 2 through 4 must wait for the shared resolver contract from task 1.

## Dispatch Profile Recording

When `--profile` is supplied for a mutating dispatch (not `--message-only`):

1. The profile is loaded via `profile_resolver.load_profile()`.
2. The loaded profile is validated against the profile schema via `validate_profile_file()`.
3. If preflight fails, no task card fields are mutated — owner, reviewer, execution metadata, and task profile remain unchanged.
4. If preflight succeeds, the canonical `profile_name` is recorded as the task card's scalar `profile` field.

`--message-only` never mutates task-card content, including `profile`. Without `--profile`, existing task `profile` fields are never overwritten.

Profile selection does NOT automatically populate execution mode, owner, reviewer, branch, worktree, artifact paths, or lifecycle state.

## Acceptance Gate

Phase 10 is complete only when an operator can intentionally select a profile,
the system can reject task metadata that violates that profile, dispatch keeps
the selected profile visible as task evidence, existing default-mode tasks
remain compatible, and the full coordination validator passes.
