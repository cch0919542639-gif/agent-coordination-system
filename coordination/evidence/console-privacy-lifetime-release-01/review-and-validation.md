# Direct-model privacy and manual lifetime: release evidence

Independent review of source candidate `1f4fb5a236800e9ba9330e438c56666a7d24327b`
found a cross-tab privacy race, loss of access after eight orphaned sessions, and
a release-manifest gap. The first two were reproduced with separate disposable
HTTP tests. The fixes bind each direct prompt to the displayed session ID,
model and privacy mode, and offer explicit same-account session recovery at login. The
recovery option is off by default and is available only after valid credentials;
it closes owned Agents for that account and leaves other accounts untouched.

An initial broad run found one UI error-message assertion failure (201 passed,
one failed, one skipped). After the message was fixed, the six-suite rerun passed
202 tests with one skip. A later model-binding hardening change was verified by
four affected suites (130 passed, one skipped); three additional focused tests
passed, including real Windows owned-process termination during manual recovery.
No test used a real provider or user session.

Old pages or clients that send an unbound direct prompt now receive a refusal;
refresh the console page after updating. Default ZDR policy and read-only monitor
boundaries remain; ordinary privacy mode still requires explicit selection and is
subject to account policies. Server, login and Agent lifetime remain manual by
default; explicit finite server operation and bounded individual requests remain.

The old scoped-monitor manifest is a historical record. A separate manifest
identifies this candidate's source/evidence commit and canonical Git blob hashes.
Real cross-machine operation, complete Hermes functionality, and a real provider
request with the new privacy choice remain unverified. No production publication
or merge is implied.
