# Current repaired delivery (2026-10-25)

- Task ID: console-github-transport-01
- Agent: ORCHESTRATOR (reassigned after worker workspace-credit failure)
- Phase: console-handoff-01
- Status: DELIVERED FOR INDEPENDENT DELTA REVIEW

## Repaired Changes

Actual allowed_scope/forbidden_scope now derives from the exact hash-bound validated card and is returned in preview/execute. RUNNING/outbox work no longer authorizes a later runner: remaining budget is recalculated after publication, after owned suspended Job construction and at wait; expired work is not resumed and owned cleanup/UNKNOWN receipts are honest. Trusted runner digest is rechecked after outbox. Shared path_key StateError is translated at card/blob/evidence boundaries into INVALID_CARD/INVALID_EVIDENCE or INVALID evidence row, with validation unchanged.

## Current Validation

final-safe-result.json binds final backend/CLI/test bytes before and after the native child.9passed/7deselected/native0 in52.65s (wall54.016), focused scope/hash/stale, invalid evidence member paths, actual timeout, and five deterministic outbox/constructor/resume/cleanup/valid deadline cases. Original7pass/1error-boundary-fail and earlier results retained. Initial60pass plus timeout1pass was earlier product bytes, not a full final regression. No unchanged broad suite repeated. Source manifest latest pins match; exact integrated commit supplied by lead. Source and tests stopped for independent delta review.

## Artifacts and Remaining Gate

Latest source-manifest.json, final-safe-run.py/result/log/JUnit; original initial-* and review-fixes artifacts remain under own evidence folder. No staging/commit by original worker, external writes, provider or live state activation. Independent repaired-commit review and portable metadata refresh still required. Runtime FINISHED remains separate from formal task acceptance.

---

Historical original delivery follows unchanged.

# Delivery Report

- Task ID: console-github-transport-01
- Agent: console-handoff-platform-01
- Phase: console-handoff-01
- Status: DELIVERED FOR INDEPENDENT REVIEW
- Candidate base:92e1248b63dee44a607296b3d63f61207b61f09a
- Branch:codex/console-handoff-sync-01
- Integrated commit:PENDING_PARENT (parallel workers do not stage or commit)

## Changed Files

- coordination_runtime/github_handoff.py: frozen HandoffService interface,
  external bound SQLite/cache, explicit Git synchronization/evidence discovery,
  READY snapshot dispatch, immutable remote claim, local inbox/outbox and approved
  finite owned Job execution. No source-worktree staging or index manipulation.
- scripts/github_handoff.py: explicit init/sync/summary/dispatch/receive and finite
  foreground watch; no installed service or schedule.
- tests/scripts/test_github_handoff.py:9 local-bare/synthetic runner scenarios.

No web/API/frontend/setup edits by this owner. Other owner changes are excluded
from this delivery. Exact raw SHA256 and computed raw Git blob IDs are in the
source manifest; parent will bind them to one serial integrated commit.

## Artifact Paths

All evidence under coordination/evidence/console-github-transport-01/:

- source-manifest.json: source/CLI/test raw pins, raw blob IDs and split coverage.
- final_audit.py: final hash/compile/whitespace check and exact timeout-only test
  function comparison; product bytes match both last verification invocations.
- pre-timeout-repair-tests.py: exact affected-run test bytes reconstructed and
  verified against that invocation's recorded SHA256.
- focused-result.json/.log/.xml: collection error from scripts namespace shadowing.
- repaired-result.json/.log/.xml:4failed/5passed, inbox insert placeholder defect.
- affected-result.json/.log/.xml:60passed/1fixturefailed235.23s (backend+state/board).
- timeout-repair-result.json/.log/.xml:1passed/8deselected32.25s, exact repaired case.
- verify.py: bounded interpreter/commands/native exits/temp roots/tested pins.
- coordination-validation.log: canonical board validation.

## Validation Steps Performed

Windows Python3.13.15 isolated -I -B, no dependencies installed, fresh system-temp
fixtures, plugin autoload disabled. All native children finish within300seconds;
none interrupted. Git pushes in tests target only a newly created local bare
fixture. Original repository files/index are checked unchanged by end-to-end tests.

Distinct preserved executions:

1. First invocation: native2/collection error. Existing tests/scripts package
   shadows namespace scripts.coordination_common. Fixed imports to the existing
   repository direct-helper convention; original result retained.
