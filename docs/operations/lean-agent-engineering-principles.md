# Lean Agent Engineering Principles

## Purpose

This document defines the implementation principles the orchestrator should prefer when designing phases, dispatching agents, reviewing delivery, and evolving the coordination system.

The goal is not minimalism for its own sake. The goal is to reduce overbuilding, keep the repo truthful, and make each change as small, verifiable, and recoverable as possible.

These principles are especially important for:

- profile-layer work
- validator and dispatch evolution
- multi-agent coordination changes
- project-specific compatibility work

## Core Principles

### 1. Prefer Existing Capability Before New Construction

Before adding a new script, schema field, artifact type, or workflow layer:

1. check whether the current repo already has a usable mechanism
2. check whether the current protocol already answers the need
3. extend the smallest existing surface that can solve the problem

Default posture:

- reuse before invent
- extend before replace
- patch before redesign

### 2. Prefer Small, Verifiable Steps

Every meaningful change should be able to pass through the existing control loop:

- task packet
- scoped implementation
- delivery evidence
- validator
- review

Avoid large speculative changes that require multiple new assumptions to become useful.

Good step shape:

- one new validator rule
- one dispatch flag
- one schema clarification
- one operator doc correction

Bad step shape:

- a full subsystem rewrite
- multiple new conventions at once
- future-state behavior documented as current behavior

### 3. Prefer Declarative Policy Over Hidden Logic

If a project difference can be expressed as declared configuration or documented policy, prefer that over embedding special-case logic into the core engine.

Examples:

- project-specific roles belong in profiles
- project-specific artifact paths belong in profiles
- project-specific branch rules belong in profiles

Do not hardcode one project's behavior into global defaults unless the behavior truly belongs to every project.

### 4. Prefer Truthful Documentation Over Aspirational Documentation

Operator docs, dispatch notes, examples, and reviewer guidance must describe:

- what is supported now
- what is manual today
- what is deferred to a future phase

Do not present future-state behavior as if the scripts already implement it.

If a flow is aspirational, label it clearly.

### 5. Prefer Repo Evidence Over Chat Assumptions

A coordination claim is only real when the repo shows it.

Examples:

- a task is not complete because chat says it is complete
- a profile is not supported because a plan mentions it
- a workflow is not live because an example document describes it

Trust order:

1. code and scripts
2. task cards, reviews, delivery reports
3. validated docs
4. chat summary

### 6. Prefer Core Stability Over Project Convenience

When a project-specific need conflicts with the stability of the coordination core:

- protect the core first
- isolate the project-specific rule in a profile, policy doc, or follow-up phase

The coordination system should become more configurable, not more entangled.

### 7. Prefer Manual Clarity Before Partial Automation

If full automation is not yet implemented, the next best state is not vague automation language.

The next best state is:

- explicit manual step
- explicit operator responsibility
- explicit boundary of what the script does and does not do

Manual but clear is better than half-automated and misleading.

### 8. Prefer the Native Platform Before New Dependencies

When a platform, language, browser, or current toolchain already provides the needed capability, use that first unless there is a strong reason not to.

Examples:

- native HTML control before UI library
- existing script before new service
- existing repo layout before new artifact tree

New dependency should justify itself with clear operational value, not aesthetic preference.

## Design Heuristics

When deciding whether to add something, ask:

1. Can the current repo already express this?
2. Can the current validator or dispatch path absorb this with a small extension?
3. Is this a core behavior or a project policy?
4. Will this make review more objective or less objective?
5. If an agent misreads this, will the repo still protect us?

If the answer to most of these is unclear, the change is probably too large or too early.

## Application To Current Roadmap

### For profile work

- define schema before runtime
- validate profiles before automating path remapping
- add `--profile` context before pretending full profile-native execution exists

### For multi-agent coordination

- strengthen validator and review flow before adding UI layers
- prefer repo-backed evidence over live orchestration theatrics
- keep agent responsibilities narrow and reviewable

### For project compatibility

- express differences in profiles
- do not rewrite global defaults to fit one project
- document unresolved gaps instead of masking them

## Review Lens

During review, these are warning signs:

- new abstraction with no immediate validation path
- docs that claim support not present in scripts
- project-specific behavior pushed into global defaults
- multiple new concepts bundled into one task
- convenience changes that weaken review clarity

These are positive signals:

- additive change with clear rollback
- validator coverage added alongside new declarations
- small extensions to existing scripts
- explicit future hooks instead of fake completeness
- stronger alignment between docs and real behavior

## Short Version

Build the smallest truthful thing that fits the existing system, proves itself through repo evidence, and does not pollute the core to satisfy one project's convenience.
