#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COORDINATION_DIR = ROOT / "coordination"
TASK_BOARD_DIR = COORDINATION_DIR / "task-board"
PROGRESS_DIR = COORDINATION_DIR / "progress"
DELIVERY_DIR = COORDINATION_DIR / "delivery"

ACTIVE_STATES = ("ready", "in_progress", "review", "blocked")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def parse_front_matter(text: str) -> tuple[dict[str, object] | None, str]:
    if not text.startswith("---\n"):
        return None, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text

    block = text[4:end]
    body = text[end + 5 :]
    result: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("  - "):
            if current_key is None:
                return None, body
            result.setdefault(current_key, [])
            value = result[current_key]
            if not isinstance(value, list):
                return None, body
            value.append(line[4:].strip())
            continue
        if re.match(r"^[A-Za-z0-9_]+:\s*\[\s*\]\s*$", line):
            key = line.split(":", 1)[0].strip()
            result[key] = []
            current_key = key
            continue
        if line.endswith(":"):
            key = line[:-1].strip()
            result[key] = []
            current_key = key
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            result[current_key] = value.strip()
            continue
        return None, body

    return result, body


def dump_front_matter(data: dict[str, object], body: str) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body.lstrip("\n")


def load_task(path: Path) -> tuple[dict[str, object], str]:
    front_matter, body = parse_front_matter(read_text(path))
    if front_matter is None:
        raise ValueError(f"{path} is missing valid front matter")
    return front_matter, body


def save_task(path: Path, front_matter: dict[str, object], body: str) -> None:
    write_text(path, dump_front_matter(front_matter, body))


def find_task(task_id: str) -> tuple[Path, dict[str, object], str]:
    for state_dir in sorted(TASK_BOARD_DIR.iterdir()):
        if not state_dir.is_dir():
            continue
        for path in state_dir.glob("*.md"):
            if path.name == "README.md":
                continue
            front_matter, body = load_task(path)
            if str(front_matter.get("task_id", "")).strip() == task_id:
                return path, front_matter, body
    raise FileNotFoundError(f"task_id `{task_id}` not found in task board")


def list_tasks(states: tuple[str, ...] | None = None) -> list[tuple[Path, dict[str, object]]]:
    results: list[tuple[Path, dict[str, object]]] = []
    selected_states = states or ACTIVE_STATES
    for state in selected_states:
        state_dir = TASK_BOARD_DIR / state
        if not state_dir.exists():
            continue
        for path in sorted(state_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            front_matter, _ = load_task(path)
            results.append((path, front_matter))
    return results


def move_task(path: Path, destination_state: str, front_matter: dict[str, object], body: str) -> Path:
    destination_dir = TASK_BOARD_DIR / destination_state
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / path.name
    front_matter["status"] = destination_state.upper()
    save_task(destination_path, front_matter, body)
    if path.resolve() != destination_path.resolve() and path.exists():
        path.unlink()
    return destination_path


def utc_now_string() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def progress_file_for(agent_name: str) -> Path:
    return PROGRESS_DIR / f"{agent_name}.md"


def delivery_file_for(task_id: str) -> Path:
    return DELIVERY_DIR / f"{task_id}-delivery-report.md"


def sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    return slug or "incident"
