# Worker Assignment Policy

## Purpose

This document defines how the lead agent chooses the right worker and reviewer for each task packet.

The policy exists to answer four questions:

1. Which agent type should own this task?
2. Which tasks may run in parallel?
3. When should work be reassigned?
4. When should review be separated from implementation?

The goal is predictable assignment, not ad hoc task claiming.

## Assignment Principles

### Principle 1: Match The Task To The Dominant Skill

Every packet should have one dominant skill profile.

Examples:

- architecture and protocol shaping -> architecture/planning agent
- Python service or script implementation -> platform/backend agent
- docs, rollout, and operator guides -> docs/operations agent
- verification, smoke, or regression coverage -> test/reviewer agent

Do not assign one packet to multiple owners. Split the packet instead.

### Principle 2: Prefer Narrow Ownership

If a task touches multiple concerns, the lead agent should first ask whether it can be decomposed.

Bad assignment:

- one task that edits routing, persistence, docs, validation, and rollout notes

Better assignment:

- implementation packet
- test/verification packet
- docs/operations packet

### Principle 3: Protect Shared Backbones

Tasks that modify shared workflows, coordination rules, or common interfaces should go to the most reliable platform or architecture agent available, with independent review afterward.

### Principle 4: Keep Review Independent When Risk Rises

As scope, risk, or coupling increases, implementation and review should be separated.

## Agent Categories

Use these categories when selecting owners.

### Planning / Architecture Agent

Best for:

- phase intake
- decomposition
- protocol design
- shared interface decisions
- dependency analysis

Avoid using as the default implementation owner for all tasks; it should enable parallel work, not absorb it.

### Platform / Backend Agent

Best for:

- Python scripts
- APIs
- data flow
- repositories and service integration
- operational tooling

Use when the main work is in `scripts/**`, `services/**`, `src/**`, or testable backend logic.

### Docs / Operations Agent

Best for:

- rollout guides
- operator checklists
- execution sheets
- onboarding docs
- playbooks and process hardening

Use when the main output is in `docs/**` or coordination-facing markdown artifacts.

### Test / Reviewer Agent

Best for:

- smoke tests
- verification harnesses
- review-only passes
- evidence and acceptance checks

Use as an independent reviewer when the implementation changes shared behavior or touches multiple filesets.

## Assignment Matrix

| Task Shape | Primary Owner | Default Reviewer |
|---|---|---|
| Phase intake / decomposition | Planning agent | Orchestrator or architecture reviewer |
| Script automation | Platform agent | Reviewer or orchestrator |
| Coordination API behavior | Platform/backend agent | Independent reviewer |
| Docs / rollout artifact | Docs/operations agent | Orchestrator or reviewer |
| Validation / smoke / harness work | Test/platform agent | Orchestrator |
| Shared workflow or protocol change | Architecture or platform agent | Independent reviewer |

## Parallelization Rules

Tasks may run in parallel only when all of the following are true:

- they do not require the same file or narrow code region
- they do not depend on the same unfinished interface decision
- each task has its own measurable acceptance criteria
- one task failing review does not invalidate the other's objective

Good parallel examples:

- backend implementation plus docs update packet
- service implementation plus independent smoke-test packet
- intake drafting plus reviewer-playbook refinement

Bad parallel examples:

- two agents editing the same orchestration command
- one task defining a contract while another implements against an unfrozen version
- docs written before interface names and flags are settled

## Dependency Rules

A task should wait when it depends on:

- an unfinished backbone decision
- a missing interface or file that another packet must create
- an unresolved incident in a shared area
- a review outcome that could change the task's acceptance criteria

If the dependency is soft rather than hard, the lead agent may open the task with the dependency explicitly listed and a constrained scope.

## Reassignment Triggers

The lead agent should consider reassignment when:

- the worker reports a capability mismatch
- the worker hits the same blocker twice after clarification
- the task expands into a different dominant skill profile
- the task was assigned before a key dependency became visible
- the phase needs an independent fix owner for clean review separation

## Review Assignment Rules

Use an independent reviewer when:

- the task touches shared orchestration logic
- the task changes dispatch or review behavior
- the task produces a new standard that future agents will follow
- multiple artifacts must be cross-checked together

The orchestrator may review directly when:

- the packet is small
- the scope is low risk
- the evidence is obvious
- speed is more important than formal separation

## Default Policy For The Next Automation Wave

For the lead-agent automation work, use this default split:

- intake generation -> planning/platform hybrid, preferably a platform agent comfortable with markdown and script scaffolding
- dispatch command expansion -> platform agent
- script docs and validation integration -> docs/operations or platform agent, depending on whether the dominant work is code or documentation
- final review -> independent reviewer or orchestrator

## Stop Conditions

Do not dispatch a task until the owner choice is at least directionally correct.

If the lead agent cannot explain in one sentence why a given owner is the best fit, the task is probably not decomposed cleanly enough yet.
