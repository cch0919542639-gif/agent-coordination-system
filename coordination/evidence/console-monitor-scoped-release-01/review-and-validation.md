# Scoped console and monitor: review and validation

The source candidate `3dc00f599779f3d12efd6ca4bd8a5e8f6b640fa8` was
independently reviewed against main `d6c4578d5278f92444b83ffa1949ec5b40891c33`.
The reviewer found no other reproducible issue in the reviewed program and
read-only authorization scope. The review identified a packaging gap: the old
historical manifest contained eight source pins that differed from this candidate,
and the current review evidence was not available in the candidate. This release
record and a separate manifest address that gap without changing the old manifest.

Independent focused validation used disposable fixtures and no provider:

```
python -B -m pytest tests/scripts/test_console_monitor.py tests/scripts/test_direct_model.py tests/scripts/test_agent_control.py::test_job_piped_input_is_owned_and_separate_from_argv tests/scripts/test_agent_control.py::test_http_role_csrf_and_session_isolation tests/scripts/test_agent_control.py::test_agent_deadline_stops_owned_process_while_console_lock_is_held -q --tb=short
25 passed in 48.84s; exit 0
```

The earlier six-suite integration check passed 199 tests with one skip in
249.06 seconds; the skip was unavailable Hermes Python. Its first invocation
incorrectly named a nonexistent test file and ran no tests; the corrected run
produced the stated result. A fresh Python virtual environment without added
packages successfully imported the runtime and displayed both setup and monitor
CLI help. Local headless browser tests exercised Viewer monitoring and ordinary
Administrator login against disposable data. The foreground monitor stopped
successfully. No actual cross-machine test, visible desktop interaction, full
Hermes test, or provider call is claimed by these checks.

Additional focused checks for the shared process guard passed four native state
controller cases, three parallel runtime cases and one local Git handoff case.
A broader 66-case regression
was stopped after approximately five minutes because the local Git cases were
too slow; it is incomplete and is not counted as a pass.

The final manifest identifies an exact source/evidence commit and hashes its
canonical Git blobs. This is an integrity aid, not a cryptographic guarantee of
publisher identity. Review and validation evidence do not authorize production
activation, merge or publication.
