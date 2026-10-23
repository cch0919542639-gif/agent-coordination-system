# Local console delivery status

2026-10-23: P1a source packaging and P1b local Windows initialization are accepted.
This is a local reviewable candidate. Publication and actual second-computer
acceptance are pending; P1 is not complete. Task creation/assignment is P2 and
is not available through this console.

Start with the self-contained [download and setup guide](console-download-guide.md).
It covers Git/version selection, Python3.12+ selectors, explicit local init,
private login handling, finite foreground startup, stop/restart and recovery.
The runtime uses Python's standard library and Git; pytest is needed for tests only.

## Provenance and portable board

Accepted code/test tip: `c3020c4d73b6965aa9f03ea2e60eabcaff587c99` on
`codex/console-bootstrap-01`. P1a tip: `5daa318d2d9c2b4dd4ff93081396bd452212c4a1`;
main base: `bfc5163af6dca4b9b7dec6b599563e3cbf984cac`. Release metadata is layered
above that accepted tip; its own commit is supplied by the release handoff.
The proposed later target is origin branch `codex/console-bootstrap-01` with a
draft PR into main. No push, PR or merge is authorized or claimed here.

The downloaded board contains the pinned main snapshot (101 cards) plus four
accepted console source/review cards (105 total). It does not contain every task
in the separate integration board currently viewed on angeline. Each computer
views its own checkout and local runtime. Only explicit Git operations exchange
tracked task changes; refreshing the browser does not synchronize computers.
Create new private configuration on each computer; never copy live accounts,
tokens, runtime DBs or ACKs between computers.

[Portable manifest](../../coordination/evidence/console-release-01/manifest.json)
pins29 accepted source/test/doc/static files and12 exact accepted board snapshots
(four DONE cards, four canonical decisions, four deliveries).
[Verification summary](../../coordination/evidence/console-release-01/verification-summary.md)
explains tests, failures and remaining gates. Copied cards/reports are historical
acceptance snapshots: references in them to archive evidence, progress, absolute
source-checkout provenance or files outside this minimal bundle are not bundled
live links. Their old delivered/review/pending wording is original history;
canonical copied decisions and this status state current acceptance. No raw logs,
transcripts, private initialization receipts or local secrets are bundled.

## Verified scope and remaining gates

P1a producer40 console and separate52 affected checks captured exit0. Independent
40-case JUnit passes, but its interrupted wrapper did not capture child native
exit. P1b final current23 bootstrap checks and independent23 checks each captured
exit0, plus independent same-host fresh-clone init/replay/finite serve with seven
views200, Viewer write403 and unchanged private bytes. Earlier61/62 runs precede
the final root-binding repair and are not final combined-suite results.

Actual second-host download/init/login/restart, Python3.13+, expanded symlink/
junction coverage and whole-repository qualification remain untested. Publication
needs a separate exact-target authorization; second-machine proof follows the
published exact commit. No daemon, remote worker launch or dispatch endpoint is
added by this delivery.
