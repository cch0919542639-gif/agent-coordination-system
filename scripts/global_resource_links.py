"""Safely validate, plan, and explicitly create shared-resource junctions."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_TYPES = {"skill", "knowledge", "design"}
REQUIRED_RESOURCE_KEYS = {
    "name",
    "type",
    "source_path",
    "source_url",
    "description",
    "invocation",
    "targets",
}
REQUIRED_TARGET_KEYS = {"runtime", "directory", "link_name"}


@dataclass(frozen=True)
class LinkPlan:
    resource_name: str
    source: Path
    target: Path
    action: str
    detail: str


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser().resolve(strict=False)


def is_safe_link_name(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and Path(value).name == value


def load_registry(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read registry: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("Registry root must be an object.")
    return data


def validate_registry(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'.")
    resources = data.get("resources")
    if not isinstance(resources, list):
        return errors + ["resources must be a list."]

    names: set[str] = set()
    for index, resource in enumerate(resources, start=1):
        prefix = f"resources[{index}]"
        if not isinstance(resource, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        missing = sorted(REQUIRED_RESOURCE_KEYS - resource.keys())
        if missing:
            errors.append(f"{prefix} is missing: {', '.join(missing)}.")
            continue
        name = resource["name"]
        if not isinstance(name, str) or not is_safe_link_name(name):
            errors.append(f"{prefix}.name must be a safe directory name.")
        elif name in names:
            errors.append(f"Duplicate resource name: {name}.")
        else:
            names.add(name)
        if resource["type"] not in VALID_TYPES:
            errors.append(f"{prefix}.type must be one of: {', '.join(sorted(VALID_TYPES))}.")
        if not isinstance(resource["source_path"], str) or not resource["source_path"].strip():
            errors.append(f"{prefix}.source_path must be a non-empty string.")
        targets = resource["targets"]
        if not isinstance(targets, list) or not targets:
            errors.append(f"{prefix}.targets must be a non-empty list.")
            continue
        for target_index, target in enumerate(targets, start=1):
            target_prefix = f"{prefix}.targets[{target_index}]"
            if not isinstance(target, dict):
                errors.append(f"{target_prefix} must be an object.")
                continue
            missing = sorted(REQUIRED_TARGET_KEYS - target.keys())
            if missing:
                errors.append(f"{target_prefix} is missing: {', '.join(missing)}.")
                continue
            if not isinstance(target["directory"], str) or not target["directory"].strip():
                errors.append(f"{target_prefix}.directory must be a non-empty string.")
            if not isinstance(target["link_name"], str) or not is_safe_link_name(target["link_name"]):
                errors.append(f"{target_prefix}.link_name must be a safe directory name.")
    return errors


def is_junction(path: Path) -> bool:
    junction_check = getattr(os.path, "isjunction", None)
    is_windows_junction = bool(junction_check(path)) if junction_check else False
    return path.exists() and path.is_dir() and (is_windows_junction or os.path.islink(path))


def build_plan(data: dict[str, Any]) -> list[LinkPlan]:
    plans: list[LinkPlan] = []
    for resource in data["resources"]:
        source = expand_path(resource["source_path"])
        for target_info in resource["targets"]:
            target = expand_path(target_info["directory"]) / target_info["link_name"]
            if not source.is_dir():
                action, detail = "blocked", "source directory is missing"
            elif target.exists() or target.is_symlink():
                if is_junction(target) and target.resolve() == source:
                    action, detail = "already-linked", "junction points to source"
                else:
                    action, detail = "blocked", "target exists and will not be replaced"
            else:
                action, detail = "create", "safe to create directory junction"
            plans.append(LinkPlan(resource["name"], source, target, action, detail))
    return plans


def print_plan(plans: list[LinkPlan], as_json: bool) -> None:
    if as_json:
        print(json.dumps([plan.__dict__ | {"source": str(plan.source), "target": str(plan.target)} for plan in plans], indent=2))
        return
    for plan in plans:
        print(f"[{plan.action}] {plan.resource_name}: {plan.target}")
        print(f"  source: {plan.source}")
        print(f"  detail: {plan.detail}")


def apply_plans(plans: list[LinkPlan]) -> int:
    if os.name != "nt":
        print("apply is supported only on Windows directory junctions.", file=sys.stderr)
        return 2
    blocked = [plan for plan in plans if plan.action == "blocked"]
    if blocked:
        print("Refusing apply because the plan contains blocked targets.", file=sys.stderr)
        return 2
    for plan in plans:
        if plan.action != "create":
            continue
        plan.target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(plan.target), str(plan.source)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"Failed to create {plan.target}: {result.stderr.strip() or result.stdout.strip()}", file=sys.stderr)
            return result.returncode or 1
        print(f"[created] {plan.resource_name}: {plan.target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "plan", "apply"))
    parser.add_argument("registry", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    try:
        registry = load_registry(args.registry)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    errors = validate_registry(registry)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print("Global resource registry validation passed.")
        return 0
    plans = build_plan(registry)
    print_plan(plans, args.as_json)
    if args.command == "plan":
        return 2 if any(plan.action == "blocked" for plan in plans) else 0
    return apply_plans(plans)


if __name__ == "__main__":
    raise SystemExit(main())
