# Console source candidate (P1a)

This is a local source candidate, not a published or initialized deployment.
Source: archive `b31267f3ba78edd891dd2fedfa955c2f34dd5d05`.
Base: main `bfc5163af6dca4b9b7dec6b599563e3cbf984cac`.

The console uses Python 3.12 standard-library modules. Import from the repository
root with `python -B -c "import web.api"`. The launch contract is in
[the console guide](web-console-guide.md); its paths and credentials must be
provided explicitly. No default accounts, DB, activation, autostart or bootstrap
are included. Historical evidence links in copied contracts refer to the archive
and are not part of this minimal candidate.

The source includes the transitive Python import closure of `web.api`, including
lazy recovery/native process-guard imports, and all three static assets. The
baseline `scripts/coordination_common.py` is the one authorized replacement:
its existing helpers now refuse shared writes with a parallel-mode marker.
Other tracked baseline files remain unchanged.

Existing verification entry points are `tests/scripts/test_web_console.py`,
`test_state_controller.py` and `test_board_projection.py`. The copied
`test_parallel_runtime.py` supplies their fixtures; its legacy worker-routing
tests are outside P1a and are not a claim of compatibility with the retained
baseline worker-poller/local-loop implementations.

Next packet P1b must provide explicit, repeatable local path/role configuration,
safe schema4 initialization and disabled binding, finite startup and PID/lifetime
handling. It must refuse conflicting accounts, databases, bindings and busy
ports. P1c separately governs independent review, authorized publication and
second-host download verification. Task creation/assignment UI remains P2.
