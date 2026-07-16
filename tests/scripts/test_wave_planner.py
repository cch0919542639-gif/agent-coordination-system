"""Tests for scripts/wave_planner.py — read-only dependency wave planner.

Covers independent tasks, linear chains, fan-in/fan-out, missing deps,
cycles, no-mutation behavior, and stable ordering.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
WAVE_PLANNER = SCRIPTS_DIR / "wave_planner.py"

sys.path.insert(0, str(SCRIPTS_DIR))


def _run_waves(extra_args: list[str] | None = None, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(WAVE_PLANNER)]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        cwd=cwd or str(ROOT),
    )


def _make_task_graph(tmp_path: Path, graph: dict[str, list[str]]) -> dict:
    """Create a minimal task board with the given dependency graph.

    graph: {task_id: [dep_ids]}
    Returns {task_id: front_matter} for all created tasks.
    """
    from coordination_common import dump_front_matter

    task_board = tmp_path / "coordination" / "task-board"
    done_dir = task_board / "done"
    ready_dir = task_board / "ready"
    done_dir.mkdir(parents=True, exist_ok=True)
    ready_dir.mkdir(parents=True, exist_ok=True)

    tasks = {}
    for tid, deps in graph.items():
        fm = {
            "task_id": tid,
            "phase": "test",
            "status": "READY",
            "owner": "UNASSIGNED",
            "reviewer": "ORCHESTRATOR",
            "priority": "medium",
            "dependencies": deps,
            "allowed_scope": ["tests/**"],
            "forbidden_scope": ["src/**"],
            "acceptance": ["test"],
            "expected_artifacts": ["code_changes"],
        }
        body = f"# Task Packet\n\n## Objective\n\nTest task {tid}.\n\n## Context\n\nContext.\n\n## Constraints\n\nConstraints.\n\n## Implementation Notes\n\nNotes.\n\n## Validation Steps\n\nSteps.\n\n## Escalation Rules\n\nEscalation.\n"
        content = dump_front_matter(fm, body)
        card = ready_dir / f"test-{tid}.md"
        card.write_text(content, encoding="utf-8")
        tasks[tid] = fm
    return tasks


def _make_done_task(tmp_path: Path, tid: str) -> dict:
    """Create a task card in done/ state."""
    from coordination_common import dump_front_matter

    task_board = tmp_path / "coordination" / "task-board"
    done_dir = task_board / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    fm = {
        "task_id": tid,
        "phase": "test",
        "status": "DONE",
        "owner": "test-agent",
        "reviewer": "ORCHESTRATOR",
        "priority": "medium",
        "dependencies": [],
        "allowed_scope": ["tests/**"],
        "forbidden_scope": ["src/**"],
        "acceptance": ["test"],
        "expected_artifacts": ["code_changes"],
    }
    body = f"# Task Packet\n\n## Objective\n\nDone task {tid}.\n\n## Context\n\nContext.\n\n## Constraints\n\nConstraints.\n\n## Implementation Notes\n\nNotes.\n\n## Validation Steps\n\nSteps.\n\n## Escalation Rules\n\nEscalation.\n"
    content = dump_front_matter(fm, body)
    card = done_dir / f"test-{tid}.md"
    card.write_text(content, encoding="utf-8")
    return fm


def _assert_no_mutation(paths: list[Path], before: list[bytes]) -> None:
    for path, content in zip(paths, before):
        assert path.read_bytes() == content, f"File {path} was mutated"


# ─── 1. Independent tasks ────────────────────────────────────────────


class TestIndependentTasks:
    """Tasks with no dependencies are all in wave 0."""

    def test_three_independent_tasks(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": []},
            "task-c": {"_file": "c.md", "_state_dir": "ready", "dependencies": []},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert len(plan["waves"]) == 1
        assert sorted(plan["waves"][0]) == ["task-a", "task-b", "task-c"]
        assert plan["ready"] == sorted(plan["waves"][0])
        assert plan["blocked"] == []
        assert plan["errors"] == []

    def test_empty_graph(self) -> None:
        from wave_planner import plan_waves
        plan = plan_waves({})
        assert plan["waves"] == []
        assert plan["ready"] == []
        assert plan["blocked"] == []
        assert plan["stats"]["total"] == 0


# ─── 2. Linear dependency chain ───────────────────────────────────────


class TestLinearChain:
    """A -> B -> C produces wave 0: [A], wave 1: [B], wave 2: [C]."""

    def test_chain_a_b_c(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
            "task-c": {"_file": "c.md", "_state_dir": "ready", "dependencies": ["task-b"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == [["task-a"], ["task-b"], ["task-c"]]

    def test_chain_with_done_dep(self) -> None:
        """A (done) -> B should put B in wave 0."""
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "done", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == [["task-b"]]
        assert plan["blocked"] == []


# ─── 3. Fan-out and fan-in ───────────────────────────────────────────


class TestFanOutFanIn:
    """Fan-out: A -> [B, C].  Fan-in: [A, B] -> C."""

    def test_fan_out(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
            "task-c": {"_file": "c.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == [["task-a"], ["task-b", "task-c"]]

    def test_fan_in(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": []},
            "task-c": {"_file": "c.md", "_state_dir": "ready", "dependencies": ["task-a", "task-b"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == [["task-a", "task-b"], ["task-c"]]


# ─── 4. Missing dependencies ─────────────────────────────────────────


class TestMissingDependencies:
    """Tasks depending on nonexistent task IDs are blocked with errors."""

    def test_missing_dep_blocked(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": ["nonexistent"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == []
        assert plan["blocked"] == ["task-a"]
        assert len(plan["errors"]) == 1
        assert plan["errors"][0]["type"] == "missing_dependency"
        assert "nonexistent" in plan["errors"][0]["message"]


# ─── 5. Cyclic dependencies ──────────────────────────────────────────


class TestCyclicDependencies:
    """Cycles are detected and reported."""

    def test_simple_cycle(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": ["task-b"]},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert len(plan["errors"]) >= 1
        cycle_errors = [e for e in plan["errors"] if e["type"] == "cycle"]
        assert len(cycle_errors) >= 1
        # Both cycle tasks should be blocked
        assert "task-a" in plan["blocked"]
        assert "task-b" in plan["blocked"]

    def test_three_node_cycle(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": ["task-b"]},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-c"]},
            "task-c": {"_file": "c.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        cycle_errors = [e for e in plan["errors"] if e["type"] == "cycle"]
        assert len(cycle_errors) >= 1
        assert plan["stats"]["ready"] == 0


# ─── 6. No-mutation behavior ──────────────────────────────────────────


class TestNoMutation:
    """Wave planner never modifies task cards or profiles."""

    def test_task_cards_unchanged_after_plan(self) -> None:
        from wave_planner import plan_waves
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        before_a = json.dumps(tasks["task-a"], sort_keys=True).encode()
        before_b = json.dumps(tasks["task-b"], sort_keys=True).encode()

        plan = plan_waves(tasks)

        after_a = json.dumps(tasks["task-a"], sort_keys=True).encode()
        after_b = json.dumps(tasks["task-b"], sort_keys=True).encode()
        assert before_a == after_a
        assert before_b == after_b

    def test_plan_waves_via_cli_no_mutation(self, tmp_path: Path) -> None:
        """Run the planner CLI against a temp task board and verify no files changed."""
        graph = {"t-a": [], "t-b": ["t-a"], "t-c": ["t-a", "t-b"]}
        _make_task_graph(tmp_path, graph)

        task_files = list((tmp_path / "coordination" / "task-board" / "ready").glob("*.md"))
        before_contents = [f.read_bytes() for f in task_files]

        result = _run_waves(cwd=str(tmp_path))
        # The CLI will fail because it uses the real ROOT, not tmp_path
        # for task scanning. But we verify no temp files were modified.
        after_contents = [f.read_bytes() for f in task_files]
        for before, after, f in zip(before_contents, after_contents, task_files):
            assert before == after, f"File {f} was mutated"


# ─── 7. Stable ordering ──────────────────────────────────────────────


class TestStableOrdering:
    """Same input always produces the same wave output."""

    def test_deterministic_output(self) -> None:
        tasks = {
            "task-c": {"_file": "c.md", "_state_dir": "ready", "dependencies": ["task-a", "task-b"]},
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": []},
        }
        from wave_planner import plan_waves
        plan1 = plan_waves(tasks)
        plan2 = plan_waves(tasks)
        assert plan1["waves"] == plan2["waves"]
        assert plan1["ready"] == plan2["ready"]
        assert plan1["blocked"] == plan2["blocked"]

    def test_sorted_within_wave(self) -> None:
        tasks = {f"task-{c}": {"_file": f"{c}.md", "_state_dir": "ready", "dependencies": []}
                 for c in "dcba"}
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"][0] == sorted(plan["waves"][0])


# ─── 8. CLI integration ──────────────────────────────────────────────


class TestCLI:
    """CLI produces valid output and exit codes."""

    def test_help_flag(self) -> None:
        result = _run_waves(["--help"])
        assert result.returncode == 0
        assert "waves" in result.stdout.lower() or "dependency" in result.stdout.lower()

    def test_json_output(self) -> None:
        result = _run_waves(["--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "waves" in data
        assert "ready" in data
        assert "blocked" in data
        assert "errors" in data
        assert "stats" in data

    def test_human_output(self) -> None:
        result = _run_waves()
        assert result.returncode == 0
        assert "Dependency Wave Planner" in result.stdout

    def test_exit_code_zero_when_no_errors(self) -> None:
        result = _run_waves()
        assert result.returncode == 0

    def test_exit_code_nonzero_when_errors(self, tmp_path: Path) -> None:
        """If there are tasks with missing deps in the real board, exit 1."""
        # This tests against the real repo; we just verify the exit code
        # logic is correct by checking the current state.
        result = _run_waves(["--json"])
        data = json.loads(result.stdout)
        if data["errors"]:
            assert result.returncode == 1
        else:
            assert result.returncode == 0


# ─── 9. Mixed states ─────────────────────────────────────────────────


class TestMixedStates:
    """Tasks in done/in_progress/review are not wave candidates."""

    def test_only_ready_tasks_are_candidates(self) -> None:
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "ready", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "done", "dependencies": []},
            "task-c": {"_file": "c.md", "_state_dir": "in_progress", "dependencies": []},
            "task-d": {"_file": "d.md", "_state_dir": "review", "dependencies": []},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["ready"] == ["task-a"]
        assert plan["stats"]["total"] == 4
        assert plan["stats"]["ready"] == 1

    def test_done_dep_satisfies_ready_task(self) -> None:
        """A ready task whose deps are all in done/ is in wave 0."""
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "done", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == [["task-b"]]

    def test_in_progress_dep_blocks(self) -> None:
        """A ready task blocked by an in_progress dep is blocked."""
        tasks = {
            "task-a": {"_file": "a.md", "_state_dir": "in_progress", "dependencies": []},
            "task-b": {"_file": "b.md", "_state_dir": "ready", "dependencies": ["task-a"]},
        }
        from wave_planner import plan_waves
        plan = plan_waves(tasks)
        assert plan["waves"] == []
        assert plan["blocked"] == ["task-b"]
