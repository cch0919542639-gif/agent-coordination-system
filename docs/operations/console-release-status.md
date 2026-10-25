# Integrated console candidate for main review

Updated2026-10-25. PR10 is merged into the bootstrap branch at
c3c6a383297326213b3c9904e9bfcfc3b7264fc6. Its product/test blobs are the reviewed
source311dc1f plus unchanged console/SID source. Entry guards passed110 relevant
regressions/native0 and independent OpenCode static review with no blocking finding.
The following metadata layer preserves those source blobs and refreshes the guide
and integrity inventory. Exact final publication state is recorded by Git/PR6.

Original92e1248 passed131tests in the original CP950/no-UTF8-override environment
(evidence5002422), including two finite login/restart cycles and private byte
preservation. This closes the original SID technical HOLD. It does not claim a
new second-machine run against this integrated candidate. Originalc7FAIL114/1,
optional reviewer harness failures and previous partial runs remain history.

The current manifest pins31 source/test/doc/static paths and21 accepted snapshots
(seven DONE cards, seven canonical reviews, seven deliveries). The original18
snapshot bytes remain unchanged. The two legacy entry scripts and new snapshots
use explicit -text attributes; their stored blobs are unchanged from c3c6a38.
The board has109cards including the integration-readiness record. Task state is
separate from publication/merge state; select the final supplied commit.

The current integration check result is in
coordination/evidence/console-main-readiness-01/ and its delivery report. The integrated eight-file regression run passed241tests/native0 in156.063seconds.
Fresh local autocrlf clone verified52raw/blob pins,109cards, isolated imports,
both CLI help entries and validator; clone remained clean. The readiness record
is accepted after these deterministic checks. Exact-head main promotion remains
a separate final operation, recorded in Git/PR6 rather than predicted here. No live
provider, task dispatch, watch, service or schedule is enabled; default Viewer
and disabled runtime remain. Real peer operation belongs to separate draftPR9.

The reused marker guard is a preflight check, not an atomic cross-process lock.
Whole-repository, broader junction/symlink and production qualification remain
outside the claims. Browser refresh reads the local checkout; create private
state separately per computer and never copy tokens, DBs or ACKs.

## Historical release status (superseded)

# Repaired console candidate: acceptance HOLD

2026-10-25: the Windows SID encoding repair is accepted locally at code/test
commit `8a5bc1693e8f8e8ea0f476424b59d37346f44b8a`. This metadata layer prepares
a repaired release; it has not been published. P1 acceptance remains HOLD until
fresh exact-release download/init/replay/login/stop/restart in the original failing
environment succeeds. P2/P3 planning waits for that result. Task creation/assignment
is not available through the console.

Original release `c7f7dee2c356009f51fbe63434ecf0c5400e7571` was published on
origin `codex/console-bootstrap-01` with draft PR6 into main; no main merge is
claimed. Evidence `4a0f61d76c78ac5bf85f61c996c8c77a539ea970` reports its original
initialization acceptance FAIL:114passed/1failed under CP950/non-ASCII account
output. The later PYTHONUTF8 workaround does not qualify that acceptance.
Physical host identity is unproven; this repair does not prove two distinct hosts.

## Use the repaired source

The [download/setup guide](console-download-guide.md) covers exact-version
selection, Python3.12+ selectors, new private initialization, local login and
finite foreground stop/restart. The SID repair requires no PYTHONUTF8 workaround:
command output stays bytes, only a validated ASCII SID field is decoded, and
account-name bytes are never decoded. Existing permissions/ACL checks remain.
Runtime uses Python's standard library and Git; pytest is needed for tests only.

Accepted initial bootstrap: `c3020c4d73b6965aa9f03ea2e60eabcaff587c99`;
P1a packaging: `5daa318d2d9c2b4dd4ff93081396bd452212c4a1`;
main base: `bfc5163af6dca4b9b7dec6b599563e3cbf984cac`. The repair changes setup
and its tests; the guide now adds revalidation instructions. The release handoff
supplies the later metadata commit; no document contains its own commit SHA.
Repaired publication to origin `codex/console-bootstrap-01` and draft PR6 update
require a separate exact-target authorization; no remote action occurs here.

## Portable board and evidence

This checkout contains main's101card snapshot plus four earlier accepted console
cards and two accepted encoding source/review cards:107total. It is separate from
the larger integration board currently viewed on angeline. Each computer views
its own checkout/runtime; explicit Git operations exchange tracked changes.
Browser refresh does not synchronize computers. Create new private state per
computer; do not copy live accounts, tokens, runtime DBs or ACKs.

[Manifest](../../coordination/evidence/console-release-01/manifest.json) pins29
source/test/doc/static files and18exact snapshots (six DONE cards, six canonical
reviews, six deliveries). Two source/test pins supersede c7f7dee; the guide pin
identifies this metadata layer separately. Prior12snapshots remain unchanged.
[Verification summary](../../coordination/evidence/console-release-01/verification-summary.md)
retains failure and test lineage. Copied reports/cards are historical snapshots:
archive evidence/progress paths or absolute source-provenance references outside
the manifest are not bundled live links. Their prior pending wording remains
history; copied canonical decisions record local acceptance. No raw logs, private
initialization receipts, transcripts or live private configuration are bundled.

Final Python3.13 affected131tests captured native0; independent isolated3.13 SID16
captured native0. Earlier red14fail/2pass and focused3.12bootstrap39 are separate.
Optional independent boundary probes have two harness failures and remain
incomplete, not green. These local checks do not replace original-environment
acceptance. Whole-repository and broader symlink/junction qualification remain
outside scope. No daemon, worker launch or task dispatch endpoint is added.
