# Integrated candidate verification (2026-10-25)

Source c3c6a38 includes accepted PR10 entry guards. Current fixed-source integrated
regression passed241tests/native0 in156.063seconds (single eight-file invocation).
Fresh local autocrlf clone at eb312738fadc0fd41ed6fe4577fae90e40c562f8 passed52raw/blob pins,109cards,
isolated imports, both CLI help entries and validator, with clean status.
Final metadata acceptance adds no source/test changes. Regression and clone results are recorded in ../console-main-readiness-01/ and its
delivery report. Earlier92e1248CP950131pass applies to that exact earlier release.
Manifest now pins31source paths plus21accepted snapshots;18prior snapshots remain
unchanged. The original failures and optional harness limits below remain history.

## Historical verification summaries

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
