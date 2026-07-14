# Orca Comparison And Roadmap

## Purpose

This document compares the current coordination system with [stablyai/orca](https://github.com/stablyai/orca) and turns that comparison into a practical roadmap.

The goal is not to copy Orca blindly.

The goal is to identify:

- where the two systems are genuinely similar
- where they operate at different layers
- what our current system already does well
- which upgrades would move us toward a stronger multi-agent platform

## Executive Summary

Orca and this project are solving adjacent parts of the same problem.

Orca is primarily a product-layer orchestration environment:

- multi-agent runtime control
- parallel worktrees
- integrated terminals
- in-app review
- browser and UI interaction
- mobile and remote operation

This project is currently a coordination-layer system:

- task protocols
- repo-backed state
- evidence-driven delivery
- dispatch and review rules
- validator-backed workflow safety
- lead-agent orchestration conventions

In short:

- Orca is closer to an agent operating environment
- this project is closer to a durable multi-agent delivery protocol

That is why the two feel highly similar while still being meaningfully different.

## Where Orca And This Project Align

### 1. Single Hub For Many Agents

Both systems assume one coordination surface should manage multiple agents rather than forcing the user to manually juggle isolated chat sessions.

### 2. Parallel Work

Both systems are optimized for running multiple tasks or approaches at once instead of one linear agent thread.

### 3. Review Matters

Both systems treat review as a first-class part of the workflow, not an afterthought.

### 4. Agent-Native Execution

Both systems assume agents are working actors inside the delivery loop, not just passive assistants.

### 5. Task Visibility

Both systems need the operator to know:

- who is doing what
- what is blocked
- what is ready for review
- what result should be trusted

## Where Orca And This Project Differ

### 1. Product Layer vs Coordination Layer

Orca is an application.

It provides:

- desktop UI
- mobile companion
- terminal management
- browser/design mode
- SSH worktrees
- worktree lifecycle tooling

This project currently provides:

- protocols
- repo structure
- scripts
- docs
- coordination API
- review and evidence model

### 2. Runtime State vs Durable Repo State

Orca emphasizes the live runtime experience of many agents.

This project emphasizes state that survives:

- restarts
- machine changes
- agent replacement
- review cycles

That is why repo artifacts are central here.

### 3. UI-First vs Evidence-First

Orca is optimized for active orchestration in a rich interface.

This project is optimized for:

- auditability
- handoff clarity
- replayability
- versioned operational evidence

### 4. Worktree Isolation

Orca bakes isolated worktrees into the core product model.

This project currently assumes task and scope isolation, but does not yet enforce worktree-per-agent as a built-in execution primitive.

## What Our System Already Does Better

### 1. Strong Repo Evidence Model

The combination of:

- task cards
- progress reports
- incidents
- delivery reports
- review reports
- validator checks

creates a strong delivery record.

### 2. Clear Acceptance Gates

This system makes acceptance explicit through:

- `accepted`
- `needs_fix`
- `reassign`
- `rejected`

That is useful for reliable engineering operations.

### 3. Recoverability

If the app disappears, the repo still contains the workflow truth.

That is a major advantage over UI-heavy systems with thinner state persistence.

### 4. Human-Agent-Agent Collaboration Discipline

This project already has:

- lead agent protocol
- worker assignment policy
- orchestrator flow
- escalation rules

That structure is unusually strong for an early-stage multi-agent system.

## What Orca Does Better Today

### 1. Operator Experience

Orca gives the operator a real environment for steering many agents.

### 2. Worktree-Native Parallelism

Its isolated worktree model reduces collisions and makes comparison easier.

### 3. Runtime Tooling

Integrated terminals, browser interaction, and SSH execution make it much more like a live orchestration cockpit.

### 4. Native Multi-Computer / Remote Story

Orca already treats remote execution as normal, not as an afterthought.

## Strategic Conclusion

We should not try to become Orca all at once.

We should preserve the strengths of this project:

- repo-backed evidence
- strict review model
- reproducible state
- orchestrator discipline

Then add the missing product/runtime layers in stages.

The best path is:

1. strengthen worktree-aware dispatch
2. strengthen runtime visibility
3. add a lightweight control surface
4. add remote worker execution ergonomics

## Roadmap

## Phase A: Worktree-Aware Coordination

Objective:

Make agent isolation real at the git/worktree level, not only at the task-card level.

Recommended outcomes:

- dispatch can create or reserve a worktree for a task
- task cards can record `branch`, `worktree_path`, and optionally `machine_id`
- review reports can reference branch/worktree provenance
- the validator can confirm worktree metadata when required

Why this phase matters:

This is the strongest Orca-like improvement with the least product complexity.

## Phase B: Lead-Agent Runtime Control

Objective:

Give the lead agent a stronger command and monitoring layer.

Recommended outcomes:

- richer `orchestrate.py next`
- queue summaries by owner, phase, and blocker class
- explicit dispatch bundles
- clearer reassignment tooling
- stronger repo-sync projections

Why this phase matters:

Before building a full dashboard, the CLI and repo state should become more expressive.

## Phase C: Minimal Orchestrator Dashboard

Objective:

Create a lightweight control UI for the orchestrator.

Recommended first dashboard views:

- ready
- in_progress
- blocked
- review
- owner
- reviewer
- last update
- branch/worktree
- heartbeat / lease status

Why this phase matters:

This is where the system starts feeling like a true orchestration product instead of only a disciplined repo workflow.

## Phase D: Remote Worker And Machine Awareness

Objective:

Make cross-computer and remote execution first-class.

Recommended outcomes:

- machine identity in assignments
- optional remote path / SSH metadata
- clearer handoff when an agent changes computers
- remote-safe task routing

Why this phase matters:

This closes the gap between repo coordination and distributed runtime orchestration.

## Phase E: Unified Product Layer

Objective:

Combine repo-backed evidence with a real orchestration interface.

Possible outcomes:

- task board UI backed by repo + API state
- worktree launch buttons
- review inbox
- diff and artifact preview
- dispatch message generation in UI
- incident triage panel

Why this phase matters:

This is the closest convergence point with the class of product Orca represents.

## Concrete Next Steps

The next practical build steps should be:

1. add task metadata for branch / worktree assignment
2. add `orchestrate.py` support for worktree-aware dispatch
3. extend review and validator logic to understand worktree provenance
4. build a minimal operator dashboard from existing coordination state

## Things We Should Not Lose

As the system evolves, do not throw away:

- repo-first truth
- delivery reports
- review reports
- explicit acceptance states
- validator-backed consistency

These are core strengths, not temporary scaffolding.

## Final Position

This project should not aim to be a weaker clone of Orca.

It should aim to become:

- a stronger coordination core
- with worktree-aware execution
- with a lightweight orchestration surface
- while preserving evidence, review, and recovery discipline

That path creates a system that is both operationally trustworthy and productively agent-native.
