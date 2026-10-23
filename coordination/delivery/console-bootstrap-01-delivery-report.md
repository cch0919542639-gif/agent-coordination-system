# Delivery Report

- Task ID: console-bootstrap-01
- Agent: console-bootstrap-platform-01
- Phase: console-delivery-01
- Status: DELIVERED FOR INDEPENDENT REVIEW
- Candidate: c3020c4d73b6965aa9f03ea2e60eabcaff587c99
- Branch: codex/console-bootstrap-01
- Base: accepted P1a5daa318d2d9c2b4dd4ff93081396bd452212c4a1

## Changed Files

Exactly four candidate paths:

- scripts/console_setup.py: explicit init, private staging and read-only replay,
  disabled schema4 binding, canonical-root/refusal checks, finite foreground serve.
- tests/scripts/test_console_setup.py:23 new-directory/synthetic bootstrap cases.
- docs/operations/console-download-guide.md: download/version selection,
  independent local configuration, startup/stop/restart/recovery and3.13+ selectors.
- .gitattributes: only three additional explicit -text path rules.

All26 accepted P1a program/test/doc/static raw and Git source pins unchanged.
No archive program, existing real account/DB/service or root D: files changed.

## Artifact Paths

- coordination/evidence/console-bootstrap-01/final-audit.json and final-audit.log:
  exact final commit/raw SHA256/Git blobs, unchanged P1a pins, fresh clone with
  core.autocrlf=true, explicit init/replay and authenticated seven-view proof.
- coordination/evidence/console-bootstrap-01/root-repair-result.json,
  root-repair.log, root-repair.xml: exact final source/test hashes and23 passed.
- coordination/evidence/console-bootstrap-01/focused-result.json, focused.log,
  focused.xml: original14 failed/7 passed before new-empty-staging ACL correction.
- coordination/evidence/console-bootstrap-01/repaired-result.json,
  repaired.log, repaired.xml: intermediate61 passed (21bootstrap+40console).
- coordination/evidence/console-bootstrap-01/final-result.json, final.log,
  final.xml: predecessor62 passed (22bootstrap+40console), before root repair.
- coordination/evidence/console-bootstrap-01/pre-root-repair-audit.json/.log:
  successful predecessor22a326a clone proof, retained as history.
- coordination/evidence/console-bootstrap-01/verify.py and final_audit.py:
  bounded child execution, exact commands/statuses and final provenance checks.
- coordination/evidence/console-bootstrap-01/coordination-validation.log.

## Validation Steps Performed

Windows Python3.12.10, isolated interpreter -I -B, no installed dependency,
PYTHONPATH removed and pytest plugin autoload disabled. Fresh system-temp roots;
all pytest invocations bounded300seconds. Results are distinct, not summed:

1. Original focused14failed/7passed2.71s. Native DACL read-back correctly refused
   Python mkdtemp explicit system/admin ACEs before credential creation. New empty
   staging now resets default ACL then removes inherited ACEs and grants only the
   current user. Win32 descriptor checks verify the resulting protected DACL.
2. Intermediate61passed39.88s (21bootstrap+40existing console).
3. Predecessor62passed41.91s after adding per-file ACL verification and a broadened
   login-file permission refusal regression. Native DACL verification is read-only
   on replay; existing permissions are never silently repaired.
4. Orchestrator-authorized extra invocation: final bootstrap23passed17.88s,
   child exit0. Self-review found supplied state-dir could differ from stored
   state-dir after copying a complete private directory. The explicit equality
   check and copied-directory regression close this gap. Final source/test raw
   SHA256 in root-repair-result.json match committed candidate. Permission and
   refusal checks plus real finite HTTP startup are exercised in this final run.

No fourth unchanged40-console suite was run; its latest separate history is the
predecessor62case execution. No whole-repository or Python3.13 execution claimed.

Final clean clone core.autocrlf=true preserves all26 old source pins and three
new source/test/guide raw/blob pins. In that new directory, explicit CLI init and
replay return0; finite foreground serve reports the owned PID, expires10seconds
and returns0. Login and all seven views return200/runtime_available; Viewer write
preview returns403. Private file bytes remain unchanged after serve. Tokens were
read only in memory/private synthetic fixture files, never emitted in logs/URLs/
arguments/reports. Test byte snapshots use hashes to avoid credential diagnostics.

Candidate diff check with core.whitespace=cr-at-eol passes; candidate is clean.
Coordination validator passes before submission; final authoritative status is
recorded by orchestrate.py submit and revalidated afterward.

## Known Residual Risks

Manual foreground tool only: no daemon, PID-kill/restart manager, scheduler,
autostart, provider/worker launch, task dispatch endpoint or remote publication.
The current computer's real Viewer and runtime were untouched. New Windows
permission APIs and synthetic ACL refusal paths were exercised on angeline;
another computer and Python3.13 remain independent acceptance work.

Failed/interrupted init preserves a private pending sibling and never adopts an
incomplete final setup. Operator recovery is preserve/inspect and explicitly
initialize a new state directory, not automatic migration/repair. Existing
foreign/schema/binding/account/mode conflicts refuse before writes. Serve cannot
create or migrate files. Loopback listeners and accounts in verification are
finite disposable synthetic fixtures; no production lifecycle changed.

## Recommended Handoff

console-bootstrap-review-01 independently reviews exact c3020c4, private ACL/
path/schema/refusal handling, evidence lineage and bounded fresh-clone proof.
Source stops at REVIEW, no self-acceptance. P1c must separately fix the exact
GitHub publication target/commit and obtain authorized publication, then actual
second-host download/setup/login/restart verification. P2 task assignment waits.

## Acceptance Criteria Coverage

- Small stdlib init/foreground serve: one new entrypoint, source APIs reused;
  no P1a source changes or temporary enable/disable cycle.
- Canonical schema4 disabled binding/default Viewer: existing new-directory test,
  read-only verification and seven-view clone proof.
- Idempotence/mismatch safety: final23 cases cover unchanged bytes, foreign/schema/
  root/workspace/mode/account/login conflicts, incomplete setup and copied root.
- Private external credentials: pairwise-separated canonical roots, SID-only
  directory/file ACL checks, secret-free outputs and bounded login read.
- Finite service/port refusal: owned PID/address/duration output, Ctrl+C/expiry,
  busy port and duration refusal; no process replacement.
- Tests/pins/docs: final23 exact tested hashes,26 old pins unchanged, clone flow
  and explicit version/download/setup/restart guide, all above.
