from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import task_delivery_evidence as evidence
from task_delivery_evidence import capture_snapshot, changed_paths


def test_snapshot_and_delta_are_scoped_and_classified(tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    (root / "scripts" / "nested").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "scripts" / "main.py").write_text("before\n", encoding="utf-8")
    (root / "scripts" / "nested" / "old.py").write_text("delete me\n", encoding="utf-8")
    (root / "docs" / "readme.md").write_text("unscoped\n", encoding="utf-8")

    before = capture_snapshot(str(root), ["scripts/**"])
    (root / "scripts" / "main.py").write_text("after\n", encoding="utf-8")
    (root / "scripts" / "nested" / "old.py").unlink()
    (root / "scripts" / "nested" / "new.py").write_text("new\n", encoding="utf-8")
    (root / "docs" / "readme.md").write_text("still outside scope\n", encoding="utf-8")
    after = capture_snapshot(str(root), ["scripts/**"])

    assert changed_paths(before, after) == {
        "added": ["scripts/nested/new.py"],
        "modified": ["scripts/main.py"],
        "deleted": ["scripts/nested/old.py"],
    }


def test_single_level_glob_does_not_capture_nested_files(tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    (root / "scripts" / "nested").mkdir(parents=True)
    (root / "scripts" / "main.py").write_text("one\n", encoding="utf-8")
    (root / "scripts" / "nested" / "nested.py").write_text("two\n", encoding="utf-8")

    snapshot = capture_snapshot(str(root), ["scripts/*.py"])

    assert list(snapshot) == ["scripts/main.py"]


@pytest.mark.parametrize("scope", ["../outside/**", "/absolute/path", "scripts\\*.py", "scripts//file.py", ""])
def test_invalid_scope_fails_closed(tmp_path: Path, scope: str) -> None:
    with pytest.raises(ValueError):
        capture_snapshot(str(tmp_path), [scope])


def test_file_and_byte_limits_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    root.mkdir()
    (root / "a.py").write_text("1234", encoding="utf-8")
    (root / "b.py").write_text("5678", encoding="utf-8")

    monkeypatch.setattr(evidence, "MAX_FILES", 1)
    with pytest.raises(ValueError, match="file limit"):
        capture_snapshot(str(root), ["*.py"])

    monkeypatch.setattr(evidence, "MAX_FILES", 10)
    monkeypatch.setattr(evidence, "MAX_TOTAL_BYTES", 4)
    with pytest.raises(ValueError, match="byte limit"):
        capture_snapshot(str(root), ["*.py"])


def test_symlink_inside_allowed_scope_is_never_followed(tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("private\n", encoding="utf-8")
    link = scripts / "linked.py"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable in this account: {exc}")

    with pytest.raises(ValueError, match="symlink"):
        capture_snapshot(str(root), ["scripts/**"])


def test_changed_paths_reject_malformed_hashes() -> None:
    with pytest.raises(ValueError, match="snapshot"):
        changed_paths({"../outside.py": "0" * 64}, {})
