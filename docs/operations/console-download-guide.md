## Main-integrated handoff candidate (2026-10-25)

This candidate combines accepted handoff source1feeca7/a82c5a7 with mainc3682d3,
including the reviewed legacy entry guards. It is not the older handoff-only or
bootstrap-only package. Select the exact final commit supplied by PR9; runtime
completion still never accepts formal tasks automatically. Original92e1248CP950
acceptance remains scoped to that release. The current manifest/status replace
older pin counts and release-pending/HOLD wording below; operational setup steps
remain useful. No real peer, runner, provider or schedule is activated here.

## Current accepted handoff candidate (2026-10-25)

The bounded handoff feature is accepted locally at source commit
`1feeca789ccfd6985f9496e1cce123cc67829160` on
`codex/console-handoff-sync-01`. This feature remains unpublished. Existing draft
PR6 still contains repaired bootstrap `92e1248b63dee44a607296b3d63f61207b61f09a`;
no feature push or main merge has occurred. Use the exact later release commit
supplied by the handoff when publication is authorized.

The other computer's evidence `5002422d33d85b3def31541241521de06fd5527b`
technically requalifies92e1248:131JUnit passes/native0 under CP950, utf8mode0 and
no PYTHONUTF8 override, two finite login/view/restart cycles, private bytes
unchanged. Human identifies the other computer; no cryptographic physical-host
or production qualification is claimed. The SID revalidation HOLD is released.
Originalc7f7dee evidence4a0f61d remains FAIL114/1; its UTF8 workaround is not
acceptance. These outcomes apply to different versions.

Actual read-only GitHub discovery using the new backend independently returned
FAIL for originalc7f7dee and VERIFIED_PASS131 for92e1248, with last_error null
(11.038seconds). It used disposable external state and existing read access;
no queue write, dispatch, receive, watch or runner ran. This does not qualify
real cross-computer execution of the new feature.

