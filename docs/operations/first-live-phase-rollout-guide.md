# First Live Phase Rollout Guide

## Purpose

This guide explains how to launch the first real GitHub-based collaboration phase with other agents using the repo-first coordination system.

The goal is not to maximize parallelism immediately.

The goal is to:

- prove the workflow works in real conditions
- keep coordination overhead manageable
- detect protocol gaps early
- establish confidence before scaling to more agents

## Short Answer

For the first live phase, do **not** open everything at once.

Run a controlled rollout:

1. start with one small phase
2. assign one or two low-coupling task packets
3. enforce strict repo-based reporting
4. review every submission manually
5. expand only after the first loop is clean

## Launch Criteria

Before the first live phase begins, the following should already exist:

- phase objective
- backbone or frozen spec for the phase
- task packet template
- progress template
- incident template
- review template
- task-board directory structure
- readiness checklist
- execution protocol
- validator script

If any of those are missing, fix that first.

## What Counts As "First Live Phase"

This is the first time you let real external agents collaborate through GitHub and repo files, instead of relying mostly on direct chat relays.

That means:

- task packets are committed
- agents pull the repo to discover context
- agents report through repo files
- review is based on repo evidence

## Recommended Rollout Scope

Choose a phase with these characteristics:

- limited architectural risk
- clear acceptance criteria
- low dependency fan-out
- small enough for close review
- valuable enough to test the real workflow

Good first-live candidates:

- documentation tasks
- isolated UI cleanup
- narrow backend handlers
- test coverage additions
- task-board or tooling support work

Avoid as first-live candidates:

- cross-cutting refactors
- migrations with destructive consequences
- unclear product decisions
- phase-defining architecture work
- anything where acceptance is mostly subjective

## Rollout Strategy

Use a three-ring rollout.

### Ring 1: Controlled Pilot

Scope:

- one phase
- one or two agents
- one or two task packets
- orchestrator reviews everything

Objective:

- verify the protocol works end to end

Success signal:

- tasks move cleanly through `ready -> in_progress -> review -> done`
- incidents are understandable
- review outcomes are actionable
- no hidden chat dependency is required

### Ring 2: Limited Expansion

Scope:

- one phase
- two to four agents
- a few independent task packets

Objective:

- verify reassignment, blockers, and concurrent coordination

Success signal:

- agents do not collide
- repo files remain consistent
- review queue stays manageable

### Ring 3: Normalized Use

Scope:

- regular GitHub-based collaboration
- multiple parallel packets
- more specialized agent roles

Objective:

- make this the default project operating mode

## Day 0 Setup

Before inviting agents, complete this sequence.

### 1. Freeze the phase boundary

Define:

- phase name
- objective
- entry criteria
- exit criteria
- frozen scope
- excluded scope

### 2. Prepare the backbone

Commit the baseline scaffolding, design direction, or frozen spec first.

Agents should build from a stable backbone, not from an evolving conversation.

### 3. Create task packets

Prepare one or two task packets only.

Each should have:

- clear objective
- narrow scope
- measurable acceptance
- explicit forbidden scope
- expected artifacts

### 4. Run validation

Run:

```bash
python scripts/validate_coordination_files.py
```

Fix any errors before inviting collaborators.

### 5. Confirm access and instructions

Every participating agent should know:

- which branch or repo state to pull
- where to read assigned task packets
- where to write progress
- where to write incidents
- where review results will appear

## Day 1 Live Launch

### Step 1: Open only the first task set

Do not dump the whole backlog into active work.

Open only:

- one task for agent A
- optionally one independent task for agent B

### Step 2: Send minimal assignment instructions

The assignment message should be short and consistent:

`Pull latest repo state, read your assigned task packet, move it to in_progress when you start, update progress in the repo, and raise an incident if blocked.`

### Step 3: Watch for the first progress update

The first critical checkpoint is not task completion.

It is whether the agent:

- read the right file
- moved the task card correctly
- updated progress correctly
- stayed in allowed scope

If the first progress update is weak or confused, pause expansion and fix the protocol.

### Step 4: Enforce incident discipline

If an agent hits ambiguity and continues anyway, stop the pattern immediately.

The first live phase should teach:

- unclear work becomes incident
- not silent improvisation

### Step 5: Review manually and strictly

For the first live phase, the orchestrator should manually inspect:

- task card state
- progress file quality
- completion report quality
- scope compliance
- validation notes

Do not relax review during the pilot.

## First Task Selection Rules

Choose task packets that are:

- useful
- isolated
- easy to verify
- unlikely to require architecture changes

Avoid tasks that depend on:

- hidden business logic
- undocumented assumptions
- frequent spec changes
- high-stakes infrastructure changes

## What To Watch During The First Loop

These are the real health signals.

### Healthy signals

- agent starts from the task packet without extra explanation
- progress reports are understandable
- incident reports are specific
- review findings map back to acceptance criteria
- repo state is enough to reconstruct what happened

### Warning signals

- agent keeps asking what a task means even after reading the card
- progress updates are too vague to be useful
- work is declared done in chat before repo evidence exists
- review must rely on memory instead of files
- task scope drifts during execution

If warning signals appear, do not add more agents yet.

## Review Gate For Scaling

After the first one or two tasks finish, pause and assess.

Ask:

1. Did the task packet hold up without heavy chat support?
2. Did the agent report progress in the expected place and format?
3. Did blockers escalate correctly?
4. Was review possible from repo evidence?
5. Could another agent recover context without asking for a replay?

If the answer to most of these is yes, you can expand carefully.

## When To Expand

Expand only when:

- the first cycle passed validation
- review overhead stayed manageable
- incidents were understandable
- no major protocol confusion appeared

Then expand by only one dimension at a time:

- more tasks, or
- more agents

Do not increase both aggressively in the same step.

## When Not To Expand

Do not expand if:

- the first agent needed continuous hand-holding
- review had to reconstruct missing evidence manually
- tasks repeatedly crossed forbidden scope
- incidents were missing or too late
- status movement in the task-board became inconsistent

In those cases, tighten the process first.

## Recommended First Live Phase Checklist

Before launch:

- [ ] Phase objective is frozen enough
- [ ] Backbone/spec is committed
- [ ] Task packets are written
- [ ] Templates are present
- [ ] Validator passes
- [ ] Repo paths for reporting are clear
- [ ] Reviewer is ready to inspect submissions quickly

During launch:

- [ ] Only one or two tasks are active
- [ ] Each task has a named owner
- [ ] First progress update is reviewed early
- [ ] Any blocker is converted into an incident

After first loop:

- [ ] Review reports are written
- [ ] Process failures are documented
- [ ] Protocol gaps are patched before scaling

## Suggested Operating Rhythm

For the first live phase, use this rhythm:

1. orchestrator publishes backbone
2. orchestrator publishes task packets
3. agents claim and execute
4. agents update repo progress
5. blocked work becomes incidents
6. completed work enters review
7. orchestrator accepts, rejects, or reassigns
8. only then open the next task wave

## Practical Recommendation

Yes, you are very close to being able to move this onto GitHub.

But I recommend the following minimum launch shape:

- one live phase
- one or two agents
- one or two low-risk task packets
- manual review by you on every submission

That is enough to validate the workflow without turning the first rollout into chaos.

## Definition Of A Successful First Live Phase

The first live phase is successful if:

- at least one task completes end to end through the repo workflow
- at least one review is completed using the standard report
- any blocker is captured through the incident path
- the repo alone preserves enough context to continue later

If those four things happen cleanly, then the system is ready for broader GitHub collaboration.

