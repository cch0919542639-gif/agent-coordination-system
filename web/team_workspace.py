"""Create preserved, distinct Git working directories for team workers."""
import os
from pathlib import Path
import secrets
import tempfile

from coordination_runtime.state_controller import StateError
from coordination_runtime.workspace import git


def base_revision(manager):
    base = git(manager.repository, 'rev-parse', 'HEAD').decode('ascii').strip()
    manager.pinned(base)
    return base


def provision(manager, base, run_id):
    """Create a new detached worktree; never adopt or delete existing work."""
    manager.pinned(base)
    path = manager.path(run_id)
    if path.exists():
        raise StateError('Workspace already exists.')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.resolve() != path.parent or not path.parent.is_relative_to(manager.root):
        raise StateError('Workspace storage is aliased or outside its root.')
    hooks = Path(tempfile.mkdtemp(prefix='team-hooks-', dir=manager.root))
    try:
        git(manager.repository, '-c', 'core.hooksPath=' + str(hooks), 'worktree', 'add', '--detach', path, base)
    finally:
        hooks.rmdir()
    actual = Path(os.fsdecode(git(path, 'rev-parse', '--show-toplevel').strip())).resolve()
    if actual != path or git(path, 'rev-parse', 'HEAD').decode('ascii').strip() != base:
        raise StateError('Workspace identity mismatch; retained for inspection.')
    return path


def run_id(index):
    return 'team-' + secrets.token_hex(12) + '-' + str(index)


def changes(manager, path, base):
    path = Path(path)
    if (path.resolve() != path or not path.is_relative_to(manager.root)
            or Path(os.fsdecode(git(path, 'rev-parse', '--show-toplevel').strip())).resolve() != path):
        raise StateError('Workspace path changed.')
    expected_common = Path(os.fsdecode(git(manager.repository, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())).resolve()
    actual_common = Path(os.fsdecode(git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())).resolve()
    if (actual_common != expected_common or git(path, 'rev-parse', 'HEAD').decode('ascii').strip() != base
            or git(path, 'rev-parse', '--abbrev-ref', 'HEAD').strip() != b'HEAD'):
        raise StateError('Workspace Git identity or revision changed.')
    tracked = git(path, 'diff', '--name-only', '--no-renames', '-z', base, '--')
    untracked = git(path, 'ls-files', '--others', '--exclude-standard', '-z')
    names = sorted(set(os.fsdecode(x) for x in (tracked + untracked).split(b'\0') if x))
    if len(names) > 2048: raise StateError('Workspace change list exceeds limit.')
    return names