Default console_setup init creates a Viewer account, which cannot dispatch.
Dispatch execution requires an explicitly provisioned Administrator who creates
and confirms the plan in that same session; Operator can preview only.
Choose roles during explicit new local setup. Existing credentials are not
upgraded or migrated here. See the [external authentication and role guide]
(web-console-guide.md#external-authentication) for deliberate operator setup.

See the [handoff guide](github-handoff-guide.md) for external per-computer
configuration, explicit initialization, role-bound preview/confirmation and
finite foreground watch. Each computer needs its own locally activated watch
terminal; navigation and5second console refresh only read local cached summary.
A coordinator watch syncs; a worker syncs/receives its own assignment. Execution
requires both locally approved bound runner/execution_enabled and --execute.
No service, schedule or autostart is installed. Existing READY assigned cards
can be handed off; task-authoring UI remains absent. Runtime FINISHED/FAILED/
UNKNOWN never means formal reviewed/DONE. No real provider or peer activation,
new credentials or automatic review/merge is authorized by this release.

Current focused source evidence: backend9pass/7deselected/native0; separate
UI19pass/13deselected/native0. Independent delta6pass/1fixture-fail/native1 is
retained honestly; separate actual-backend HTTP probe native0/6.970seconds
verifies scope preview/confirmation. The minimal reviewer controller fixture
failed before original HTTP scope assertions; the earlier execution claim was
corrected. No7green or combined full-suite claim. Older backend60+1, UI30/92,
repair131/16 and original failure runs remain distinct historical executions.

Portable manifest contains35source/test/doc/static pins and30accepted snapshots
(10DONE cards,10canonical decisions,10deliveries),65files and111board cards.
All prior18snapshots remain byte-exact. New snapshots cover remote reacceptance,
backend, UI and independent review. Their archive evidence links are historical
and unbundled unless pinned; no private logs, tokens, DBs or transcripts ship.
Manifest hashes provide integrity, not independent authenticity. Whole-repository
and broader symlink/junction qualification remain outside scope.

Earlier sections below are dated history: old HOLD/publication-pending wording
does not describe current92acceptance or this local feature status.

## Locale repair and required acceptance rerun (2026-10-25)

Select the repaired release commit supplied in the handoff; its accepted code/test
base is8a5bc1693e8f8e8ea0f476424b59d37346f44b8a. Original publishedc7f7dee
failed initialization under CP950/non-ASCII whoami output (114passed/1failed in
evidence4a0f61d). PYTHONUTF8 is not required by the repair and is not an acceptance
workaround. The repair reads raw command bytes and decodes only a validated ASCII
SID; account-name bytes are never decoded, and existing ACL checks are unchanged.

After the repaired release is authorized and published, repeat exact-commit
download, init, identical replay, login, stop and restart in the original failing
environment with its ordinary configuration and the chosen isolated interpreter;
do not add PYTHONUTF8 to make it pass. Preserve the failed attempt as history.
Local Python3.13 repair tests do not substitute for this acceptance rerun or prove
a distinct physical host. P1 acceptance remains HOLD; P2/P3 planning waits for the
rerun. See [current release status](console-release-status.md) for exact evidence
and publication gates. Initialize only new explicitly chosen private state as
explained below; do not reset or alter an existing setup to force acceptance.

# Download, initialize and run the local console

This guide describes a Windows Python3.12+ source candidate. Publication and a
second computer's acceptance are separate steps. Do not substitute an older
GitHub main or archive branch for the reviewed console version.

## Select the reviewed version

Install Git and Python3.12+ first. Once a repository URL and reviewed commit are
published, clone that repository, then select the exact supplied commit:

```powershell
git clone <REPOSITORY_URL> console
Set-Location console
git checkout --detach <REVIEWED_COMMIT>
git rev-parse HEAD
py -3.12 --version
```

Angle-bracket values are placeholders. Use the commit printed in the release
handoff. These commands do not install dependencies, create accounts, push or
enable workers. The runtime uses Python's standard library.

The examples select Python3.12 with `py -3.12`. If your computer already has
Python3.13 or later, use its selector (for example `py -3.13`) or that interpreter's
full executable path throughout; you do not need an additional Python3.12
installation. Confirm the selected interpreter is3.12+ with `--version`.

## Initialize explicitly on this computer

Select three separate absolute canonical paths: the downloaded repository,
workspace storage, and a new private state directory. None may contain another.
The private state's parent directory must already exist. Workspace storage need
not exist yet. Avoid junctions, symlinks, `..`, app virtualization aliases and
another computer's paths. Resolve your own paths locally; do not copy another
host's auth, tokens, database, leases or ACK files.

For example, after replacing the paths with your actual local locations:

```powershell
py -3.12 scripts/console_setup.py init --repo "C:\Work\console" --workspaces "C:\Workspaces\console" --project-id local-console --state-dir "C:\Private\console-state"
```

Default account: `viewer`, role Viewer. An explicitly different username or role
may be selected with `--username` and `--role viewer|operator|administrator`;
those selections become part of the immutable local configuration. Administrator
permits the existing controlled operations. It does not add task dispatch.

Initialization uses schema4 and inserts a disabled project binding directly;
it never temporarily enables parallel mode. A new private staging directory is
restricted to the current Windows user's SID with a protected DACL before any
secret is written. It is published to the chosen final state directory only
after the database, config, authentication digest and private login file exist.
Permission failure refuses setup. Do not broaden that directory's permissions.

The command prints the private `login.txt` location, never its token. Open that
file locally when signing in. Keep its contents out of screenshots, issue
reports, command arguments, URLs and shared Git files. Authentication configuration
contains only the token digest; the private login file contains the original.

Repeating the identical command verifies the complete existing setup read-only
and preserves token and database bytes. A changed project, root, username, role,
schema, binding, login file or mode is refused without reset or migration.
Existing foreign/incomplete state is preserved. Interrupted initialization may
leave a private `NAME.pending-*` sibling. Do not copy individual files into the
final location or rerun with different values to force adoption. Preserve it
for local diagnosis, choose a fresh state directory, and initialize explicitly.
This small entry point does not repair or migrate existing databases.

## Start, stop and restart

```powershell
py -3.12 scripts/console_setup.py serve --state-dir "C:\Private\console-state" --port 8766 --duration 300
```

Serve requires a complete matching initialized setup; it cannot create or migrate
the DB or accounts. The terminal reports `http://127.0.0.1:PORT`, process PID,
finite duration and stop instructions. Open exactly that origin on this computer,
then sign in using the private login file. Seven views show local board/runtime
data. Viewer is read-only; no task or worker starts through initialization.

Keep the foreground terminal open. Stop with **Ctrl+C** in that terminal or wait
for expiry (default300seconds, allowed10..1800). Restart with the same serve
command; existing local credentials and DB persist. If the port is occupied,
choose another port or explicitly stop its owner. This tool never kills the
other process, starts a daemon or installs an autostart task.

The console is loopback-only. Another computer initializes its own local copy
and views that checkout's task files. Updating the checkout via GitHub and
refreshing the page are different operations; refresh is not cross-machine
synchronization. Creation/assignment UI, remote execution, publication and
second-host verification remain separate work.
