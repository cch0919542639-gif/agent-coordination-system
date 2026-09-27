from pathlib import Path
from subprocess import CompletedProcess

from phaseh_worktree_preflight import verify_worktrees


COMMIT = "a" * 40


def bindings():
    return [{"worktree_ref": f"worker-{number}"} for number in range(1, 7)]


def runner(calls, *, dirty=False, attached=False, wrong_pin=False, git_failure=False, ownership_guard=False):
    def run(args):
        calls.append(args)
        command = args[-2:]
        scoped = len(args) > 4 and args[2] == f"safe.directory={Path(args[4]).resolve()}"
        if git_failure or (ownership_guard and not scoped):
            return CompletedProcess(args, 128, "", "ownership guard")
        if command == ["status", "--porcelain"]:
            return CompletedProcess(args, 0, "M file\n" if dirty else "", "")
        if command == ["symbolic-ref", "-q"] or args[-3:] == ["symbolic-ref", "-q", "HEAD"]:
            return CompletedProcess(args, 0 if attached else 1, "", "")
        return CompletedProcess(args, 0, ("b" * 40 if wrong_pin else COMMIT) + "\n", "")
    return run


def test_scoped_git_reads_accept_six_current_bindings(tmp_path):
    for binding in bindings():
        (tmp_path / binding["worktree_ref"]).mkdir()
    calls = []
    result = verify_worktrees(bindings(), tmp_path, COMMIT, run=runner(calls))
    assert result["decision"] == "worktrees_current" and result["current_bindings"] == 6
    assert all(command[:3] == ["git", "-c", f"safe.directory={Path(command[4]).resolve()}"] for command in calls)


def test_unsafe_or_failed_binding_denies_without_aggregate_success(tmp_path):
    for binding in bindings():
        (tmp_path / binding["worktree_ref"]).mkdir()
    bad = bindings(); bad[0] = {"worktree_ref": "../outside"}
    assert verify_worktrees(bad, tmp_path, COMMIT)["decision"] == "deny_worktree_state"
    assert verify_worktrees(bindings(), tmp_path, COMMIT, run=runner([], dirty=True))["current_bindings"] == 0
    assert verify_worktrees(bindings(), tmp_path, COMMIT, run=runner([], wrong_pin=True))["decision"] == "deny_worktree_state"


def test_ownership_guard_scope_and_every_failure_deny_before_aggregate_success(tmp_path):
    for binding in bindings():
        (tmp_path / binding["worktree_ref"]).mkdir()
    calls = []
    assert verify_worktrees(bindings(), tmp_path, COMMIT, run=runner(calls, ownership_guard=True))["decision"] == "worktrees_current"
    assert calls[0][2].startswith("safe.directory=")
    assert verify_worktrees(bindings(), tmp_path, COMMIT, run=runner([], git_failure=True))["decision"] == "deny_worktree_state"
    assert verify_worktrees(bindings(), tmp_path, COMMIT, run=runner([], attached=True))["current_bindings"] == 0
    missing = bindings(); (tmp_path / missing[0]["worktree_ref"]).rmdir()
    calls = []
    assert verify_worktrees(missing, tmp_path, COMMIT, run=runner(calls))["decision"] == "deny_worktree_state" and calls == []
