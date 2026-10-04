# Progress

## Current State

- Central monitor and owner-strict routing are active for the local
  `agent-usage-collector` project.
- Phase 14 local activation is accepted: a worker payload is durably written
  to a local inbox before acknowledgement and resolves the real task-card path.
- Phase 14 branch-aware monitoring is accepted: the configured worker branch
  for `usage-mvp-01` produced a `review_submitted` orchestrator delivery.
- `phase14-local-03` is accepted: the worker branch was pushed, the monitor
  detected `review_submitted`, 72 focused tests and coordination validation
  passed, and the status-projector delivery is recorded on the task board.
- `phase14-runtime-adapter-01` is accepted: its deterministic, read-only
  OpenCode/MiMo preflight is integrated with the status projector on `main`.
- Phase 14.5 contract and dry-run-only preflight are accepted, integrated on
  `main`, and pushed; no runtime launch was performed or authorized.

## Active Work

- `phase14.5-architecture-01` is accepted: it defines the repository-first
  six-agent control plane and its connector, scheduler, safety, and acceptance
  contracts. Phase B admission planning is next; no connector is enabled yet.
- `phase14.5-summary-01` is compiling the accepted and integrated Phase 14.5
  evidence in the project plan.
- `phase14.5-04` is ready but depends on that summary; it is restricted to a
  supervised-launch design and cannot implement or invoke a runtime.

## Blockers And Risks

- The focused branch-aware pytest suite exceeded the bounded local verification
  window; the accepted compatibility runner and real monitor demonstration are
  retained as evidence, with a provisioned full-suite rerun still desirable.
- Same-machine runtime state is Git-ignored by design; cross-machine delivery
  is deferred.
- OpenCode/provider credentials, model behavior, and supervised one-shot
  execution remain unverified and unapproved.

## Next Action

Independently validate the lead-agent triage/automatic redispatch policy update
before starting another Phase 14.5 task.

## 2026-09-20 Fresh Phase H Admission

- The operator granted one new exact Phase H pilot authority after Task 29's
  accepted non-secret launch projection. `phase14.5-fresh-six-worker-pilot-30`
  is the new, non-retry task packet. Independent review denied admission before
  approval materialization because the packet lacks a reviewed binding to the
  protocol-required pilot task identity and one exact run ID. No runtime,
  provider, credential, network, token, or child process action occurred.
- `phase14.5-pilot-identity-projection-31` is independently accepted. It binds
  Task 30 to the required Phase H identity and an unused exact run ID; Task 30
  is eligible for one current preflight, not a retry or automatic launch.
- Task 30's one permitted current preflight denied at the aggregate six-binding
  state gate. It stopped before admission; no approval, token, process,
  provider, credential, network action, start attestation, or concurrency
  evidence exists, and no retry or fallback is authorized.
- `phase14.5-scoped-worktree-preflight-32` is submitted for independent review.
  Its command-scoped ownership guard handling reports all six bindings current
  without persisting Git configuration; it has no pilot authority.
- `phase14.5-scoped-worktree-preflight-32` is independently accepted. The
  repair validates six bindings with command-scoped ownership trust only; Task
  30 remains terminally blocked and cannot be retried under its prior authority.

## 2026-09-03 Orchestration Planning

- The accepted controlled-orchestration architecture is now mapped to Phase
  B–H task cards in `docs/operations/phase14.5-controlled-orchestration-task-map.md`.
- `phase14.5-bootstrap-02` is the sole dispatchable implementation candidate.
  It supplies the reviewed least-privilege OpenCode profile required before
  B0's manual handoff; `phase14.5-bootstrap-01`,
  `phase14.5-controlplane-02`, and subsequent cards have hard `DONE`
  dependencies and are not
  authorization to start a connector or a runtime.
- Phase I cross-machine expansion remains intentionally unscheduled pending
  separate design approval and security review.
- OpenCode bootstrap execution is blocked pending a successful bounded runtime
  probe and provisioned worker worktree; see
  `coordination/incidents/20260903-01_opencode-bootstrap-probe-failed.md`.
- `phase14.5-bootstrap-02` is accepted. One B0 OpenCode retry is authorized
  only with its accepted least-privilege profile and the existing isolated
  worker worktree.
