# Manual lifetime validation

The user requested no automatic 30-minute console shutdown and explicitly chose
manual termination for login and Agent sessions as well. Both foreground CLI
entries now default to no server shutdown timer; explicit durations remain
available. Login cookies do not have a 15-minute Max-Age. Agent sessions created
by the console have no expiry timer. Logout and server closure still close owned
Agent sessions; one-use action plans and bounded network/startup waits are unchanged.

Six affected test suites passed 201 tests with one skip. Following the final
cookie assertion update, ten focused direct-model, login/cleanup and CLI checks
passed. Node syntax, coordination validation and diff whitespace checks passed.
Tests used disposable local data; no real key or provider request was used.

The tested candidate `8251798` was cloned into a separate local installation.
The existing user-facing foreground launcher was updated to remove the explicit
1800-second argument and point to this version. Its Python process was checked
to have no `--duration` argument and the console returned HTTP 200 with the
existing direct-model privacy control. No unrelated process was stopped.
