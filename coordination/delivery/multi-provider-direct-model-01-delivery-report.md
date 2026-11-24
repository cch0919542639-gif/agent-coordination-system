# Delivery Report

- Task ID: multi-provider-direct-model-01
- Agent: ORCHESTRATOR
- Phase: agent-control-center
- Status: REVIEW

## Acceptance Criteria Coverage

Direct sessions support OpenRouter, DeepSeek, Agnes AI and a custom HTTPS
OpenAI-compatible endpoint. Provider selection clears unsent keys; session
snapshots bind provider and custom base URL. OpenRouter retains the default
zero-retention provider routing and catalogue. Other providers use their own
policies, are not claimed to provide ZDR, and use example or manual model IDs.
Custom URLs reject non-HTTPS, userinfo, query strings, fragments and controls;
redirects remain forbidden. User-provided destination receives the key and text.

## Changed Files

Direct bridge, agent controller, console API, static interface, guide and tests;
no keys, user state or existing installation were changed.

## Validation Steps Performed

Direct-model, web-console and Agent suites: 118 passed, 1 skipped. Tests include
request destinations and payloads, provider privacy rejection, custom URL
validation, role/session behavior and end-to-end synthetic Agent operation.
An isolated local browser fixture showed all four choices and custom URL field.
After review fixes, the direct-model, Agent, web-console and monitor suites passed
138 tests with one skip. The two earlier monitor timeouts were traced to the
Windows venv launcher PID and fixed under multi-provider-monitor-failures-01.
Independent direct-model re-review passed 52 isolated tests; no new blocking
findings were found. Coordination validation, JS syntax and diff checks passed.

## Independent Review and Repairs

The first review found old pages could send prompts to an unintended provider,
change or stop a newer session, and a slow provider could hold a request open.
Prompt, model and stop operations now bind to the displayed session and provider;
prompt and model also bind the relevant privacy and model state. Legacy requests
are rejected and the UI synchronizes new sessions. A single direct-model request
has a 100-second deadline, after which its owned bridge is stopped. Session and
console lifetime remain manual. Independent re-review found no new blocking issue.

## Known Residual Risks

No real DeepSeek, Agnes AI or custom-provider call was made; provider-side models,
prices, capabilities and policies must be verified with a user key. OpenRouter
ZDR is not applied to other providers. Custom endpoints require trusted HTTPS URLs
and manual model IDs. A legitimate response taking over 100 seconds will time out. The running console
was not interrupted or updated; merge and publication remain pending.
