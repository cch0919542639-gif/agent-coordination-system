# Delivery Report

- Task ID: console-encoding-fix-01
- Agent: console-encoding-platform-01
- Phase: console-delivery-01
- Status: DELIVERED FOR INDEPENDENT REVIEW
- Base: c7f7dee2c356009f51fbe63434ecf0c5400e7571
- Candidate: 8a5bc1693e8f8e8ea0f476424b59d37346f44b8a
- Branch: codex/console-bootstrap-01

## Changed Files

- scripts/console_setup.py: current_sid captures binary whoami output, matches
  exactly one quoted CSV record with an ASCII SID field, decodes only that field,
  bounds output and refuses malformed/missing/failed command results safely.
- tests/scripts/test_console_setup.py:16 synthetic encoding/isolated-child/failure
  cases; existing23 bootstrap cases retained.

Exactly two candidate files changed;666 other tracked files unchanged, including
all runtime/web/controller code, ACL checks, guide and published release manifest.
No dependency, global encoding setting or environment workaround introduced.

## Artifact Paths

All evidence below is under coordination/evidence/console-encoding-fix-01/:

- provenance.json and provenance.py: exact base/remote evidence commits and hashes.
- original-console_setup.py: byte-exact published source, before repair.
- original-verification-report.md and original-encoding-diagnosis.json: exact
  already-sanitized remote report/diagnosis from4a0f61d, preserved without merging.
- red-result.json, red.xml, red.log: original source against new regressions.
- red-wrapper-note.md: raw CP950 log-preview error after native result capture.
- focused-result.json, focused.xml, focused.log: repaired Python3.12 checks.
- affected-result.json, affected.xml, affected.log: final Python3.13 affected suite.
- final-audit.json and final_audit.py: exact raw/Git hashes, final tested-byte
  binding, two-file diff, unchanged baseline and syntax/whitespace checks.
- verify.py: bounded native child execution with commands/statuses/source pins.
- coordination-validation.log: canonical board validation.

## Validation Steps Performed

Three permitted pytest invocations, each isolated -I -B, maximum300seconds,
fresh system-temp directory, plugin autoload disabled and no PYTHONPATH.
Native child returncodes, commands, interpreter and source SHA256 captured.

1. Original source:16 new SID cases selected;14failed/2passed,23deselected,
   child exit1, JUnit2.884s. Reproduces UTF8-account/CP950 decoding refusal,
   CP950-account/UTF8 refusal, raw nontext bytes, stdoutNone AttributeError
   under isolated child, malformed SID and unwrapped command failures. Raw
   logs/JUnit remain intact. Log preview itself then encountered a CP950/UTF8
   mismatch after recording child completion; preview now uses ASCII escaping,
   without changing original logs or spending another test invocation.
2. Repaired Python3.12.10 bootstrap:39passed21.56s, child0. Subsequent test ID
   labels were shortened only; exact final source/test bytes are covered below.
3. Final Python3.13.15 affected:131passed71.44s, child0 (wall73.163s):39bootstrap,
   40web,24state,28board. Existing3.13 installation used; nothing installed.
   Includes actual synthetic fresh-directory init/replay and10second foreground
   HTTP/login/seven views, Viewer403, byte preservation, canonical root/schema/
   config refusal, native directory/file DACL checks and broadened-file refusal.

The isolated synthetic child explicitly uses -I -Xutf8=0 while its environment
contains PYTHONUTF8=1; it asserts isolated mode and utf8_mode0 before extracting
the synthetic SID. UTF8, CP950, arbitrary nontext and quoted-comma account bytes
are never decoded. Command failure/timeout/missing/malformed/multiple/oversized
output fail closed with the fixed StateError; no real account name is logged.

Every current_sid caller was traced: private_directory needs it for the existing
current-user ACL grant, and require_private needs it for existing DACL identity
comparison. Only acquisition changed. Raw SID validation is stricter; original
Windows ACL checks/grants and all account/runtime behavior remain unchanged.

Final code and tests raw SHA256 equal final affected-tested hashes and committed
Git blob bytes. Compile and CR-aware diff whitespace checks pass; candidate clean.
Canonical coordination validation runs before submission and afterward.
This is a focused/affected result, not a whole-repository green claim.

## Known Residual Risks

The original published verification remains FAIL:114passed/1failed, original
CP950 decoding/None-chain and separate PYTHONUTF8 workaround. It is preserved
and not relabeled successful. Its physical host identity was not proven; this
local3.13 repair run does not prove two distinct hardware hosts or complete P1.

This source packet intentionally does not refresh portable release pins: the
published manifest still binds old source at c7f7dee. After independent acceptance,
a separate metadata refresh/review and authorized repaired publication are needed
before an actual acceptance rerun. No push, PR mutation, merge, live credential/
DB/permissions change or provider launch occurred in this task.

## Recommended Handoff

console-encoding-review-01 independently reviews exact8a5bc16, binary parsing,
red/green lineage,3.13 isolated-child and affected evidence. Source stops at REVIEW.
After acceptance, refresh pinned release metadata separately, obtain authorized
publication and repeat actual download/init/replay/login/restart acceptance.
P1 acceptance and P2/P3 planning stay gated on that outcome.

## Acceptance Criteria Coverage

- Original non-ASCII bug reproduced: exact predecessor/provenance and red14/2.
- Locale-independent acquisition: raw bytes, only validated ASCII SID decoding;
  no global UTF8/environment assumption or ACL weakening.
- Meaningful regressions/failures:16cases, including isolated UTF8-environment
  bypass, None, command failure/timeout and malformed/oversized raw output.
- Final focused/affected validation:3.12bootstrap39 and final3.13affected131,
  exact tested hashes, no runtime/web changes or product dependencies.
- Original failure/workaround retained and limits explicit; source-only local
  commit, no publication/manifest refresh or P1/second-host acceptance claimed.
