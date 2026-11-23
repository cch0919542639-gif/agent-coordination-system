# Direct model privacy choice: local validation

- Candidate source: `95197beb0dc6ea353e2321999d20fff38a2e2c22`
- User selection: ZDR by default, with an explicit per-session ordinary mode.
- Prior approved monitor and existing sessions were not stopped.

The candidate adds a user-visible retention/training notice for ordinary mode,
retains ZDR and data-collection denial by default, and binds the chosen mode to the
direct-model session. A refreshed view recovers and displays the actual session
mode. Catalogue results are restricted to text-input/text-output models; ZDR mode
also intersects them with OpenRouter's current ZDR endpoints. A catalogue entry
is not a guarantee of route availability, quota or account permission.

The affected console/agent/monitor regression passed 128 tests, with one skip,
in 164.31 seconds. After a final logout-UI reset, the direct suite passed six
tests in 5.64 seconds. Node syntax and coordination validation passed. Live
public catalogue discovery found the requested Baidu model in ordinary mode and
not ZDR mode, and excluded the incompatible decision model. No private key or
user prompt was used by automated checks.

The candidate was started as an ordinary foreground console on port 18768.
Port 8768 was already occupied and its owner was not disturbed. A real provider
request depends on the user entering their key and confirming the response.
The local candidate is not merged, pushed or released.
