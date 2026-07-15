# Lead Agent Orchestration Protocol

## Purpose

This document defines how a single lead agent turns a user requirement into a managed multi-agent delivery loop.

The lead agent is the system's execution hub:

- receives the user request
- converts it into a bounded phase or task intake
- decomposes work into executable packets
- assigns work to implementation agents
- collects delivery evidence
- routes work to review
- decides whether to accept, fix, reassign, or escalate
- returns one consolidated report to the user

The goal is not full agent autonomy. The goal is controlled delegation with a single accountable operator inside the system.

## Role Definition

The lead agent is responsible for orchestration, not just planning.

It owns:

- intake quality
- task decomposition quality
- dispatch correctness
- dependency ordering
- blocker triage
- review routing
- final synthesis

It does not offload accountability for delivery quality to worker agents.

## Operating Contract

The lead agent may act autonomously when:

- the requirement is clear enough to define scope and acceptance
- the work can be decomposed without changing the product goal
- task ownership can be chosen from existing agent types
- a review outcome is routine and evidence-backed
- a blocker can be resolved by clarification, splitting work, or reassignment without changing user intent

The lead agent must stop and escalate to the user when:

- the requirement changes product scope or business intent
- two implementation paths have materially different cost, risk, or UX impact
- a missing dependency requires a new system, service, or external approval
- the system cannot choose between conflicting acceptance criteria
- the phase should be cancelled, significantly delayed, or fundamentally redesigned

## Standard Orchestration Loop

Every lead-agent run should follow the same sequence.

### 1. Intake

Turn the user request into a phase or task intake packet.

Minimum intake output:

- objective
- in-scope boundaries
- out-of-scope boundaries
- constraints
- dependencies
- exit criteria
- first-pass decomposition candidates

If the request is too small for a full phase, the lead agent may create a single task packet directly.

### 2. Freeze The Backbone

Before dispatching workers, the lead agent must freeze:

- the primary objective
- required interfaces or artifact formats
- allowed and forbidden scope
- review expectations

Workers should not be used to discover the backbone by trial and error.

### 3. Decompose Into Task Packets

Split the work into packets that are:

- independently reviewable
- narrow enough for one owner
- measurable by explicit acceptance criteria
- ordered by dependency

Each packet must state:

- what changes are allowed
- what must not be touched
- what evidence is required at submission

### 4. Assign And Dispatch

For each packet, the lead agent chooses:

- owner
- reviewer
- dispatch order
- whether the task may run in parallel with other tasks

Dispatch should happen only after:

- validator is clean
- dependencies are satisfied or clearly declared
- the assigned agent type matches the work

### 5. Monitor Execution

The lead agent monitors:

- task-board state
- progress reports
- incidents
- review queue

It should prefer short feedback loops over opening too many tasks at once.

### 6. Triage Blockers

When a worker opens an incident, the lead agent must choose one of five paths:

1. clarify the spec
2. patch the backbone
3. split the task into smaller packets
4. reassign to a better-fit agent
5. pull the work back into lead-agent ownership

Workers must not be left to resolve orchestration ambiguity on their own.

### 7. Review And Integrate

Once a task reaches review, the lead agent either:

- reviews it directly, or
- routes it to a designated reviewer agent

Review must check:

- scope compliance
- acceptance coverage
- repo-complete evidence
- validation and test results
- residual risks

### 8. Report Upward

The lead agent returns a single consolidated status to the user.

That report should summarize:

- what was completed
- what is still active
- what was blocked and why
- which decisions were made autonomously
- which user decisions are now required

## Required System Artifacts

The lead agent is responsible for ensuring these artifacts exist and stay coherent:

- `coordination/task-board/`
- `coordination/progress/`
- `coordination/incidents/`
- `coordination/delivery/`
- `coordination/reviews/`

For substantial initiatives, it should also produce:

- a phase intake packet
- a first-wave dispatch set
- a phase-level summary after the wave closes

## Command Expectations

The lead agent should use the coordination scripts as its primary control plane.

Current baseline commands:

- `python scripts/orchestrate.py validate`
- `python scripts/orchestrate.py next`
- `python scripts/orchestrate.py intake`
- `python scripts/orchestrate.py dispatch`
- `python scripts/orchestrate.py review`
- `python scripts/orchestrate.py repo-sync`
- `python scripts/orchestrate.py doctor` (see Doctor Command Details below)

### Doctor Command Details

The `doctor` subcommand runs read-only preflight diagnostics before any dispatch
or lifecycle operation.

**Checks performed:**

1. **Repository root** — verifies `coordination/`, `scripts/`, `docs/`, and
   `profiles/` exist in the current working directory.
2. **Git availability** — checks Git is installed, the directory is a Git
   repository, and remote `origin` is configured.
3. **Python runtime** — reports the Python version and executable path.
4. **Coordination directories** — verifies `task-board/{ready,in_progress,
   review,blocked,done}` exist, warns about optional subdirectories.
5. **Optional `--task-id`** — validates the referenced task card exists in any
   task-board state directory.
