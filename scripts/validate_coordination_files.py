#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from profile_resolver import load_profile, ProfileError


ROOT = Path(__file__).resolve().parents[1]
COORDINATION_DIR = ROOT / "coordination"
TEMPLATES_DIR = COORDINATION_DIR / "templates"
TASK_BOARD_DIR = COORDINATION_DIR / "task-board"
PROFILES_DIR = ROOT / "profiles"

TASK_BOARD_STATES = {"ready", "in_progress", "review", "done", "blocked"}
VALID_TASK_STATUSES = {
    "READY",
    "IN_PROGRESS",
    "REVIEW",
    "DONE",
    "BLOCKED",
    "NEEDS_FIX",
    "REASSIGNED",
    "CANCELLED",
}
VALID_REVIEW_DECISIONS = {"accepted", "needs_fix", "reassign", "rejected"}
VALID_EXECUTION_MODES = {"REPO_FIRST", "WORKTREE"}
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
TASK_OPTIONAL_KEYS = {
    "execution_mode",
    "branch",
    "worktree_path",
    "machine_id",
    "profile",
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
DELIVERY_DIR = COORDINATION_DIR / "delivery"
DELIVERY_REQUIRED_LABELS = {
    "- Task ID:",
    "- Agent:",
    "- Phase:",
    "- Status:",
    "## Changed Files",
    "## Validation Steps Performed",
    "## Known Residual Risks",
    "## Acceptance Criteria Coverage",
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

    unknown_keys = sorted(set(front_matter) - TASK_REQUIRED_KEYS - TASK_OPTIONAL_KEYS)
    for key in unknown_keys:
        if key.startswith("_"):
            continue
        # Extra front matter keys are allowed; no error needed.
        break

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

    status_value = str(front_matter.get("status", "")).strip()
    if status_value and status_value not in VALID_TASK_STATUSES:
        errors.append(
            ValidationError(
                path,
                f"invalid front matter status `{status_value}`; must be one of {sorted(VALID_TASK_STATUSES)}",
            )
        )

    for list_key in ("dependencies", "allowed_scope", "forbidden_scope", "acceptance", "expected_artifacts"):
        if list_key in front_matter and not isinstance(front_matter[list_key], list):
            errors.append(ValidationError(path, f"`{list_key}` must be a list"))

    for scalar_key in ("execution_mode", "branch", "worktree_path", "machine_id"):
        if scalar_key in front_matter and isinstance(front_matter[scalar_key], list):
            errors.append(ValidationError(path, f"`{scalar_key}` must be a scalar value, not a list"))

    execution_mode = str(front_matter.get("execution_mode", "")).strip()
    if execution_mode:
        if execution_mode not in VALID_EXECUTION_MODES:
            errors.append(
                ValidationError(
                    path,
                    f"invalid execution_mode `{execution_mode}`; must be one of {sorted(VALID_EXECUTION_MODES)}",
                )
            )
        if execution_mode == "WORKTREE":
            for required_key in ("branch", "worktree_path"):
                value = str(front_matter.get(required_key, "")).strip()
                if not value:
                    errors.append(
                        ValidationError(
                            path,
                            f"`{required_key}` is required when execution_mode is `WORKTREE`",
                        )
                    )

    has_worktree_provenance = any(str(front_matter.get(key, "")).strip() for key in ("branch", "worktree_path", "machine_id"))
    if has_worktree_provenance and not execution_mode:
        errors.append(
            ValidationError(
                path,
                "worktree provenance fields are present but `execution_mode` is missing",
            )
        )

    for section in sorted(TASK_REQUIRED_SECTIONS):
        if section not in text:
            errors.append(ValidationError(path, f"missing section `{section}`"))

    # --- Profile-aware additive enforcement ---
    profile_ref = str(front_matter.get("profile", "")).strip()
    if profile_ref:
        result = load_profile(profile_ref)
        if isinstance(result, ProfileError):
            errors.append(ValidationError(path, f"profile `{profile_ref}`: {result.message}"))
        else:
            profile_data = result.data
            task_format = profile_data.get("task_format")
            if isinstance(task_format, dict):
                allowed_statuses = task_format.get("allowed_statuses")
                if isinstance(allowed_statuses, list) and status_value:
                    if status_value not in allowed_statuses:
                        errors.append(
                            ValidationError(
                                path,
                                f"status `{status_value}` is not in profile `{profile_ref}` allowed_statuses: {allowed_statuses}",
                            )
                        )

                allowed_modes = task_format.get("allowed_execution_modes")
                if isinstance(allowed_modes, list) and execution_mode:
                    if execution_mode not in allowed_modes:
                        errors.append(
                            ValidationError(
                                path,
                                f"execution_mode `{execution_mode}` is not in profile `{profile_ref}` allowed_execution_modes: {allowed_modes}",
                            )
                        )

                extra_required_fm = task_format.get("required_front_matter")
                if isinstance(extra_required_fm, list):
                    core_required = TASK_REQUIRED_KEYS
                    for field in extra_required_fm:
                        if field not in core_required and field not in front_matter:
                            errors.append(
                                ValidationError(
                                    path,
                                    f"profile `{profile_ref}` requires additional front matter field `{field}`",
                                )
                            )

                extra_required_sections = task_format.get("required_sections")
                if isinstance(extra_required_sections, list):
                    core_sections = TASK_REQUIRED_SECTIONS
                    for section in extra_required_sections:
                        if section not in core_sections and section not in text:
                            errors.append(
                                ValidationError(
                                    path,
                                    f"profile `{profile_ref}` requires additional section `{section}`",
                                )
                            )

    return errors


def validate_progress_file(path: Path) -> list[ValidationError]:
    text = read_text(path)
    return [ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, PROGRESS_REQUIRED_LABELS)]


def validate_incident_file(path: Path) -> list[ValidationError]:
    text = read_text(path)
    return [ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, INCIDENT_REQUIRED_LABELS)]


