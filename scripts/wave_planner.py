#!/usr/bin/env python3
"""Read-only dependency wave planner for `orchestrate waves`.

Scans task cards across all task-board states, builds a dependency graph,
and proposes deterministic execution waves.  Never mutates task cards,
assignments, profiles, branches, or worktrees.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coordination_common import (  # noqa: E402
    ROOT,
    TASK_BOARD_DIR,
    find_task,
    list_tasks,
    load_task,
)

# Terminal accepted state: a dependency is satisfied only when the
# dependent task lives under task-board/done/.
ACCEPTED_STATES = frozenset({"done"})


def _scan_all_tasks() -> dict[str, dict]:
    """Return {task_id: front_matter} for every task card in the board."""
    tasks: dict[str, dict] = {}
    for state_dir in sorted(TASK_BOARD_DIR.iterdir()):
        if not state_dir.is_dir():
            continue
        for path in sorted(state_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                fm, _ = load_task(path)
            except (ValueError, KeyError):
                continue
            tid = str(fm.get("task_id", "")).strip()
            if tid:
                fm["_file"] = str(path)
                fm["_state_dir"] = state_dir.name
                tasks[tid] = fm
    return tasks


def _dep_satisfied(dep_id: str, tasks: dict[str, dict]) -> bool:
    """A dependency is satisfied when the task exists in done/."""
    dep = tasks.get(dep_id)
    if dep is None:
        return False
    return dep.get("_state_dir") in ACCEPTED_STATES


def _classify_tasks(
    tasks: dict[str, dict],
) -> tuple[list[str], list[str], list[str], list[dict]]:
    """Classify ready tasks into wave-0 candidates, later-wave candidates,
    blocked tasks, and graph errors.

    Returns (wave0_ids, later_ids, blocked_ids, errors).

    - wave0: all deps satisfied (in done/)
    - later: deps exist, some on other ready tasks, none missing
    - blocked: missing deps OR deps on unfinished (in_progress/review/blocked) tasks
    """
    wave0: list[str] = []
    later: list[str] = []
    blocked: list[str] = []
    errors: list[dict] = []

    for tid, fm in sorted(tasks.items()):
        state = fm.get("_state_dir", "")
        if state != "ready":
            continue

        deps = fm.get("dependencies", [])
        if not isinstance(deps, list):
            deps = []

        missing = [d for d in deps if d not in tasks]
        if missing:
            for m in missing:
                errors.append({
                    "type": "missing_dependency",
                    "task": tid,
                    "dependency": m,
                    "message": f"Task `{tid}` depends on `{m}` which does not exist in the task board.",
                })
            blocked.append(tid)
            continue

        # All deps exist — classify by satisfaction
        if all(_dep_satisfied(d, tasks) for d in deps):
            wave0.append(tid)
            continue

        # Some deps unsatisfied — check if they're on other ready tasks
        # (plannable later) or on unfinished tasks (truly blocked)
        unsatisfied_ready = []
        unsatisfied_other = []
        for d in deps:
            if _dep_satisfied(d, tasks):
                continue
            dep_state = tasks[d].get("_state_dir", "")
            if dep_state == "ready":
                unsatisfied_ready.append(d)
            else:
                unsatisfied_other.append(d)

        if unsatisfied_other:
            # Blocked by unfinished tasks
            dep_str = ", ".join(f"{d} ({tasks[d].get('_state_dir', '?')})" for d in unsatisfied_other)
            blocked.append(tid)
        else:
            # Deps are on other ready tasks — plannable in later wave
            later.append(tid)

    return wave0, later, blocked, errors


def _detect_cycles(tasks: dict[str, dict]) -> tuple[list[dict], set[str]]:
    """Detect cycles in the dependency graph among READY tasks.

    Returns (errors, cycle_task_ids) — the set of all task IDs involved in cycles.
    """
    errors: list[dict] = []
    cycle_tasks: set[str] = set()
    ready_ids = {tid for tid, fm in tasks.items() if fm.get("_state_dir") == "ready"}

    # Build adjacency only among ready tasks
    graph: dict[str, list[str]] = {}
    for tid in ready_ids:
        deps = tasks[tid].get("dependencies", [])
        if isinstance(deps, list):
            graph[tid] = [d for d in deps if d in ready_ids]
        else:
            graph[tid] = []

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {tid: WHITE for tid in ready_ids}
    path_stack: list[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        path_stack.append(node)
        for neighbor in graph.get(node, []):
            if color[neighbor] == GRAY:
                # Found a cycle
                cycle_start = path_stack.index(neighbor)
                cycle = path_stack[cycle_start:] + [neighbor]
                cycle_str = " -> ".join(f"`{c}`" for c in cycle)
                errors.append({
                    "type": "cycle",
                    "task": neighbor,
                    "cycle": cycle,
                    "message": f"Dependency cycle detected: {cycle_str}",
                })
                # Mark all cycle participants
                for c in cycle:
                    cycle_tasks.add(c)
            elif color[neighbor] == WHITE:
                dfs(neighbor)
        path_stack.pop()
        color[node] = BLACK

    for tid in sorted(ready_ids):
        if color[tid] == WHITE:
            dfs(tid)

    return errors, cycle_tasks


def _topological_waves(
    tasks: dict[str, dict],
    wave0_ids: list[str],
    later_ids: list[str],
) -> list[list[str]]:
    """Assign tasks to waves by topological depth.

    Wave 0 = tasks with all deps satisfied (done/).
    Wave 1+ = tasks whose ready-deps are in earlier waves.

    The same repo state always produces the same waves (sorted within each
    wave for deterministic output).
    """
    wave0_set = set(wave0_ids)
    later_set = set(later_ids)
    all_candidates = wave0_set | later_set

    # For later tasks, compute depth based on deps on other candidates
    depth: dict[str, int] = {}
    computed: dict[str, bool] = {}

    def compute_depth(tid: str) -> int:
        if tid in computed:
            return depth[tid]
        computed[tid] = True
        deps = tasks[tid].get("dependencies", [])
        if not isinstance(deps, list):
            deps = []
        ready_deps = [d for d in deps if d in all_candidates and d != tid]
        if not ready_deps:
            depth[tid] = 0
        else:
            depth[tid] = max(compute_depth(d) for d in ready_deps) + 1
        return depth[tid]

    for tid in later_ids:
        compute_depth(tid)

    # Wave 0 is always the wave0_ids
    waves: list[list[str]] = []
    if wave0_ids:
        waves.append(sorted(wave0_ids))

    # Later tasks by depth (depth 0 = depends only on wave0 tasks)
    if later_ids:
        max_depth = max(depth.values()) if depth else 0
        for d in range(max_depth + 1):
            wave = sorted(tid for tid in later_ids if depth.get(tid, 0) == d)
            if wave:
                waves.append(wave)

    return waves


def plan_waves(
    tasks: dict[str, dict] | None = None,
) -> dict:
    """Produce a complete wave plan. Returns a dict with:
    - waves: list of lists of task IDs
    - ready: list of task IDs eligible for immediate dispatch (wave 0)
    - blocked: list of task IDs waiting on dependencies
    - errors: list of graph problems
    - stats: summary counts
    """
    if tasks is None:
        tasks = _scan_all_tasks()

    # Detect cycles first
    errors, cycle_tasks = _detect_cycles(tasks)

    wave0_ids, later_ids, blocked_ids, classify_errors = _classify_tasks(tasks)
    errors.extend(classify_errors)

    # Remove cycle tasks from wave candidates
    clean_wave0 = [tid for tid in wave0_ids if tid not in cycle_tasks]
    clean_later = [tid for tid in later_ids if tid not in cycle_tasks]
    if cycle_tasks:
        blocked_ids.extend(sorted(cycle_tasks))
        blocked_ids = sorted(set(blocked_ids))

    waves = _topological_waves(tasks, clean_wave0, clean_later)

    return {
        "waves": waves,
        "ready": clean_wave0,
        "blocked": blocked_ids,
        "errors": errors,
        "stats": {
            "total": len(tasks),
            "ready": len(clean_wave0),
            "blocked": len(blocked_ids),
            "error_count": len(errors),
        },
    }


def _format_human(plan: dict) -> str:
    """Format plan as human-readable output."""
    lines: list[str] = []

    border = "=" * 60
    lines.append(border)
    lines.append("  Dependency Wave Planner")
    lines.append(border)
    lines.append("")

    stats = plan["stats"]
    lines.append(f"  Total tasks scanned: {stats['total']}")
    lines.append(f"  Ready for dispatch:  {stats['ready']}")
    lines.append(f"  Blocked by deps:     {stats['blocked']}")
    lines.append(f"  Graph errors:        {stats['error_count']}")
    lines.append("")

    # Waves
    if plan["waves"]:
        lines.append("  Execution Waves")
        lines.append("  " + "-" * 56)
        for i, wave in enumerate(plan["waves"]):
            lines.append(f"  Wave {i}: {', '.join(wave)}")
        lines.append("")

    # Blocked tasks
    if plan["blocked"]:
        lines.append("  Blocked Tasks")
        lines.append("  " + "-" * 56)
        tasks = _scan_all_tasks()
        for tid in plan["blocked"]:
            fm = tasks.get(tid, {})
            deps = fm.get("dependencies", [])
            state = fm.get("_state_dir", "?")
            # Find which deps are unsatisfied
            unsatisfied = []
            if isinstance(deps, list):
                for d in deps:
                    dep_fm = tasks.get(d)
                    if dep_fm is None:
                        unsatisfied.append(f"{d} (missing)")
                    elif dep_fm.get("_state_dir") not in ACCEPTED_STATES:
                        unsatisfied.append(f"{d} ({dep_fm.get('_state_dir', '?')})")
            dep_str = ", ".join(unsatisfied) if unsatisfied else "unknown"
            lines.append(f"  {tid} [state={state}] — waiting on: {dep_str}")
        lines.append("")

    # Errors
    if plan["errors"]:
        lines.append("  Graph Errors")
        lines.append("  " + "-" * 56)
        for err in plan["errors"]:
            lines.append(f"  [{err['type'].upper()}] {err['message']}")
        lines.append("")

    lines.append(border)
    overall = "COMPLETE" if not plan["errors"] else "INCOMPLETE"
    lines.append(f"  Plan status: {overall}")
    lines.append(border)

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Propose dependency-aware execution waves without lifecycle mutation.",
        epilog="Exit status: 0 if all graph errors resolved, 1 if any remain.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output plan as JSON (one object per line).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    plan = plan_waves()

    if args.json:
        import json
        output = {
            "waves": plan["waves"],
            "ready": plan["ready"],
            "blocked": plan["blocked"],
            "errors": plan["errors"],
            "stats": plan["stats"],
        }
        print(json.dumps(output, indent=2))
    else:
        print(_format_human(plan))

    return 0 if not plan["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
