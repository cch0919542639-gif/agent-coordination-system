# Progress Report

- Agent: codex
- Active Task: strategic-reference-tracking
- Phase: cross-phase-planning
- Status: IN_PROGRESS
- Last Updated: 2026-07-08 Asia/Taipei

## Current Step

Maintaining a persistent Codex-only reference and strategy file so future planning, phase design, and dispatch decisions can reuse prior analysis without depending on chat memory.

## Changes So Far

- `coordination/progress/codex.md` — created and populated with strategic notes covering rental-rebuild compatibility, Orca comparison, Clawling comparison, and implementation direction

## Blocker Status

none

## Next Step

Continue using this file as the stable internal planning reference before opening future phases, designing project-profile support, and dispatching roadmap-derived work.

## Why This File Exists

This file is my dedicated repo-backed memory for:

- external reference analysis
- project-profile compatibility decisions
- architecture comparison notes
- implementation direction that should survive chat loss or machine changes

It is not a delivery artifact for one task. It is an operational memory file to support continued planning and dispatch.

## Reference Set A: Rental-Rebuild Compatibility Draft

Source:

- user-provided migration draft from another Codex session
- intended target: make `agent-coordination-system` compatible with the rental rebuild project without forcing the rental project to adopt a new coordination syntax

Main ideas from that draft:

- support `backlog/`, `handoffs/`, and `completed/`
- support non-YAML markdown task cards
- support project-specific specialist roles such as `Codex`, `reasonix`, `open`, `mimo`, `box`
- integrate GitHub branch / PR rules into lifecycle
- elevate phase backbone artifacts such as master status and dispatch / handoff plans
- strengthen validator from file-shape checks into flow-consistency checks

## Decision On Reference Set A

The migration draft is useful, but it should not overwrite the core system globally.

Adopt:

- backlog as a first-class state
- handoffs as a first-class coordination artifact
- stronger validator flow-consistency checks
- project-specific role policy support
- GitHub lifecycle integration
- backbone artifact elevation

Do not adopt globally as hard core defaults:

- pure markdown task cards replacing YAML everywhere
- fixed role names hardcoded into the core system
- one project's branch / PR policy becoming universal policy
- `completed/` replacing `delivery/` globally

Correct framing:

- the rental project draft should become a `project profile`
- the core system should remain profile-driven and multi-project capable

## Reference Set B: Orca

Source:

- [stablyai/orca](https://github.com/stablyai/orca)

Key observations:

- Orca is product-layer orchestration
- strong multi-agent runtime management
- strong worktree-oriented execution model
- operator experience is a major strength
- better live orchestration cockpit than our current system

What Orca validates for us:

- multi-agent orchestration should have a clear control hub
- worktree isolation is a high-value next step
- runtime visibility should eventually become first-class

What not to do:

- do not abandon repo-backed evidence
- do not jump straight into a heavy UI before core coordination remains solid
- do not replace our protocol layer with a pure runtime shell

Implementation direction extracted from Orca:

- add worktree-aware dispatch
- add branch / worktree provenance
- add stronger orchestrator control views
- later add minimal dashboard / console

## Reference Set C: Clawling

Source:

- [Clawling home](https://clawling.com/)
- [ClawChat](https://clawling.com/chat)
- [ClawNest](https://clawling.com/nest)
- [ClawMesh](https://clawling.com/mesh)

Key observations:

- product family is clearly layered
- `ClawChat` = interaction layer
- `ClawNest` = agent creation / distribution / market layer
- `ClawMesh` = protocol / trust / value-exchange layer
- strong framing around trust, openness, control, and not being locked into platforms

What Clawling validates for us:

- our system should separate coordination core from product/runtime surface
- project-profile system is the right next abstraction
- an eventual agent registry / capability catalog would be valuable
- a whitepaper-level protocol narrative is useful, not just operational docs

What not to copy directly right now:

- consumer-facing product surface
- value / asset / reward system
- chat-first product priority

Implementation direction extracted from Clawling:

- define clear system layers
- build project profile layer explicitly
- later add agent registry / capability catalog
- eventually produce a stronger coordination whitepaper / protocol narrative

## Current Strategic Synthesis

The system should evolve as:

1. core coordination engine
2. project profile layer
3. worktree-aware execution layer
4. runtime orchestration surface

The core engine should remain stable around:

- repo-first evidence
- task lifecycle
- progress / incident / delivery / review concepts
- validator-backed consistency
- explicit acceptance states

Project-specific customization should move into profiles, not into hardcoded core behavior.

## What We Should Build Next

### Highest-priority architecture direction

- formal `project profile system`
- `rental-rebuild` as the first non-default profile
- worktree-aware dispatch

### Current planned phase

- `phase7-worktree-aware-coordination`

Reason:

- strongest next step validated by Orca comparison
- low risk relative to building a large UI
- improves parallel safety and provenance

### Next phase after worktree-aware coordination

- `phase8-profile-layer`

Intended outcomes:

- define profile schema
- keep YAML-capable core intact
- add markdown-task-card compatibility as a profile option
- support role mapping and artifact mapping per project
- separate global policy from project policy

## Profile-Layer Decisions Already Reached

These should be treated as settled working assumptions unless later evidence invalidates them:

- task card format should be profile-configurable
- artifact model should support `delivery/`, `completed/`, and `handoffs/` with profile mapping
- role names should be project-specific mappings, not core engine constants
- branch / PR rules should be project policy, not universal defaults

## Validator Direction

Short term:

- continue strict repo-consistency checks

Medium term:

- validator reads active project profile
- schema rules vary by profile
- required evidence rules vary by profile
- high-conflict ownership rules can become profile-driven

Do not make GitHub / PR checks hard blockers too early unless they are stable and project-aware.

## Dispatch And Review Direction

Dispatch should eventually understand:

- owner
- reviewer
- branch
- worktree path
- machine identity
- profile-specific policy checks

Review should eventually understand:

- provenance
- profile-specific acceptance rules
- role-sensitive conflict zones

## Practical Guidance For Future Me

Before opening the next planning phase or dispatching new work:

1. check whether the requested change belongs to core engine, project profile, or runtime surface
2. avoid putting project-specific behavior into global defaults
3. preserve repo-backed evidence model
4. prefer additive compatibility over destructive migration
5. use Orca as runtime inspiration, not as a direct template
6. use Clawling as a layering inspiration, not as a product clone

## Likely Next Docs / Specs To Create

- `docs/operations/project-profile-system.md`
- `profiles/default/profile.md`
- `profiles/rental-rebuild/profile.md`
- `docs/operations/clawling-comparison-and-implementation-notes.md` if a public-facing internal comparison doc is needed

## Current Reminder

The right direction is not:

- “rewrite the coordination system around one project”

The right direction is:

- “turn the coordination system into a configurable multi-project coordination platform”

## Reference Set D: Ponytail-Inspired Working Principles

Source:

- [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)

What is useful for this project:

- strong bias toward existing capability before new construction
- resistance to overbuilding
- preference for smaller, more native solutions
- emphasis on truthful, minimal implementation over decorative complexity

What should not be copied blindly:

- any assumption that terse implementation alone is enough for coordination work
- any reduction that weakens repo evidence, validator coverage, or review clarity
- replacing orchestration protocol with style-only guidance

Adopted into this project as working principles:

- reuse before invent
- extend before replace
- patch before redesign
- declarative project policy before core hardcoding
- truthful docs before aspirational docs
- manual clarity before misleading partial automation

Repo artifact:

- `docs/operations/lean-agent-engineering-principles.md`
