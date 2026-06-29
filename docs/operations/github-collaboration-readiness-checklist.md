# GitHub Collaboration Readiness Checklist

## Purpose

Use this checklist before opening a new phase to GitHub-based collaboration with other agents.

The goal is to answer one practical question:

**Is this phase ready to be shared with other agents without relying on fragile chat-only coordination?**

If the answer is "mostly no", keep the phase local and tighten the protocol first.

## How To Use

Review this checklist at the start of each phase.

Interpretation:

- `Ready`: safe to open GitHub collaboration for this phase
- `Ready with caution`: limited collaboration is acceptable, but only with tight orchestrator control
- `Not ready`: do not scale to multi-agent collaboration yet

Suggested scoring:

- `Yes` = 2
- `Partial` = 1
- `No` = 0

Suggested thresholds:

- `34-40`: Ready
- `24-33`: Ready with caution
- `0-23`: Not ready

## Section 1: Phase Definition

### 1.1 Phase goal is explicit

- [ ] The phase has a clear name and objective.
- [ ] The phase has explicit entry criteria.
- [ ] The phase has explicit exit criteria.
- [ ] The phase has a defined review gate before moving forward.

Why it matters:

If the phase itself is vague, task packets will drift and agents will interpret success differently.

## Section 2: Backbone and Spec Readiness

### 2.1 Backbone exists

- [ ] The orchestrator has already produced the backbone, scaffold, or main design direction.
- [ ] The backbone is committed to the repo.
- [ ] The backbone identifies what is stable and what is still open.

### 2.2 Specs are frozen enough for delegation

- [ ] The current phase spec is written down.
- [ ] The frozen parts are clearly marked.
- [ ] Open questions are clearly separated from fixed rules.
- [ ] Agents can work without needing to guess hidden intent.

Why it matters:

Do not delegate ambiguity. Delegate bounded execution.

## Section 3: Task Packet Quality

### 3.1 Task packets are actionable

- [ ] Each task has a unique ID.
- [ ] Each task has a concrete objective.
- [ ] Each task identifies dependencies.
- [ ] Each task is small enough for one agent to finish without excessive coordination.

### 3.2 Task scope is constrained

- [ ] Each task defines `allowed_scope`.
- [ ] Each task defines `forbidden_scope`.
- [ ] Each task names expected deliverables.
- [ ] Each task defines acceptance criteria.

### 3.3 Task wording is operational, not conversational

- [ ] Tasks do not rely on oral context or memory.
- [ ] Tasks do not assume the agent "already knows what we mean".
- [ ] Tasks can be executed by reading the repo alone.

Why it matters:

If a task cannot stand on its own in the repo, GitHub collaboration will collapse back into manual message relaying.

## Section 4: State Machine Readiness

### 4.1 Task states are defined

- [ ] The team uses a fixed status model such as `ready / in_progress / review / done / blocked`.
- [ ] Everyone knows which statuses agents may change themselves.
- [ ] Everyone knows which statuses only the orchestrator or reviewer may change.

### 4.2 Transition rules are defined

- [ ] There is a rule for when a task moves from `ready` to `in_progress`.
- [ ] There is a rule for when a task moves from `in_progress` to `review`.
- [ ] There is a rule for when a task becomes `blocked`.
- [ ] There is a rule for `needs_fix` or reassignment.

Why it matters:

A board without transition rules is only a visual list, not a collaboration system.

## Section 5: Reporting Protocol

### 5.1 Progress reporting is standardized

- [ ] There is a progress report template.
- [ ] Agents know when they must update progress.
- [ ] Progress reports include current step, changed files, and next step.

### 5.2 Incident reporting is standardized

- [ ] There is an incident report template.
- [ ] Agents know when they must stop and raise an incident.
- [ ] Incidents distinguish between spec blockers, environment blockers, and capability blockers.

### 5.3 Completion reporting is standardized

- [ ] There is a delivery or completion report template.
- [ ] Agents must list changed files.
- [ ] Agents must include validation steps or test results.
- [ ] Agents must include residual risks.

Why it matters:

Without standard reports, review quality becomes inconsistent and orchestration cost rises sharply.

## Section 6: Review Discipline

### 6.1 Review rules are explicit

- [ ] Reviewer identity is defined.
- [ ] Acceptance criteria are checked during review.
- [ ] Forbidden-scope violations are checked during review.
- [ ] A task is not considered complete until review passes.

### 6.2 Review outcomes are standardized

- [ ] Review can produce `accepted`.
- [ ] Review can produce `needs_fix`.
- [ ] Review can produce `reassign`.
- [ ] Review can produce `rejected` or equivalent.

Why it matters:

If review outcomes are informal, GitHub threads and repo state will drift apart.

