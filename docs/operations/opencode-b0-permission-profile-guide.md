# OpenCode B0 Permission Profile

## Purpose

`opencode-b0-permission-profile.json` is a versioned, task-scoped OpenCode v1
permission profile for `phase14.5-bootstrap-01`. It resolves the headless
permission-prompt blocker without using `--auto` or a blanket allow rule.

## Allowed Capability

- read, list, glob, and grep inside the B0 worktree;
- edits only in B0's declared `allowed_scope`;
- `git status`, `git diff`, the two task-card lifecycle `git mv` operations,
  Python compilation, and coordination validation.

## Explicitly Denied Capability

- external directories, web tools, subagents, LSP, skills, and interactive
  questions;
- any shell command not named in the profile, including package installation;
- Git commit and push, because the shell default is deny;
- any edit outside B0's declared scope.

## Operator Launch Boundary

The profile is not a runtime grant. After this task has independent review,
the operator may use an isolated config root and explicitly point OpenCode at
this versioned profile for one B0 session. Do not use `--auto`; explicit deny
rules remain the boundary, and a new task needs a new reviewed profile.
