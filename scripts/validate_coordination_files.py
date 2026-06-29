#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COORDINATION_DIR = ROOT / "coordination"
TEMPLATES_DIR = COORDINATION_DIR / "templates"
TASK_BOARD_DIR = COORDINATION_DIR / "task-board"

TASK_BOARD_STATES = {"ready", "in_progress", "review", "done", "blocked"}
TASK_REQUIRED_KEYS = {
    "task_id",
    "phase",
    "status",
    "owner",
    "reviewer",
    "priority",
    "dependencies",
    "allowed_scope",
    "forbidden_scope",
    "acceptance",
    "expected_artifacts",
}
TASK_REQUIRED_SECTIONS = {
    "## Objective",
    "## Context",
    "## Constraints",
    "## Implementation Notes",
    "## Validation Steps",
    "## Escalation Rules",
}
PROGRESS_REQUIRED_LABELS = {
    "- Agent:",
    "- Active Task:",
    "- Phase:",
    "- Status:",
    "- Last Updated:",
    "## Current Step",
    "## Changes So Far",
    "## Blocker Status",
    "## Next Step",
}
INCIDENT_REQUIRED_LABELS = {
    "- Incident ID:",
    "- Agent:",
    "- Task ID:",
    "- Phase:",
    "- Severity:",
    "- Category:",
    "- Status:",
    "- Created At:",
    "## Summary",
    "## What Was Attempted",
    "## Exact Blocker",
    "## Scope / Risk Impact",
    "## Recommended Next Action",
}
REVIEW_REQUIRED_LABELS = {
    "- Review ID:",
    "- Reviewer:",
    "- Task ID:",
    "- Phase:",
    "- Decision:",
    "- Reviewed At:",
    "## Summary",
    "## Findings",
    "## Scope Compliance",
    "## Validation Check",
    "## Required Changes",
    "## Accepted Artifacts",
}


class ValidationError:
    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path.relative_to(ROOT)}: {self.message}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_front_matter(text: str) -> dict[str, object] | None:
    if not text.startswith("---\n"):
        return None

    end = text.find("\n---\n", 4)
    if end == -1:
        return None

    block = text[4:end]
    result: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("  - "):
            if current_key is None:
                return None
            result.setdefault(current_key, [])
            value = result[current_key]
            if not isinstance(value, list):
                return None
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
        return None

    return result


def has_all_labels(text: str, labels: set[str]) -> list[str]:
    return [label for label in sorted(labels) if label not in text]


def validate_task_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    text = read_text(path)
    front_matter = parse_front_matter(text)

    if front_matter is None:
        return [ValidationError(path, "missing or invalid front matter block")]

    missing_keys = sorted(TASK_REQUIRED_KEYS - set(front_matter))
    for key in missing_keys:
        errors.append(ValidationError(path, f"missing front matter key `{key}`"))

    status = str(front_matter.get("status", "")).lower()
    parent_state = path.parent.name.lower()
    if parent_state in TASK_BOARD_STATES and status:
        normalized_status = status.lower()
        normalized_parent = parent_state.lower()
        if normalized_status != normalized_parent.upper().lower():
            errors.append(
                ValidationError(
                    path,
                    f"front matter status `{front_matter.get('status')}` does not match folder `{path.parent.name}`",
                )
            )

    for list_key in ("dependencies", "allowed_scope", "forbidden_scope", "acceptance", "expected_artifacts"):
        if list_key in front_matter and not isinstance(front_matter[list_key], list):
            errors.append(ValidationError(path, f"`{list_key}` must be a list"))

    for section in sorted(TASK_REQUIRED_SECTIONS):
        if section not in text:
            errors.append(ValidationError(path, f"missing section `{section}`"))

    return errors


def validate_progress_file(path: Path) -> list[ValidationError]:
    text = read_text(path)
    return [ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, PROGRESS_REQUIRED_LABELS)]


def validate_incident_file(path: Path) -> list[ValidationError]:
    text = read_text(path)
    return [ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, INCIDENT_REQUIRED_LABELS)]


def validate_review_file(path: Path) -> list[ValidationError]:
    text = read_text(path)
    return [ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, REVIEW_REQUIRED_LABELS)]


def iter_markdown_files(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*.md") if p.is_file())


def validate_templates() -> list[ValidationError]:
    errors: list[ValidationError] = []
    template_map = {
        TEMPLATES_DIR / "task-packet.md": validate_task_file,
        TEMPLATES_DIR / "progress-report.md": validate_progress_file,
        TEMPLATES_DIR / "incident-report.md": validate_incident_file,
        TEMPLATES_DIR / "review-report.md": validate_review_file,
    }

    for path, validator in template_map.items():
        if not path.exists():
            errors.append(ValidationError(path, "template file is missing"))
            continue
        errors.extend(validator(path))

    return errors


def validate_repo_files() -> list[ValidationError]:
    errors: list[ValidationError] = []

    for path in iter_markdown_files(TASK_BOARD_DIR):
        if path.name == "README.md":
            continue
        errors.extend(validate_task_file(path))

    progress_dir = COORDINATION_DIR / "progress"
    for path in iter_markdown_files(progress_dir):
        errors.extend(validate_progress_file(path))

    incidents_dir = COORDINATION_DIR / "incidents"
    for path in iter_markdown_files(incidents_dir):
        errors.extend(validate_incident_file(path))

    reviews_dir = COORDINATION_DIR / "reviews"
    for path in iter_markdown_files(reviews_dir):
        errors.extend(validate_review_file(path))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate repo-backed coordination markdown files.")
    parser.add_argument(
        "--templates-only",
        action="store_true",
        help="Validate only the coordination templates.",
    )
    args = parser.parse_args()

    errors = validate_templates()
    if not args.templates_only:
        errors.extend(validate_repo_files())

    if errors:
        print("Coordination validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Coordination validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