- `phase14.5-bootstrap-01` is independently reviewed, accepted, and integrated
  on this planning branch. Its 24 focused tests and coordination validation
  pass. The external corrective-session failure remains recorded as a connector
  capability incident; it does not invalidate the local-only handoff contract.
- `phase14.5-launcher-09` is now the required B.1 task after connector
  admission. It is explicitly a supervised single-worker launcher, not a claim
  of full Windows sandbox enforcement.
- `phase14.5-controlplane-02` is independently reviewed, accepted, and
  integrated on this planning branch. Its local-only grant validator and
  no-launch admission planner pass 33 focused tests and coordination
  validation; the stale READY card for the former uncallable owner was removed.
- `phase14.5-worktree-context-04` is independently reviewed and accepted on
  this planning branch. Its fixture-only six-identity allocation planner and
  bounded context snapshot builder pass 58 focused regression tests; no real
  worktree, runtime, network, or credential operation was performed.
- `phase14.5-lease-recovery-05` is independently reviewed and accepted. Its
  fake-clock lease fencing, terminal submission, bounded retry, incident, and
  approval-projection fixtures pass 67 focused regression tests; no runtime,
  network, credential, or real timer operation was performed.
- Phase F evidence/review projections and Phase G operator-surface projections
  are independently accepted. Phase H's safe preflight is accepted, but the
  live six-agent pilot remains blocked: the operator authorization intake is
  recorded, while six actual admitted enforcement-capable connectors, accepted
  effectful-adapter evidence, and concrete one-shot bindings are absent.
- `phase14.5-effectful-adapter-09` is independently accepted: it adds a
  fake-tested, exact-binding one-shot process boundary that requires a current
  external enforcement attestation. It creates no connector; the six-record
  provisioning task is next.
- `phase14.5-connector-provision-10` is independently accepted: it validates
  six exact in-memory connector bindings and emits one privacy-bounded incident
  when platform enforcement is unavailable. It creates no runtime or connector.
- The L1 local-control rebaseline and its separate adapter/provision boundary
  are independently accepted. L1 now has an explicit best-effort six-worker
  path, while L2 sandbox claims remain separately gated; no live pilot has run.
- The operator approved a Phase H rebaseline: L1 local controlled collaboration
  is the default acceptance path, with `best_effort` evidence only. L2
  platform-enforced isolation remains optional hardening and is required before
  any claim of enforced filesystem, process-identity, or network isolation.
- `phase14.5-local-opencode-executor-13` is independently accepted: it adds a
  fake-tested, one-shot, no-shell local OpenCode executor with an empty child
  environment. A real process start still needs a current exact approval.
- `phase14.5-opencode-network-credential-exception-14` is independently
  accepted: a precise, enabled-and-unexpired one-shot exception can pass only
  caller-supplied safe provider-configuration roots to OpenCode. Credentials
  remain opaque and are neither read nor recorded; a real process start still
  requires an accepted live runner and exact current run evidence.
- `phase14.5-local-opencode-live-runner-15` is independently accepted: its
  fixed, no-shell PowerShell wrapper runner accepts only provenance-bound
  input and an already validated exact request. It remains L1 best-effort;
  no real six-worker run has been prepared or started.
- `phase14.5-six-worker-preflight-16` is independently accepted: six clean,
  detached worktrees are pinned to the reviewed runner commit and a
  privacy-bounded preflight record is available. No OpenCode run has started.
- `phase14.5-live-approval-runsheet-17` is independently accepted: the
  launch-time fields remain explicitly unset, so the draft creates no launch
  authority and cannot be consumed before a current operator record exists.
- `phase14.5-lease-supervisor-project-context-18` is independently accepted:
  launch-time IDs, renewable lease supervision, and exact worktree context
  replace guessed total duration and arbitrary configuration roots.
- `phase14.5-pilot-approval-fanout-20` is independently accepted: one pilot
  admission fences six exact, independently consumable binding launches;
  retained-state replay is denied before spawn.

## 2026-09-06 Next Dispatch Gate

- `phase14.5-launcher-09` is dependency-eligible and remains READY for its
  assigned ORCHESTRATOR implementation. Its implementation must preserve the
  no-launch boundary; a real supervised process start still requires separate,
  exact operator approval.

## 2026-09-22 Phase H Task 38

