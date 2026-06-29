# Phase 2 Productionization Plan

## Purpose

Phase 2 turns the validated pilot workflow into a stronger operating system that can support real project work, not just process validation tasks.

Phase 1 proved that:

- external agents can start from repo context
- repo-backed progress and review can work
- validator enforcement improves data quality
- reviewer discipline can be standardized

Phase 2 should make that system more durable, more scalable, and more suitable for real engineering delivery.

## Phase 2 Objective

Productionize the repo-first coordination workflow so it can support actual project tasks with tighter artifact discipline, stronger review inputs, and a cleaner handoff from workflow tasks to real implementation tasks.

## Entry Criteria

Phase 2 begins only after:

- `phase1-live-01` is done
- `phase1-live-02` is done
- `phase1-live-03` is done
- the validator passes on the current coordination repo
- the orchestrator confirms the pilot proved the workflow is usable

## Exit Criteria

Phase 2 is complete when:

- a formal retrospective captures what Phase 1 taught
- delivery-report expectations are standardized and enforced
- the repo includes a repeatable intake path for real project work
- at least one real-project phase packet or implementation-ready backlog is prepared for the next execution wave

## Scope

### In Scope

- retrospective and lessons-learned capture
- artifact standardization improvements
- validator strengthening tied to established rules
- phase intake and real-project task packet preparation
- workflow documentation updates required to support the above

### Out Of Scope

- broad product implementation not yet packetized
- destructive infra or migration work
- unbounded architecture changes
- large API or service implementation without a separate project phase spec

## What Changes In Phase 2

Phase 1 asked: "Can the workflow run?"

Phase 2 asks:

- can the workflow reliably support real work?
- can submissions become more complete and less ambiguous?
- can the next phase prepare actual engineering backlog instead of only process tasks?

## Key Risks

- review may still rely too much on informal judgment if delivery artifacts remain loose
- real project tasks may have wider scope and hidden dependencies than pilot tasks
- agents may still under-produce explicit delivery evidence unless the standard is tightened

## Phase 2 Strategy

Use a controlled expansion:

1. capture pilot lessons while they are fresh
2. tighten the weakest artifact rule discovered in Phase 1
3. create a clean intake and packetization path for real engineering work
4. only then open the next non-process delivery phase

## Recommended Phase 2 Workstreams

### Workstream A: Retrospective

Capture:

- what worked in Phase 1
- what still required human interpretation
- what should change before scaling

### Workstream B: Delivery Artifact Standardization

Strengthen:

- explicit delivery report expectations
- validator support for that standard if appropriate

### Workstream C: Real Project Intake

Create:

- a project intake template or phase intake document
- the first implementation-ready project phase packet set

## Recommended Phase 2 First Wave

The first wave of Phase 2 should contain three tasks:

- `phase2-01` Phase 1 retrospective
- `phase2-02` delivery report standardization
- `phase2-03` real-project intake packet

These are deliberately chosen because they:

- build directly on what Phase 1 exposed
- improve the workflow before broader scaling
- prepare the bridge into actual engineering work

## Success Signals

You should consider Phase 2 healthy if:

- future tasks have clearer artifact expectations than Phase 1
- reviewers spend less time inferring missing evidence
- a real project can be decomposed into task packets without reinventing the workflow

## Practical Recommendation

Do not jump straight from Phase 1 pilot success into a large implementation wave.

Use Phase 2 to harden the workflow with a small number of targeted tasks, then open the first real engineering phase from a stronger base.

