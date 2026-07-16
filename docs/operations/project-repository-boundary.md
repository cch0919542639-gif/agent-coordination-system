# Project Repository Boundary

## Rule

`agent-coordination-system` is the reusable coordination engine. Every product
or business project is a separate Git repository and owns its own coordination
artifacts.

The engine repository's `coordination/` directory tracks only changes to the
engine itself. It must not become a shared task board for unrelated products.

## Required Project Layout

Every adopting project commits this structure at its repository root:

```text
<project-repository>/
  coordination/
    task-board/{ready,in_progress,review,done,blocked}/
    progress/
    delivery/
    reviews/
    incidents/
    completed/
```

Task cards, progress, delivery reports, incidents, review records, and phase
intakes belong to the repository whose code or documents they describe. They
are committed with that project's branch and reviewed with that project's
changes.

## Engine Responsibilities

The engine provides reusable scripts, templates, validation rules, profiles,
and operational protocol. It does not own product task state.

Projects either vendor/install a compatible engine release or run a checked-out
engine runtime configured to target that project repository. Runtime state such
as monitor cursors, event ledgers, and local worktree paths remains local and
Git-ignored; it is never a tracked artifact in either repository.

## Project Registry

The Phase 12 monitor uses an explicit local project registry. Each entry names
one project, its local clone path, Git remote, default branch, optional profile,
and enabled event destinations. The registry is local-only because it may
contain machine paths and runner routing details.

The monitor polls each registered project independently and includes the
project identifier in every event ID. It never assumes engine task cards are
product-project task state.

## Cross-Project Safety

- A task changes artifacts only inside its owning project repo.
- A review event is routed to the owning project's reviewer policy.
- Owner identities may be reused, but assignments and cursors are project-scoped.
- Shared engine upgrades are versioned separately and never rewrite product
  task history automatically.
- A project profile narrows policy for that project; it cannot change the core
  lifecycle or leak artifact paths into another project.

## Example

```text
agent-coordination-system/
  scripts/                    # engine implementation
  coordination/               # engine development only

agent-usage-collector/
  src/
  coordination/               # collector tasks and evidence only

rental-rebuild/
  src/
  coordination/               # rental tasks and evidence only
```

## Adoption Gate

Before dispatching to a new project, verify that it has its own committed
coordination layout, explicit profile/default policy, and project-registry
entry. A missing layout is a setup failure, not a reason to write product task
artifacts into the engine repository.