- Task 38's fresh self-contained admission projection passed independent
  review, then its one permitted current read-only preflight denied at the
  aggregate worktree-binding gate. The task is terminally blocked; no retry,
  fallback, approval, token, runtime, process, credential, or network action
  occurred. Privacy-bounded record and incident evidence are retained.

## 2026-09-27 OpenCode recovery and Task 46

- Installed OpenCode 1.18.32 version and serve help now exit zero after package
  postinstall repair; the prior CLI startup failure is not a current blocker.
- Native Windows Desktop automation was observed working. Selecting the worker
  project was not verified, and no model prompt was sent through that UI.
- Task 44/45 remain accepted preparation-only adapters. They do not establish a
  real HTTP transport, fresh launch authority, or successful six-worker pilot.
- Task 46's reviewed one-spawn loopback schema probe succeeded on 1.18.32 and
  stopped its server. Independent result review accepted this diagnostic only.
  Nine probe tests / 17 combined regressions pass. Modern permission reply body
  differs from the injected controller; referenced request schemas remain to
  verify. No new pilot ran and Phase H is not complete.
- Session closed at the user's request (「先收工」). Work is paused pending
  user resume; closeout reran 17 focused tests, coordination validation and
  diff whitespace checks successfully. Handoff saved; no commit or push.

## 2026-09-28 Task 49 and OpenCode Connectivity

- Task 49's live API task runner, durable one-shot permission consumption, and
  exact-session supervision passed independent review and is in `done/`. Its
  checks passed: 52 focused tests (one Windows symlink skip), module compilation,
  coordination validation, and whitespace validation. No live API/runtime call
  was made by Task 49.
- Task 50 sent one read-only plan-agent OpenCode request from an empty temporary
  directory with plugins disabled. OpenCode 1.18.32 returned the expected fixed
  response, exit code 0, in about 84.9 seconds; raw output was discarded.
- Per the user's 2026-09-28 scope clarification, local acceptance is this one
  connectivity check; the remaining five agents are intended for other
  computers. This does not demonstrate task dispatch, permission reply, report
  callback, automatic redispatch, or a six-agent run.
- The invocation-boundary repository diff was not captured. The updated Task 50
  explicitly excludes repository non-mutation from acceptance and does not
  claim that it was verified. Independent review accepted the revised scope;
  no second request or six-agent run was made.

## 2026-09-29 Local Supervised Loop

- Task 51 implements the v1.18.32 loopback HTTP callbacks expected by Task 49,
  with fake-connection coverage only. Six focused tests, compilation,
  coordination validation, and whitespace validation pass. No server/API,
  model, prompt, or permission action ran. The task is waiting for independent
  review.
- The adapter only reports session completion after observing activity then
  idle. Report submission, human review, and dependency-safe next-task dispatch
  remain to be implemented locally; the five remote worker-machine setups are
  left to the user.
- Phase H remains incomplete. Any task-bound live run still needs a fresh exact
  user authorization and current launch packet.

## 2026-09-30 Local Supervised Loop Complete

- Task 51 is independently accepted/DONE. Its strict v1.18.32 loopback HTTP
  adapter connects the Task 49 callbacks and passes seven fake-transport tests;
  no live API, server, model, session, or permission call was made.
- Task 52 is independently accepted/DONE. `orchestrate next` and direct
  dispatch now fail closed on unresolved or ambiguous dependencies; review
  continuation requires an accepted review and explicit owner, then assigns
  at most one ready task without launching a worker.
- The local report flow is ready for worker-authored delivery evidence:
  `submit_task.py` moves a completed report into review, a person makes the
  acceptance decision, and the opt-in `review_task.py --continue-after-accept`
  command can assign one next task. OpenCode idle does not create a report or
  accept a review.
- Final focused validation: 63 passed, 2 skipped; changed modules compiled;
  coordination validation and `git diff --check` passed. The stale duplicate
  `phase14.5-bootstrap-01` card in `ready/` is preserved, but its duplicate ID
  is blocked from planning and dispatch.
- Five additional worker machines remain for the user to prepare. No live
  task-bound run was attempted, Phase H remains incomplete, and the current
  changes remain uncommitted and unpushed.

## 2026-09-30 Task 53 Automatic Delivery Submission