6. **Optional `--profile`** — validates the named profile or profile path is
   resolvable (reuses `profile_resolver.py`).

**Exit behavior:**

- Exit code `0`: all required checks passed.
- Exit code `1`: one or more required checks failed. Output shows which checks
  failed and a recommended recovery action for each.

**Usage examples:**

```bash
# Basic diagnostic from the repository root
python scripts/orchestrate.py doctor

# Validate a specific task reference
python scripts/orchestrate.py doctor --task-id phase11-runtime-safety-01

# Validate a specific profile reference
python scripts/orchestrate.py doctor --profile rental-rebuild

# Validate both
python scripts/orchestrate.py doctor --task-id phase11-runtime-safety-01 --profile rental-rebuild
```

**Key constraints:**

- The command is diagnostic only. It never writes, moves, claims, dispatches,
  commits, pushes, creates worktrees, or changes task-card fields.
- It does not require network access for the default diagnostic path.
- It reuses existing runtime and profile-resolution helpers instead of
  duplicating profile parsing.
- It keeps default-mode repositories fully compatible.

### Dispatch Command Details

The `dispatch` command assigns a task owner (and optional reviewer), then prints a ready-to-send dispatch message to stdout. The message includes the task ID, task file path, required protocol docs, and start/blocked/finish instructions.

Flags:

- `--task-id` (required) — task to dispatch
- `--owner` (required) — agent to assign
- `--reviewer` — optional reviewer override
- `--execution-mode` — optional execution contract (`REPO_FIRST` or `WORKTREE`)
- `--branch` — branch provenance for worktree-aware dispatch
- `--worktree-path` — worktree path provenance for worktree-aware dispatch
- `--machine-id` — optional machine provenance for distributed runs
- `--no-message` — suppress the dispatch message output
- `--output FILE` — write the dispatch message to FILE (`-` for stdout-only, supresses decorated block)
- `--message-only` — print the message without updating owner/reviewer
- `--allow-terminal` — allow dispatching tasks in terminal states

When `--execution-mode WORKTREE` is used, dispatch must include a branch and worktree path, either from the command flags or already-present task metadata. The command does not create the git worktree for the worker. It only records the provenance and includes it in the dispatch message so the assigned agent can verify it before implementation.

### Owner Selection and Reviewer Routing

When choosing an owner and reviewer for dispatch, refer to the [Worker Assignment Policy](worker-assignment-policy.md). It defines:

- **Assignment Matrix** — which agent type (platform, docs, architecture, test) should own which task shape
- **Parallelization Rules** — when tasks may run concurrently vs. must wait for a dependency
- **Review Assignment Rules** — when review should be separated from implementation, and when the orchestrator may review directly

Use the dispatch `--reviewer` flag to override the task card's default reviewer when the policy recommends independent review for high-risk or cross-cutting changes.

Example:

```bash
python scripts/orchestrate.py dispatch \
  --task-id phase6-lead-agent-02 \
  --owner external-agent-platform-15 \
  --reviewer ORCHESTRATOR
```

Worktree-aware example:

```bash
python scripts/orchestrate.py dispatch \
  --task-id phase7-worktree-02 \
  --owner external-agent-platform-16 \
  --execution-mode WORKTREE \
  --branch agent/external-agent-platform-16-phase7-worktree-02-r1 \
  --worktree-path worktrees/external-agent-platform-16/phase7-worktree-02 \
  --machine-id workstation-a
```

The command prints the updated task info followed by a `--- Dispatch Message ---` block that the lead agent can paste directly to the assigned worker. Use `--output -` to pipe the raw message body into another tool (e.g. `... --output - | pbcopy`).

## Dispatch Rules

The lead agent must not dispatch work that is:

- blocked by an unresolved dependency
- missing acceptance criteria
- missing scope boundaries
- already in active review unless the next action is a fix return
- too large to be reasonably reviewed as a single packet

It should prefer opening a small first wave, then expanding once review feedback proves the pattern is stable.

## Review Routing Rules

The lead agent may review directly when:

- the task is small and low risk
- the evidence is straightforward
- no separation of duties is required

It should route to a reviewer agent when:

- the task changes a shared backbone
- multiple workers contributed intersecting changes
- the task is compliance-heavy or process-heavy
- an independent read is more valuable than speed

## Reassignment Rules

The lead agent should reassign work when:

- the assigned agent lacks the needed capability
- the task proves broader or narrower than expected
- the same blocker repeats after clarification
- the original owner is no longer the best fit

Reassignment is a normal control action, not a failure signal.

## Completion Gate

The lead agent must not report a task or phase as complete unless:

- the repo contains the expected artifacts
- the task has a review outcome
- validator passes
- residual risks are stated
- dependent follow-up work is either opened or explicitly deferred

## Success Criteria For Lead-Agent Mode

This protocol is working when:

- the user gives the requirement once
- the lead agent creates and dispatches the work without repeated human relaying
- worker agents operate from repo state rather than chat transcripts
- review outcomes are evidence-based and repeatable
- the user receives one coherent summary instead of fragmented agent chatter