def validate_delivery_file(path: Path) -> list[ValidationError]:
    text = read_text(path)
    return [ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, DELIVERY_REQUIRED_LABELS)]


def validate_review_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    text = read_text(path)
    errors.extend(
        ValidationError(path, f"missing label `{label}`") for label in has_all_labels(text, REVIEW_REQUIRED_LABELS)
    )

    decision_match = re.search(r"^- Decision:\s*(.+)$", text, re.MULTILINE)
    if decision_match:
        decision_value = decision_match.group(1).strip()
        if decision_value.lower() not in VALID_REVIEW_DECISIONS:
            errors.append(
                ValidationError(
                    path,
                    f"invalid decision value `{decision_value}`; must be one of {sorted(VALID_REVIEW_DECISIONS)}",
                )
            )

    return errors


PROFILE_REQUIRED_KEYS = {
    "profile_name",
    "schema_version",
    "description",
}
PROFILE_SCHEMA_VERSION = "1.0"

CORE_STATUSES = VALID_TASK_STATUSES
CORE_EXECUTION_MODES = VALID_EXECUTION_MODES


def parse_profile_front_matter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    block = text[4:end]
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def validate_profile_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    text = read_text(path)
    front_matter = parse_profile_front_matter(text)

    if front_matter is None:
        return [ValidationError(path, "missing or invalid front matter block")]

    missing_keys = sorted(PROFILE_REQUIRED_KEYS - set(front_matter))
    for key in missing_keys:
        errors.append(ValidationError(path, f"missing front matter key `{key}`"))

    profile_name = str(front_matter.get("profile_name", "")).strip()
    if not profile_name:
        errors.append(ValidationError(path, "`profile_name` must be non-empty"))

    schema_version = str(front_matter.get("schema_version", "")).strip()
    if schema_version and schema_version != PROFILE_SCHEMA_VERSION:
        errors.append(
            ValidationError(
                path,
                f"`schema_version` must be `{PROFILE_SCHEMA_VERSION}`, got `{schema_version}`",
            )
        )

    description = str(front_matter.get("description", "")).strip()
    if not description:
        errors.append(ValidationError(path, "`description` must be non-empty"))

    extends = front_matter.get("extends")
    if extends is not None and str(extends).strip() != "null":
        errors.append(
            ValidationError(
                path,
                f"`extends` must be null in schema v1, got `{extends}`",
            )
        )

    task_format = front_matter.get("task_format")
    if isinstance(task_format, dict):
        allowed_statuses = task_format.get("allowed_statuses")
        if allowed_statuses is not None:
            if not isinstance(allowed_statuses, list):
                errors.append(
                    ValidationError(path, "`allowed_statuses` must be a list, not a scalar")
                )
            else:
                for status_val in allowed_statuses:
                    status_str = str(status_val).strip()
                    if status_str and status_str not in CORE_STATUSES:
                        errors.append(
                            ValidationError(
                                path,
                                f"`allowed_statuses` contains unrecognized value `{status_str}`; "
                                f"must be a subset of {sorted(CORE_STATUSES)}",
                            )
                        )
        allowed_modes = task_format.get("allowed_execution_modes")
        if allowed_modes is not None:
            if not isinstance(allowed_modes, list):
                errors.append(
                    ValidationError(path, "`allowed_execution_modes` must be a list, not a scalar")
                )
            else:
                for mode_val in allowed_modes:
                    mode_str = str(mode_val).strip()
                    if mode_str and mode_str not in CORE_EXECUTION_MODES:
                        errors.append(
                            ValidationError(
                                path,
                                f"`allowed_execution_modes` contains unrecognized value `{mode_str}`; "
                                f"must be a subset of {sorted(CORE_EXECUTION_MODES)}",
                            )
                        )

    artifact_mapping = front_matter.get("artifact_mapping")
    if isinstance(artifact_mapping, dict):
        coord_structure = artifact_mapping.get("coordination_structure")
        if isinstance(coord_structure, dict):
            for key, val in coord_structure.items():
                path_str = str(val).strip()
                is_absolute = (
                    path_str.startswith("/")
                    or path_str.startswith("\\")
                    or re.match(r"^[A-Za-z]:[\\\/]", path_str) is not None
                    or path_str.startswith("//")
                )
                if ".." in path_str or is_absolute:
                    errors.append(
                        ValidationError(
                            path,
                            f"`artifact_mapping.coordination_structure.{key}` contains unsafe path `{path_str}`",
                        )
                    )

    return errors


