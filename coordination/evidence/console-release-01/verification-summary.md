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
