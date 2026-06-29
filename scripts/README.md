# Scripts

## `validate_coordination_files.py`

Validates the repo-backed coordination markdown files.

Checks:

- task packet front matter keys
- required markdown sections
- progress report labels
- incident report labels
- review report labels
- task card status versus task-board folder state

Usage:

```bash
python scripts/validate_coordination_files.py
```

Templates only:

```bash
python scripts/validate_coordination_files.py --templates-only
```

Recommended use:

- run before opening a phase to external agents
- run before review on a batch of newly added task cards
- later wire into CI or pre-commit hooks

