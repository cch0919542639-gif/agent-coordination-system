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

Finish independent verification of the Phase 14.5 summary before beginning
the documentation-only `phase14.5-04` supervised-launch design task.

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

## 2026-09-06 Next Dispatch Gate

- `phase14.5-launcher-09` is dependency-eligible and remains READY for its
  assigned ORCHESTRATOR implementation. Its implementation must preserve the
  no-launch boundary; a real supervised process start still requires separate,
  exact operator approval.