def iter_markdown_files(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*.md") if p.is_file())


def validate_templates() -> list[ValidationError]:
    errors: list[ValidationError] = []
    template_map = {
        TEMPLATES_DIR / "task-packet.md": validate_task_file,
        TEMPLATES_DIR / "progress-report.md": validate_progress_file,
        TEMPLATES_DIR / "incident-report.md": validate_incident_file,
        TEMPLATES_DIR / "review-report.md": validate_review_file,
        TEMPLATES_DIR / "delivery-report.md": validate_delivery_file,
    }

    for path, validator in template_map.items():
        if not path.exists():
            errors.append(ValidationError(path, "template file is missing"))
            continue
        errors.extend(validator(path))

    return errors


def validate_repo_files() -> list[ValidationError]:
    errors: list[ValidationError] = []

    profile_names: dict[str, Path] = {}
    profile_files = [
        p for p in iter_markdown_files(PROFILES_DIR)
        if p.name not in ("README.md", "schema-profile-v1.md")
    ]
    for path in profile_files:
        errors.extend(validate_profile_file(path))
        front_matter = parse_profile_front_matter(read_text(path))
        if front_matter:
            pname = str(front_matter.get("profile_name", "")).strip()
            if pname:
                if pname in profile_names:
                    errors.append(
                        ValidationError(
                            path,
                            f"duplicate `profile_name` `{pname}`; first defined in {profile_names[pname].relative_to(ROOT)}",
                        )
                    )
                else:
                    profile_names[pname] = path

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

    delivery_dir = COORDINATION_DIR / "delivery"
    for path in iter_markdown_files(delivery_dir):
        errors.extend(validate_delivery_file(path))

    for path in iter_markdown_files(TASK_BOARD_DIR):
        if path.name == "README.md" or path.parent.name not in ("review", "done"):
            continue
        text = read_text(path)
        front_matter = parse_front_matter(text)
        if front_matter is None:
            continue
        artifacts = front_matter.get("expected_artifacts")
        if not isinstance(artifacts, list) or "delivery_report" not in artifacts:
            continue
        task_id = str(front_matter.get("task_id", ""))
        if not task_id:
            continue
        expected_delivery_file = delivery_dir / f"{task_id}-delivery-report.md"
        if not expected_delivery_file.exists():
            errors.append(
                ValidationError(
                    path,
                    f"task lists `delivery_report` in expected_artifacts but no matching delivery report found at `{expected_delivery_file.relative_to(ROOT)}`",
                )
            )

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
