# Handoff verification continuation

## Current accepted handoff candidate (2026-10-25)

The bounded handoff feature is accepted locally at source commit
`1feeca789ccfd6985f9496e1cce123cc67829160` on
`codex/console-handoff-sync-01`. This feature remains unpublished. Existing draft
PR6 still contains repaired bootstrap `92e1248b63dee44a607296b3d63f61207b61f09a`;
no feature push or main merge has occurred. Use the exact later release commit
supplied by the handoff when publication is authorized.

The other computer's evidence `5002422d33d85b3def31541241521de06fd5527b`
technically requalifies92e1248:131JUnit passes/native0 under CP950, utf8mode0 and
no PYTHONUTF8 override, two finite login/view/restart cycles, private bytes
unchanged. Human identifies the other computer; no cryptographic physical-host
or production qualification is claimed. The SID revalidation HOLD is released.
Originalc7f7dee evidence4a0f61d remains FAIL114/1; its UTF8 workaround is not
acceptance. These outcomes apply to different versions.

Actual read-only GitHub discovery using the new backend independently returned
FAIL for originalc7f7dee and VERIFIED_PASS131 for92e1248, with last_error null
(11.038seconds). It used disposable external state and existing read access;
no queue write, dispatch, receive, watch or runner ran. This does not qualify
real cross-computer execution of the new feature.

