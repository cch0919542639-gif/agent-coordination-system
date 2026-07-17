#!/usr/bin/env python3
"""Opt-in worker-side polling command for Phase 12 event-driven orchestration.

Reads only the registered worker's project-scoped pending ready-assignment
notification payloads from the delivery state and renders a safe dispatch
message.  Never auto-claims, auto-executes, launches processes, or mutates
task lifecycle.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from coordination_common import ROOT

MONITOR_DIR = ROOT / "coordination" / "monitor"
WORKERS_FILE = MONITOR_DIR / "workers.json"

PROTOCOL_DOC = "docs/operations/agent-task-execution-protocol.md"
EXECUTION_DOC = "docs/operations/lead-agent-orchestration-protocol.md"
ASSIGNMENT_DOC = "docs/operations/worker-assignment-policy.md"

MIN_POLL_INTERVAL = 60
DEFAULT_POLL_INTERVAL = 600
DEFAULT_JITTER = 0.1


@dataclass
class WorkerRegistration:
    worker_id: str
    project_id: str
    enabled: bool = True
    registered_at: str = ""

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "project_id": self.project_id,
            "enabled": self.enabled,
            "registered_at": self.registered_at or _now_iso(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkerRegistration:
        return cls(
            worker_id=data["worker_id"],
            project_id=data.get("project_id", data.get("project", "")),
            enabled=data.get("enabled", True),
            registered_at=data.get("registered_at", ""),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_workers() -> list[WorkerRegistration]:
    if not WORKERS_FILE.exists():
        return []
    try:
        data = json.loads(WORKERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [WorkerRegistration.from_dict(entry) for entry in data if isinstance(entry, dict)]


def _save_workers(workers: list[WorkerRegistration]) -> None:
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    data = [w.to_dict() for w in workers]
    WORKERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def register_worker(worker_id: str, project_id: str) -> bool:
    workers = _load_workers()
    for w in workers:
        if w.worker_id == worker_id:
            if w.project_id != project_id:
                w.project_id = project_id
            w.enabled = True
            _save_workers(workers)
            return True
    workers.append(WorkerRegistration(
        worker_id=worker_id,
        project_id=project_id,
        enabled=True,
        registered_at=_now_iso(),
    ))
    _save_workers(workers)
    return True


def unregister_worker(worker_id: str) -> bool:
    workers = _load_workers()
    before = len(workers)
    workers = [w for w in workers if w.worker_id != worker_id]
    if len(workers) == before:
        return False
    _save_workers(workers)
    return True


def list_workers() -> list[WorkerRegistration]:
    return _load_workers()


def get_worker(worker_id: str) -> WorkerRegistration | None:
    for w in _load_workers():
        if w.worker_id == worker_id:
            return w
    return None


def _load_delivery_records() -> list[dict]:
    from event_routing import DELIVERY_FILE
    if not DELIVERY_FILE.exists():
        return []
    records: list[dict] = []
    for line in DELIVERY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def poll_worker(
    worker_id: str,
    output_json: bool = False,
) -> int:
    worker = get_worker(worker_id)
    if worker is None:
        print(f"Worker `{worker_id}` not registered.", file=sys.stderr)
        return 1
    if not worker.enabled:
        print(f"Worker `{worker_id}` is disabled.", file=sys.stderr)
        return 1

    records = _load_delivery_records()
    pending = [
        r for r in records
        if r.get("project_id") == worker.project_id
        and r.get("event_type") == "ready_assigned"
        and r.get("destination") == "registered_worker"
        and r.get("status") == "pending"
        and r.get("owner", "") == worker.worker_id
    ]

    if not pending:
        if output_json:
            print(json.dumps({"worker_id": worker_id, "notifications": []}, indent=2))
        else:
            print("No pending work.")
        return 0

    if output_json:
        safe_notifications = []
        for rec in pending:
            safe_notifications.append(_build_safe_payload(rec))
        print(json.dumps({
            "worker_id": worker_id,
            "project_id": worker.project_id,
            "notifications": safe_notifications,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Worker: {worker_id}  Project: {worker.project_id}")
        print(f"Pending notifications: {len(pending)}")
        print()
        for rec in pending:
            _render_notification(rec)
            print()

    return 0


def _build_safe_payload(rec: dict) -> dict:
    task_id = rec.get("task_id", "")
    return {
        "payload_id": rec.get("payload_id", ""),
        "project_id": rec.get("project_id", ""),
        "task_id": task_id,
        "event_type": rec.get("event_type", ""),
        "ref": rec.get("ref", ""),
        "commit": rec.get("commit", ""),
        "owner": rec.get("owner", ""),
        "reviewer": rec.get("reviewer", ""),
        "artifact_paths": rec.get("artifact_paths", []),
        "task_card_path": f"coordination/task-board/ready/{task_id}.md",
    }


def _render_notification(rec: dict) -> None:
    task_id = rec.get("task_id", "")
    project_id = rec.get("project_id", "")
    ref = rec.get("ref", "")
    commit = rec.get("commit", "")
    owner = rec.get("owner", "")
    reviewer = rec.get("reviewer", "")
    payload_id = rec.get("payload_id", "")
    artifact_paths = rec.get("artifact_paths", [])

    card_path = f"coordination/task-board/ready/{task_id}.md"

    print("=" * 60)
    print(f"  Task: {task_id}")
    print(f"  Project: {project_id}")
    print(f"  Ref: {ref}")
    print(f"  Commit: {commit[:12] if commit else ''}")
    print(f"  Owner: {owner}")
    print(f"  Reviewer: {reviewer}")
    print(f"  Card: {card_path}")
    if artifact_paths:
        print(f"  Artifact paths:")
        for p in artifact_paths:
            print(f"    - {p}")
    print()
    print("  Please pull the latest repo, then read:")
    print(f"  - {card_path}")
    print(f"  - {PROTOCOL_DOC}")
    print()
    print("  When you start:")
    print(f"  - move the task card to coordination/task-board/in_progress/")
    print(f"  - update coordination/progress/{owner}.md" if owner else "")
    print()
    print("  If blocked:")
    print("  - create an incident in coordination/incidents/")
    print("  - do not continue by guessing outside the task scope")
    print()
    print("  When finished:")
    print("  - move the task card to coordination/task-board/review/")
    print("  - submit repo-based delivery evidence and validation notes")
    print()
    print("  Protocol references:")
    print(f"  - {PROTOCOL_DOC}")
    print(f"  - {EXECUTION_DOC}")
    print(f"  - {ASSIGNMENT_DOC}")
    if reviewer:
        print(f"  Reviewer: {reviewer}")
    print()
    print(f"  Payload ID: {payload_id}")
    print(f"  (Use --acknowledge {payload_id} to confirm notification delivery)")
    print("=" * 60)


def acknowledge_delivery(payload_id: str) -> int:
    from event_routing import acknowledge
    result = acknowledge(payload_id)
    if result:
        print(f"Acknowledged delivery: {payload_id}")
        return 0
    else:
        print(f"Delivery record not found: {payload_id}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Activation — Phase 14 same-machine worker handoff
# ---------------------------------------------------------------------------

def activate_worker(worker_id: str, output_json: bool = False) -> int:
    """Emit one safe action payload for the first owner-matching pending delivery.

    Acknowledgement happens only after the payload is durably printed.
    Returns 0 on success, 1 on any failure (fail-closed).

    Constraints honoured:
    - No subprocess, HTTP, webhook, agent launch, or Codex/MiMo invocation.
    - No task-card claim, move, review, merge, commit, or push.
    - Empty or mismatched owner fails closed.
    """
    worker = get_worker(worker_id)
    if worker is None:
        print(f"Worker `{worker_id}` not registered.", file=sys.stderr)
        return 1
    if not worker.enabled:
        print(f"Worker `{worker_id}` is disabled.", file=sys.stderr)
        return 1

    records = _load_delivery_records()

    # Strict owner-strict filtering: only pending ready_assigned for this worker
    eligible = [
        r for r in records
        if r.get("project_id") == worker.project_id
        and r.get("event_type") == "ready_assigned"
        and r.get("destination") == "registered_worker"
        and r.get("status") == "pending"
        and r.get("owner", "") == worker.worker_id
    ]

    if not eligible:
        if output_json:
            print(json.dumps({"worker_id": worker_id, "activated": False, "reason": "no eligible delivery"}))
        else:
            print("No eligible delivery for activation.")
        return 0

    rec = eligible[0]
    payload_id = rec.get("payload_id", "")

    # Fail-closed: reject non-pending states
    status = rec.get("status", "")
    if status != "pending":
        reason = f"delivery status is '{status}', expected 'pending'"
        if output_json:
            print(json.dumps({"worker_id": worker_id, "activated": False, "reason": reason}))
        else:
            print(f"Activation rejected: {reason}", file=sys.stderr)
        return 1

    # Build the safe action payload for the local agent heartbeat
    action_payload = _build_activation_payload(rec)

    # Emit the payload durably (to stdout — the agent session reads it)
    if output_json:
        output = {"activated": True, **action_payload}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        _render_activation(action_payload)

    # Acknowledge only after the payload is durably available
    from event_routing import acknowledge
    acknowledge(payload_id)

    return 0


def _build_activation_payload(rec: dict) -> dict:
    """Build a safe, compact action payload from a delivery record.

    Never includes raw task body, prompt text, source code, or absolute paths.
    """
    task_id = rec.get("task_id", "")
    project_id = rec.get("project_id", "")
    return {
        "action": "ready_task_available",
        "worker_id": rec.get("owner", ""),
        "project_id": project_id,
        "task_id": task_id,
        "event_type": rec.get("event_type", ""),
        "ref": rec.get("ref", ""),
        "commit": rec.get("commit", ""),
        "reviewer": rec.get("reviewer", ""),
        "payload_id": rec.get("payload_id", ""),
        "task_card_path": f"coordination/task-board/ready/{task_id}.md",
        "protocol_path": PROTOCOL_DOC,
        "instructions": [
            "Pull the latest repo.",
            f"Read {PROTOCOL_DOC}.",
            f"Read coordination/task-board/ready/{task_id}.md",
            "Claim the task by moving the card to in_progress/.",
            "Execute within allowed scope.",
            "Submit for review when done.",
        ],
    }


def _render_activation(payload: dict) -> None:
    """Render a human-readable activation message."""
    print("=" * 60)
    print("  WORKER ACTIVATION — Phase 14 Local Handoff")
    print("=" * 60)
    print(f"  Worker:  {payload.get('worker_id', '')}")
    print(f"  Task:    {payload.get('task_id', '')}")
    print(f"  Project: {payload.get('project_id', '')}")
    print(f"  Ref:     {payload.get('ref', '')}")
    print(f"  Commit:  {payload.get('commit', '')[:12] if payload.get('commit') else ''}")
    print(f"  Reviewer:{payload.get('reviewer', '')}")
    print()
    print("  Next steps:")
    for i, step in enumerate(payload.get("instructions", []), 1):
        print(f"    {i}. {step}")
    print()
    print(f"  Card:    {payload.get('task_card_path', '')}")
    print(f"  Protocol:{payload.get('protocol_path', '')}")
    print(f"  Payload: {payload.get('payload_id', '')}")
    print("=" * 60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Opt-in worker-side polling for registered worker notifications.",
        epilog="Exit status: 0 on success, 1 on error.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # register
    reg_parser = subparsers.add_parser("register", help="Register a worker for a project.")
    reg_parser.add_argument("worker_id", help="Unique worker identifier.")
    reg_parser.add_argument("project_id", help="Project to register for.")

    # unregister
    unreg_parser = subparsers.add_parser("unregister", help="Unregister a worker.")
    unreg_parser.add_argument("worker_id", help="Worker identifier to remove.")

    # list
    list_parser = subparsers.add_parser("list", help="List registered workers.")

    # poll
    poll_parser = subparsers.add_parser("poll", help="Poll for pending notifications.")
    poll_parser.add_argument("worker_id", help="Registered worker identifier.")
    poll_parser.add_argument("--json", action="store_true", help="Output as JSON.")
    poll_parser.add_argument(
        "--interval", type=int, default=DEFAULT_POLL_INTERVAL,
        help=f"Poll interval in seconds for scheduler setup (default: {DEFAULT_POLL_INTERVAL}). Minimum: {MIN_POLL_INTERVAL}.",
    )
    poll_parser.add_argument(
        "--jitter", type=float, default=DEFAULT_JITTER,
        help=f"Random jitter as fraction of interval for scheduler setup (default: {DEFAULT_JITTER}).",
    )

    # acknowledge
    ack_parser = subparsers.add_parser("acknowledge", help="Acknowledge a delivery notification.")
    ack_parser.add_argument("payload_id", help="Payload ID to acknowledge.")

    # activate
    act_parser = subparsers.add_parser(
        "activate",
        help="Activate one owner-matching pending delivery for a worker.",
    )
    act_parser.add_argument("worker_id", help="Registered worker identifier.")
    act_parser.add_argument("--json", action="store_true", help="Output action payload as JSON.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "register":
        register_worker(args.worker_id, args.project_id)
        print(f"Registered worker `{args.worker_id}` for project `{args.project_id}`.")
        return 0

    if args.command == "unregister":
        if unregister_worker(args.worker_id):
            print(f"Unregistered worker `{args.worker_id}`.")
            return 0
        print(f"Worker `{args.worker_id}` not found.", file=sys.stderr)
        return 1

    if args.command == "list":
        workers = list_workers()
        if not workers:
            print("No workers registered.")
            return 0
        for w in workers:
            status = "enabled" if w.enabled else "disabled"
            print(f"  {w.worker_id} -> project={w.project_id} [{status}] registered={w.registered_at}")
        return 0

    if args.command == "poll":
        if args.interval is not None and args.interval < MIN_POLL_INTERVAL:
            print(f"ERROR: minimum interval is {MIN_POLL_INTERVAL} seconds.", file=sys.stderr)
            return 1
        return poll_worker(args.worker_id, output_json=args.json)

    if args.command == "acknowledge":
        return acknowledge_delivery(args.payload_id)

    if args.command == "activate":
        return activate_worker(args.worker_id, output_json=args.json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
