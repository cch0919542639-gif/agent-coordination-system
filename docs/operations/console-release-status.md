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
