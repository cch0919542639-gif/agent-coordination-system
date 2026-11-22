# Independent review: privacy and session lifetime

- Reviewed candidate: `1f4fb5a236800e9ba9330e438c56666a7d24327b`
- Baseline: `69b5ce5acde565e24cee10f3ce19bf0a28279f10`
- Result: needs fix.

1. **Cross-tab privacy race.** Two tabs sharing a login can observe different
   direct-model sessions. A stale ZDR tab can send to a newer ordinary session
   before polling refreshes the display. An independent disposable HTTP fixture
   reproduced the issue (1 passed, 2.27 seconds).
2. **Lost-cookie session exhaustion.** Closing a browser without logout can lose
   the session cookie while leaving the server session and its Agent active.
   Eight such sessions exhaust the login limit without a way to recover them
   individually. An independent fixture reproduced this (1 passed, 3.41 seconds).
3. **Release manifest gap.** The existing historical source manifest has 16 pins
   that differ from the new candidate; release status must distinguish historical
   pins and provide a current independently reviewable manifest.

The reviewer found no other actionable issues in scope. Coordination validation,
`git diff --check 69b5ce5 1f4fb5a`, and JavaScript syntax passed. Tests used
synthetic data; no real provider, private sessions or second machine were tested.