Default console_setup init creates a Viewer account, which cannot dispatch.
Dispatch execution requires an explicitly provisioned Administrator who creates
and confirms the plan in that same session; Operator can preview only.
Choose roles during explicit new local setup. Existing credentials are not
upgraded or migrated here. See the [external authentication and role guide]
(../../../docs/operations/web-console-guide.md#external-authentication) for deliberate operator setup.

See the [handoff guide](../../../docs/operations/github-handoff-guide.md) for external per-computer
configuration, explicit initialization, role-bound preview/confirmation and
finite foreground watch. Each computer needs its own locally activated watch
terminal; navigation and5second console refresh only read local cached summary.
A coordinator watch syncs; a worker syncs/receives its own assignment. Execution
requires both locally approved bound runner/execution_enabled and --execute.
No service, schedule or autostart is installed. Existing READY assigned cards
can be handed off; task-authoring UI remains absent. Runtime FINISHED/FAILED/
UNKNOWN never means formal reviewed/DONE. No real provider or peer activation,
new credentials or automatic review/merge is authorized by this release.

Current focused source evidence: backend9pass/7deselected/native0; separate
UI19pass/13deselected/native0. Independent delta6pass/1fixture-fail/native1 is
retained honestly; separate actual-backend HTTP probe native0/6.970seconds
verifies scope preview/confirmation. The minimal reviewer controller fixture
failed before original HTTP scope assertions; the earlier execution claim was
corrected. No7green or combined full-suite claim. Older backend60+1, UI30/92,
repair131/16 and original failure runs remain distinct historical executions.

Portable manifest contains35source/test/doc/static pins and30accepted snapshots
(10DONE cards,10canonical decisions,10deliveries),65files and111board cards.
All prior18snapshots remain byte-exact. New snapshots cover remote reacceptance,
backend, UI and independent review. Their archive evidence links are historical
and unbundled unless pinned; no private logs, tokens, DBs or transcripts ship.
Manifest hashes provide integrity, not independent authenticity. Whole-repository
and broader symlink/junction qualification remain outside scope.

Earlier sections below are dated history: old HOLD/publication-pending wording
does not describe current92acceptance or this local feature status.

# Encoding repair verification continuation (2026-10-25)

Current accepted code/test tip:8a5bc1693e8f8e8ea0f476424b59d37346f44b8a.
Original publishedc7f7dee and evidence4a0f61d remain historical facts: original
acceptance FAIL114pass/1fail, CP950/non-ASCII whoami decoding failure. Subsequent
PYTHONUTF8 workaround is not acceptance, and physical distinct-host identity is
not proven. P1acceptance HOLD and P2/P3planning deferred until a fresh exact repaired
release download/init/replay/login/stop/restart succeeds in that original environment.
Repaired publication still needs exact-target authorization; no remote edits here.

Repair captures raw whoami output, validates one quoted record and decodes only
its ASCII SID field. Account-name bytes never decode; command/output errors fail
closed. Existing ACL checks/grants and other setup behavior are unchanged.

| Distinct repair execution | Result | Limits |
| --- | --- | --- |
| Original source with16new regressions |14failed/2passed, native1, JUnit2.884s|red reproduction;23deselected; separate CP950 preview error after captured exit |
| Repaired Python3.12 bootstrap |39passed21.56s, native0|test labels later shortened; final byte binding below |
| Final Python3.13.15 affected |131passed71.44s, native0|39bootstrap+40web+24state+28board; exact final source/test hashes |
| Independent Python3.13 isolated SID |16passed1.60s, native0|23deselected;-I -Xutf8=0 with ignored PYTHONUTF8=1 environment |
| Optional independent boundary children |two native1 harness failures|first incorrect length fixture; corrected child later incorrect lone-CR refusal expectation; incomplete, not green |

Five valid boundary cases and one oversized refusal ran in the corrected optional
child before its harness assertion failed; later optional cases were not run.
These failures do not establish a product defect or a passing boundary smoke.
No new pytest invocation is made for this metadata layer. Final131 includes
synthetic native ACL/init/replay/finite HTTP/login/seven-view/Viewer403 checks,
not actual original-host or two-physical-host acceptance. Existing broader
symlink/junction and whole-repository limits remain. Suites must not be summed.

Manifest now carries29raw/blob source/test/doc/static pins: two repaired code/test
identities from8a5bc16 supersede predecessor pins, while guide provenance is this
metadata layer. Prior old pins are retained under superseded_pins. Six new exact
repair DONE/review/delivery snapshots expand12to18; board105to107. All prior12
snapshot bytes stay unchanged. Existing source attributes stay intact; six new
snapshot rules are explicit -text. Remaining archive evidence links in copied
snapshots are historical/unbundled. No raw logs/private receipts are distributed.

To verify a download from the repository root, load manifest.json using json,
then check hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() equals
item['sha256'] for source_pins + accepted_board_snapshots (47files). Git blobs
identify the same pinned bytes. Manifest equality is integrity, not independent
authenticity; select the exact handed-off repaired release commit. Current source
acceptance supersedes old source pins, not the failed original acceptance outcome.

The original2026-10-23 summary below is byte-preserved dated history. Its previous
current-version,41files,105cards and publication-pending statements are superseded
by this continuation and release status; original test outcomes remain unchanged.

# Portable verification summary

This evidence-only release packet reruns no product tests. The manifest pins
accepted code/test tip c3020c4 and selected exact board acceptance snapshots.

| Evidence | Observed result | Scope |
| --- | --- | --- |
| P1a producer console |40 passed26.92s, captured exit0|5daa318 raw tested source |
| P1a producer affected |52 passed7.50s, captured exit0|separate state/board invocation |
| P1a independent console |40-case JUnit,0fail/error/skip;37.31s log|wrapper interrupted; native child exit unknown;300s enforcement ended |
| P1b original producer |14failed/7passed2.71s|native ACL refusal before staging repair |
| P1b intermediate producer |61passed39.88s|21bootstrap+40console, intermediate source |
| P1b predecessor producer |62passed41.91s|22bootstrap+40console, before root repair |
| P1b final producer |23passed17.88s, captured child exit0|current c3020c4, explicitly authorized fourth invocation |
| P1b independent |23passed20.15s, captured child exit0|current c3020c4,300s bound, no interruption |
| P1b independent fresh-clone smoke |init/replay/10sserve exit0; seven views200,Viewer403;private bytes unchanged|same Windows/Python3.12 host;120s wrapper bound |

These are distinct executions, not a summed suite. No final40-console rerun,
Python3.13+ run, second-host proof or whole-repository green claim is made.
P1a original5415bd9 normalized CRLF blobs despite correct tested raw bytes;
path-specific -text rules and5daa318 repaired blobs without retesting unchanged
raw bytes. P1b original ACL refusal drove new empty staging/DACL protection;
per-file ACL refusal and supplied-versus-stored state-root binding were repaired
in subsequent source versions. Original failures remain archive history.
Windows symlink creation error1314 left P1a symlink refusal untested; broader
symlink/junction tests and legacy fixture guard cases remain unqualified.

P1a26 exact raw/blob pins and P1b three added source/test/guide pins form the29
unchanged accepted files in manifest.json. P1a622 baseline identities and P1b649
other existing identities were independently checked; fresh core.autocrlf=true
clones preserved pinned bytes. Identity proofs are not full regression coverage.
.gitattributes appends12 path-specific snapshot rules; its old29rules stay intact.
Only README, release documentation/evidence and12 snapshots change in this
metadata layer; no product source/test or runtime changes.

The twelve copied files are historical board snapshots, including canonical
accepted decisions for console-package-01, console-package-review-01,
console-bootstrap-01 and console-bootstrap-review-01. Their archive evidence/
progress references are not shipped unless listed in manifest.json. No raw logs,
transcripts or private initialization receipts are bundled. Source checkout paths
inside snapshots identify historical provenance, not private runtime settings.

## Check a downloaded copy

From the repository root, use your Python3.12+ interpreter to load manifest.json
with json.loads, then verify hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()
equals item['sha256'] for every entry in source_pins and accepted_board_snapshots
(41 files). Git blob IDs also identify accepted content. This verifies integrity
against the supplied manifest, not external authenticity: select the exact release
commit supplied in the handoff. Publication target/commit authorization and actual
second-computer acceptance remain separate gates; task dispatch is later P2.
