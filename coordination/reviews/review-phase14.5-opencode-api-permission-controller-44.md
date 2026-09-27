# Independent Review: phase14.5-opencode-api-permission-controller-44

- Review ID: `review-phase14.5-opencode-api-permission-controller-44`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_34`
- Task ID: `phase14.5-opencode-api-permission-controller-44`
- Phase: `phase14.5-phase-h-live-pilot`
- Reviewed At: `2026-09-25`
- Decision: accepted

## Summary

Accepted. The standard-library-only core is transport-free, compares the four
permitted pending fields to its exact supplied binding, consumes its identity
before invoking the injected callback, and sends only an explicit
non-remembered `once` response.

## Findings

## Accepted Artifacts

`scripts/opencode_permission_controller.py` and its focused test file, within
the original transport-free acceptance scope. Heading backfill dated 2026-09-27.

## Detailed Findings

The prior P1 is resolved. `_valid` now requires `_digest` for every pending
and binding resource digest; `_digest` accepts only 64 lowercase hexadecimal
characters. The new regression covers short, non-hex, uppercase, and
cross-wired digests and confirms zero injected callbacks. Exact input still
produces only `{"response": "once", "remember": false}`. Mismatches,
malformed maps, and replay deny before callback; the identity is consumed
before callback, including an unsuccessful reply path.

## Required Changes

None.

## Validation Check

- `python -m pytest tests/scripts/test_opencode_permission_controller.py -q`
  — 4 passed (with an unrelated pytest-cache permission warning).
- `py_compile scripts/opencode_permission_controller.py` — passed.
- `git diff --check -- scripts/opencode_permission_controller.py
  tests/scripts/test_opencode_permission_controller.py` — passed.

## Scope Compliance

The reviewed delivery files are within Task 44's allowed scope. The core is
standard-library-only and contains no HTTP, socket, subprocess, environment,
configuration, or credential access. This review made no runtime, server,
network, provider, credential, configuration, merge, or push action.

## Residual Risk

This is preparation only. A later separately reviewed adapter must still bind
the core to loopback transport and a current approval; this review does not
authorize a server or runtime launch.