## Section 7: Repo Structure Readiness

### 7.1 Coordination directories exist

- [ ] `coordination/task-board/` exists.
- [ ] `coordination/progress/` exists.
- [ ] `coordination/incidents/` exists.
- [ ] `coordination/completed/` or `coordination/reviews/` exists.

### 7.2 File conventions are stable

- [ ] Naming conventions are defined.
- [ ] Date or task ID conventions are defined.
- [ ] Agents know where to place each kind of report.

Why it matters:

Agents should not have to improvise repository structure.

## Section 8: GitHub Workflow Readiness

### 8.1 Branch and PR rules are defined

- [ ] Branch naming rules exist.
- [ ] PR naming or description rules exist.
- [ ] Agents know whether they work directly on branches, PRs, or patch files.

### 8.2 GitHub is being used as a shared coordination surface

- [ ] Repo is accessible to the intended collaborators.
- [ ] Agents know to pull latest state before starting work.
- [ ] Agents know where to read the assigned task packet.
- [ ] Agents know where to publish their result in the repo or PR.

Why it matters:

GitHub works well when it is the shared evidence trail, not when it is treated as a passive backup.

## Section 9: Orchestrator Control

### 9.1 Single dispatcher rule is active

- [ ] One orchestrator is responsible for assignment decisions.
- [ ] Agents do not self-assign high-risk tasks.
- [ ] Agents do not self-advance phases.

### 9.2 Reassignment path exists

- [ ] The orchestrator has a rule for reassigning blocked work.
- [ ] The orchestrator has a rule for splitting oversized tasks.
- [ ] The orchestrator has a rule for taking work back when agents are stuck.

Why it matters:

Multi-agent systems fail when delegation exists but ownership does not.

## Section 10: Recoverability

### 10.1 Repo state is enough to reconstruct work

- [ ] A new agent can recover context by pulling the repo.
- [ ] Task state and progress are not trapped only in chat.
- [ ] Delivery artifacts are committed or linked from the repo.

### 10.2 Crash recovery is realistic

- [ ] If an agent disappears, another person or agent can identify the unfinished task.
- [ ] If local tools fail, the work history still exists in GitHub and repo files.

Why it matters:

Recoverability is one of the strongest reasons to move collaboration into GitHub.

## Section 11: Scope of Collaboration

### 11.1 Low-risk rollout is possible

- [ ] The phase can be opened first to one or two agents only.
- [ ] The phase contains at least some low-coupling tasks.
- [ ] The orchestrator can review outputs without a large delay.

### 11.2 High-risk work is still protected

- [ ] Critical architecture changes remain orchestrator-led.
- [ ] Unsafe or destructive operations require additional approval.
- [ ] Ambiguous tasks are retained by the orchestrator until clarified.

Why it matters:

You do not need full decentralization on day one. Controlled delegation is enough.

## Ready / Not Ready Signals

### Strong signs you are ready

- [ ] Task cards are specific and repeatable.
- [ ] Agents can work from repo files without chat replay.
- [ ] Review and rejection rules are already understood.
- [ ] Blocked work escalates through a standard incident path.
- [ ] The orchestrator can reconstruct the phase from repo state alone.

### Strong signs you are not ready

- [ ] Tasks are still written as loose ideas.
- [ ] Acceptance criteria changes during execution without documentation.
- [ ] Agents often need hidden verbal context to act.
- [ ] Completion is often declared in chat without repo evidence.
- [ ] Nobody can tell whether a task is blocked, waiting review, or truly done.

## Final Decision

Mark one:

- [ ] `Ready`
- [ ] `Ready with caution`
- [ ] `Not ready`

## If The Result Is "Ready"

Recommended next actions:

1. Open the phase to GitHub collaboration.
2. Assign one or two task packets first.
3. Require repo-based reporting from the first agent cycle.
4. Review the first cycle before increasing parallelism.

## If The Result Is "Ready with caution"

Recommended next actions:

1. Limit collaboration to small, low-risk tasks.
2. Keep orchestrator-led assignment and strict review.
3. Tighten the weakest protocol area before adding more agents.

## If The Result Is "Not ready"

Recommended next actions:

1. Fix task packet schema first.
2. Fix reporting templates next.
3. Fix review and status transition rules after that.
4. Re-run this checklist before inviting more agents.

## Recommended Minimum Bar

In practice, the minimum acceptable bar before involving external agents on GitHub is:

- phase objective is explicit
- task packet template is fixed
- allowed and forbidden scope are defined
- progress and incident templates exist
- review outcome model exists
- repo file structure is stable
- "no repo update, not complete" is enforced

If those seven conditions are not true, collaboration may still be possible, but the coordination cost will usually be higher than the execution gain.