- Task 53 now detects the native same-instance loopback callbacks and requests
  a bounded task/run-bound final manifest from the worker. After exact session
  supervision reports completion, it generates a sanitized, unverified-claims
  delivery report and submits the task to `review/` through the shared
  submission checks. The submission lifecycle rechecks the exact `in_progress/`
  state and owner after reading the final message and before report creation;
  tests cover a task moving to `blocked/` and its owner being removed in that
  window. Invalid or stale output fails closed.
- The reviewer still checks actual repository evidence and explicitly accepts
  or rejects the task. Only an accepted review can request the Task 52
  one-task continuation. Automatic review acceptance remains a non-goal.
- Fake-only combined validation: 100 passed, 2 skipped. Module compilation,
  coordination validation, and `git diff --check` passed. No live API/runtime
  was called; five remote worker machines remain for the user.
- Independent review accepted Task 53 after the race fix. The task card is
  `DONE`; no commit or push was made, and Phase H remains incomplete.

## 2026-09-30 Task 54 Controller-Observed Delivery

- Task 54 removes the worker-authored final JSON manifest. The native runner
  captures a bounded in-memory snapshot of the assigned `allowed_scope` before
  the session, compares it after exact supervised completion, and generates
  the review report from controller-observed added, modified, and deleted
  paths. It does not persist file contents or hashes.
- The generated report states that validation output and risk assessment were
  not collected by the controller, so reviewers must verify them. Human review
  and the optional accepted-only continuation remain in place.
- Focused Task 49/51/52/53/54 validation: 112 passed, 3 skipped. Changed
  modules compiled; coordination validation and `git diff --check` passed.
  No live OpenCode/API/runtime was used. Independent review accepted Task 54;
  no continuation was triggered. Five other computers remain for the user,
  and Phase H is incomplete.

## 2026-10-03 Controller-Triaged Delivery Loop

- The user replaced mandatory human acceptance with lead-agent triage: stop and
  notify only when a human decision is needed or risk is identified.
- `review_task.py --controller-triage` records both answers. A clear acceptance
  moves the task to `done/` and assigns at most one dependency-ready task to the
  same owner; bounded `needs_fix` or a clear capability reassignment routes
  work to the selected owner after the review queue is clear; `paused` leaves
  it in `review/` and prints an escalation notification.
- Updated the current plan, durable decision log, review protocols, operator
  docs, validator outcome set, and handoff. Older Task 54 evidence remains a
  historical record of the policy at that time.
- No tests, compilation, coordination validation, or live OpenCode/API run was
  performed for this policy change. No worker launch, commit, or push occurred.
- Worker assignment still does not start a process. The five other computers
  remain external, and Phase H remains incomplete.

## 2026-10-04 Task 55: Controller Triage and Repeatable Delivery

- Task 55 is accepted/DONE. The lead agent records human-decision and risk
  triage; clear acceptance, bounded corrections, and safe reassignment continue
  without waiting on unrelated review cards. Escalations stay in `review/`.
- Fixed the correction-loop dead end: delivery callbacks now write immutable
  run-keyed reports, so a `needs_fix` rerun can submit again while keeping old
  task-ID-only and prior-run evidence. Repeated reviews also keep separate
  records, and task feedback links to the newest review.
- The Coordination API requires its dedicated
  `COORDINATION_ORCHESTRATOR_REVIEW_KEY`, exact `ORCHESTRATOR` identity, and
  both triage fields; no key value was provisioned or changed.
- Focused local fake-only suite: 120 passed, 2 skipped. Six changed modules
  compiled in memory; coordination validation and `git diff --check` passed.
  A Starlette/httpx deprecation warning came from the temporary API test setup.
- No live API/OpenCode/worker, commit, push, merge, or remote-machine action
  occurred. Five computers remain for the user; Phase H remains incomplete.
- Next step requires separate authorization to publish or to start a
  task-bound worker; no dependency-ready Phase 14.5 child task remains.

## 2026-10-04 Phase 14.5 Handoff Published

- With the user's authorization, the curated Phase 14.5 control-plane package was committed as `51b57d8` (`feat(orchestration): complete controller-triaged delivery loop`) and pushed to `origin/agent/orchestrator/phase14.5-controlplane-02`.
- The commit contains 58 scoped code, documentation, task-card, delivery, and review files. It excludes pytest temporary directories, pilot/approval projections, and the unrelated Phase 10 card; those local artifacts remain untouched.
- The five other computers can now sync the branch. No worker or live API was started, and Phase H remains incomplete.