2. Second:4failed/5passed104.60s/native1. All four receive failures traced to an
  8-column SQLite inbox INSERT with9placeholders; fixed once.
3. Third:60passed/1failed235.23s/native1. Product end-to-end, claim-before-Job,
   dedupe, outbox replay, identity/project/hash/revision refusals and evidence
   verifier pass, plus24state/28board checks. Only timeout fixture failed because
   it edited the trusted script without updating its configured expected hash;
   product correctly refused RUNNER_CHANGED before launch.
4. Parent authorized one extra timeout-focused invocation:1passed32.25s/native0,
  8deselected. Test now supplies the intended script/hash/one-second timeout in
   the trusted local config. Product and CLI bytes unchanged from run3. Exact
   before/after test hashes plus AST check prove only that test function changed.

This is61distinct green cases through split validation, not a fictitious single
all-green61case run. No remaining failure is hidden or relabeled successful.

Representative verified behavior:

- Constructor is nonmutating and summary is local/read-only; missing/foreign
  state refuses, identical initialization preserves DB bytes.
- Sender preview does not publish. Explicit dispatch binds READY card bytes,
  configured peer, code and queue expectations. Stale cards/revisions/queues refuse.
- Two separate clone/stores with the same peer identity cannot both execute an
  existing immutable remote claim. Spy verifies matching remote run_id before
  actual JobProcess construction/resume. Real synthetic Job exits0 with stopped
  tree; replay produces exactly one marker line.
- Failed FINISHED receipt publication retains durable local outbox; retry sends
  receipt and never executes again. Interrupted RUNNING becomes UNKNOWN with no
  blind rerun. Changed runner hash refuses. Timeout returns FAILED with real
  exit/stopped-tree evidence, no retry.
- Discovery automatically enumerates configured evidence refs and manifests.
  Hashes are checked before results/JUnit. Supported actual5002422-style proof
  requires fixed native exits (0, conflict2), two finite login/view cycles, all
  seven views200/runtime-available, Viewer403, private/schema/byte-preservation
  flags, exact revision and no encoding workaround. Report-controlled expected=1
  does not make a failed native exit acceptable. Bad digest/native/schema/JUnit/
  workaround evidence is INVALID; other revision STALE; reported failure FAIL.
- Unrelated UNASSIGNED legacy cards with descriptive unsupported scopes do not
  prevent acceptance discovery. Eligible selected cards remain strictly checked.
- Offline fetch preserves last successful freshness and exposes error rather
  than marking unknown transport healthy. Safe summaries omit paths/argv/bodies.
- CLI watch budget validation rejects121cycles without setup mutation; scheduled
  wait and actual wall deadline cap7200seconds, propagated into Git/runner waits.

Final syntax, owner-source whitespace and canonical board validation pass.
No worker git add/commit, real GitHub write, provider call, live account/runtime
change, permanent watch or formal task acceptance occurred.

## Known Residual Risks

Git identities are cooperative configuration, not hardware attestation. Remote
queue writes rely on immutable claim objects and fast-forward CAS; the focused
suite covers stale expectations and competing identity replay, but does not force
a simultaneous two-process remote push race. Independent review should probe that
boundary and unsupported native containment/failure receipts. Existing JobProcess
provides process-tree ownership, not a filesystem sandbox; the runner is explicitly
locally trusted. State/config migration and UNKNOWN recovery are manual by design.

Real GitHub dispatch/worker activation remains off. Evidence VERIFIED_PASS is a
technical report status and never formal REVIEW acceptance/DONE/merge. Source
portable publication metadata is not refreshed by this task.

## Recommended Handoff

Parent serially commits the disjoint backend/UI sources, verifies these exact
source pins and hands integrated version to console-handoff-review-01. Source
stops at REVIEW. Independent race/receipt/path/role checks and reviewed release
metadata precede any separately authorized real handoff activation/publication.

## Acceptance Criteria Coverage

- Frozen service/finite CLI/external bound cache+state: implemented in two files.
- Claim/dedupe/revision/runner/owned Job: local-bare synthetic proof and failure/
  replay checks above; no formal lifecycle acceptance by runtime.
- Automatic hash/JUnit/revision/environment discovery and safe cached freshness:
  positive and seven negative evidence variants, offline/legacy-card regression.
- Local end-to-end and outbox/failure tests: split61case green coverage with exact
  product byte equality and original red histories; no original index mutation.
