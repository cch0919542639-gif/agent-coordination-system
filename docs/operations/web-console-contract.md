# Phase5 local Web console contract

Frozen before implementation, 2026-10-16. Scope: trusted local operator on this
Windows host; no hostile OS user protection or public network deployment.

## Transport and identity

`python -B -m web.api --repo REPO --db DB --workspaces ROOT --project-id ID
--auth-file EXTERNAL_JSON --port 8765 --duration 300` binds only IPv4 127.0.0.1.
All paths explicit; no DB creation/migration, mode activation or default accounts.
Lifetime 10..1800 seconds, port 1024..65535 (0 for owned tests only).
Auth file outside repository and workspace root, maximum16KiB, schema_version1,
users1..8 unique `{username,role,token_sha256}` records; roles viewer/operator/
administrator. Token must be random32bytes encoded URL-safe without padding;
only SHA256 digest stored. File permissions remain the operator's responsibility.

Login POST JSON exchanges username/token for random HttpOnly SameSite=Strict
host-only cookie and independent session CSRF token held in JS memory. No browser
storage, query credentials, raw logs, external resources or permissive CORS.
Sessions expire after15minutes, maximum8. Failed login budget5/minute per server.
Exact Host and mutation Origin must equal server loopback origin; foreign GET
Origin also refused. POST requires JSON and CSRF except login. Maximum body16KiB,
response256KiB; fixed routes/static allowlist, no arbitrary file access. Request
socket timeout2seconds; four active request handlers maximum. No proxy support.
Loopback HTTP cannot offer transport encryption; use only this host. A compromised
local browser/profile or OS is outside scope. Cookie name includes port.

## Read model and UI

Seven views: Overview, Task Board, Agent Monitor, Workspace Explorer, Review Center,
Events, Settings. Board-first metadata is authoritative for formal lifecycle;
runtime phase and persisted process receipts are separately labelled. No invented
health/progress or raw transcripts, argv, absolute paths, event artifacts, review
bodies or task bodies. Canonical review headers are historical records, not fresh
acceptance/validity checks. No arbitrary workspace file browsing.

Board scan maximum2048 cards/8MiB total,64KiB per card, cached10seconds. Directory
enumeration uses streaming scandir with a4096 total-entry ceiling. Browser
requests at most100 cards/runs/evidence/reviews per page; events use incremental
sequence cursor with default50/max100. Read-only StateController schema4 snapshots
validate project/repository/workspace binding. Missing DB is explicit unavailable,
never creates a file; invalid schema/binding returns a private error. SQL counts
are exact for bound project and pages explicitly indicate truncation/more.
Only current view polls,5seconds visible/60seconds hidden, one pending request;
events DOM retains at most100 rows. No progress animations/background workers/CDN.

## Mutations

Viewer reads only. Operator may inspect a run and obtain controller dry-run plans.
Administrator may execute a preview using a session-bound random60second one-use
plan token. Preview binds exact validated action/arguments; execute accepts only
that token. Controllers recheck existing DB version/fence, resource sequence,
intent preimage and quiescence. Expired/used plan requires a new preview.
Allowed actions: recovery.reconcile; resource.probe/reset; board.reconcile/cancel;
parallel.disable. Probe preview samples only, execution may open the resource latch.
No generic command/SQL/Git endpoint, worker start/kill, provider dispatch, enable,
permission editor, evidence acceptance or ref publication. Operator capabilities
cover recovery requests and plans for currently accepted controllers; actual
provider dispatch belongs to Phase6. Authentication is web access control, not
an attribution guarantee added to older Controller event receipts.

## Validation and limits

Owned finite D-only fixtures exercise HTTP attacks, roles, one-shot preview and
stale guards, real backend projection, missing/foreign database, browser operation
and hidden polling. Record measured API-process CPU and working set while idle
with browser polling; target CPU<3%, memory<=150MiB on tested host. This is not
a benchmark for every older machine or for future provider processes.
No production runtime activation; preserve accepted source and legacy service.
Independent review then separate docs task follows acceptance.

Design references: [Python HTTP server](https://docs.python.org/3.12/library/http.server.html)
and [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
The stdlib server is restricted to local finite trusted use, not public hosting.

Pre-acceptance amendment (2026-10-16): real204-card polling measured3.28% CPU with
5second board cache, above the<3% target. Cache lifetime is10seconds for repository
metadata only; browser polling remains5/60seconds and runtime snapshots stay fresh.
Old contract/code and above-target measurements are retained in external D archives.
