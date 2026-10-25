## Current integrated candidate (2026-10-25)

PR10's independently reviewed entry guards are integrated at c3c6a38. The original
CP950 acceptance of exact92e1248 is verified by evidence5002422; the SID technical
HOLD is closed. This candidate additionally refuses legacy loop/activation entry
when a Parallel Mode marker exists. Select the final exact commit supplied in PR6
or its merge receipt; the metadata commit is intentionally not self-referenced.
Use console-release-status.md and the release manifest for current pins and gates.
The following locale-repair section is preserved history, not a current HOLD.
No new other-computer run or production qualification is implied by integration.

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
