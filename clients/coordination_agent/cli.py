import argparse
import sys
from typing import List

from clients.coordination_agent.client import CoordinationClient


def _print_json(data) -> None:
    import json
    print(json.dumps(data, indent=2, default=str))


def _error(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_poll(client: CoordinationClient, args: argparse.Namespace) -> None:
    tasks = client.poll(args.agent_id, args.status)
    if not tasks:
        print("No tasks found.")
        return
    for t in tasks:
        print(f"  {t['task_id']:50s} status={t['status']}")


def cmd_claim(client: CoordinationClient, args: argparse.Namespace) -> None:
    result = client.claim(args.task_id, args.agent_id)
    _print_json(result)


def cmd_heartbeat(client: CoordinationClient, args: argparse.Namespace) -> None:
    result = client.heartbeat(args.task_id, args.agent_id, args.status)
    _print_json(result)


def cmd_progress(client: CoordinationClient, args: argparse.Namespace) -> None:
    files: List[str] = args.files.split(",") if args.files else []
    result = client.progress(
        args.task_id, args.agent_id,
        current_step=args.step,
        changed_files=[f.strip() for f in files if f.strip()],
        blocker_status=args.blocker,
        next_step=args.next,
    )
    _print_json(result)


def cmd_incident(client: CoordinationClient, args: argparse.Namespace) -> None:
    result = client.incident(
        args.task_id, args.agent_id,
        severity=args.severity,
        summary=args.summary,
        category=args.category,
        details=args.details,
        proposed_resolution=args.resolution,
    )
    _print_json(result)


def cmd_artifact(client: CoordinationClient, args: argparse.Namespace) -> None:
    result = client.artifact(
        args.task_id,
        artifact_type=args.type,
        path_or_url=args.path,
        repo_ref=args.repo_ref,
        commit_hash=args.commit,
    )
    _print_json(result)


def cmd_submit(client: CoordinationClient, args: argparse.Namespace) -> None:
    ids: List[str] = args.artifact_ids.split(",") if args.artifact_ids else []
    notes: List[str] = args.validation_notes.split(",") if args.validation_notes else []
    risks: List[str] = args.residual_risks.split(",") if args.residual_risks else []
    result = client.submit(
        args.task_id, args.agent_id,
        artifact_ids=[i.strip() for i in ids if i.strip()],
        summary=args.summary,
        validation_notes=[n.strip() for n in notes if n.strip()],
        residual_risks=[r.strip() for r in risks if r.strip()],
    )
    _print_json(result)


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="coordination-agent",
        description="CLI client for the Coordination API control plane.",
    )
    parser.add_argument("--base-url", help="API base URL (default: $COORDINATION_API_BASE_URL or http://localhost:8000)")
    parser.add_argument("--api-key", help="API key (default: $COORDINATION_API_KEY)")

    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p_poll = sub.add_parser("poll", help="List assigned tasks")
    p_poll.add_argument("--agent-id", required=True)
    p_poll.add_argument("--status", default="assigned")
    p_poll.set_defaults(func=cmd_poll)

    p_claim = sub.add_parser("claim", help="Claim a task")
    p_claim.add_argument("task_id")
    p_claim.add_argument("--agent-id", required=True)
    p_claim.set_defaults(func=cmd_claim)

    p_hb = sub.add_parser("heartbeat", help="Send a heartbeat")
    p_hb.add_argument("task_id")
    p_hb.add_argument("--agent-id", required=True)
    p_hb.add_argument("--status", default="in_progress")
    p_hb.set_defaults(func=cmd_heartbeat)

    p_prog = sub.add_parser("progress", help="Report progress")
    p_prog.add_argument("task_id")
    p_prog.add_argument("--agent-id", required=True)
    p_prog.add_argument("--step", default="", help="Current step description")
    p_prog.add_argument("--files", default="", help="Comma-separated changed files")
    p_prog.add_argument("--blocker", default="none", help="Blocker status")
    p_prog.add_argument("--next", default="", help="Next planned step")
    p_prog.set_defaults(func=cmd_progress)

    p_inc = sub.add_parser("incident", help="Open an incident")
    p_inc.add_argument("task_id")
    p_inc.add_argument("--agent-id", required=True)
    p_inc.add_argument("--severity", required=True, choices=["low", "medium", "high"])
    p_inc.add_argument("--summary", required=True)
    p_inc.add_argument("--category", default="")
    p_inc.add_argument("--details", default="")
    p_inc.add_argument("--resolution", default="", help="Proposed resolution")
    p_inc.set_defaults(func=cmd_incident)

    p_art = sub.add_parser("artifact", help="Attach an artifact")
    p_art.add_argument("task_id")
    p_art.add_argument("--type", required=True, dest="type", help="Artifact type (e.g. repo_file)")
    p_art.add_argument("--path", default="", help="File path or URL")
    p_art.add_argument("--repo-ref", default="")
    p_art.add_argument("--commit", default="")
    p_art.set_defaults(func=cmd_artifact)

    p_sub = sub.add_parser("submit", help="Submit for review")
    p_sub.add_argument("task_id")
    p_sub.add_argument("--agent-id", required=True)
    p_sub.add_argument("--artifact-ids", default="", help="Comma-separated artifact IDs")
    p_sub.add_argument("--summary", default="")
    p_sub.add_argument("--validation-notes", default="", help="Comma-separated notes")
    p_sub.add_argument("--residual-risks", default="", help="Comma-separated risks")
    p_sub.set_defaults(func=cmd_submit)

    parsed = parser.parse_args()

    client = CoordinationClient(base_url=parsed.base_url, api_key=parsed.api_key)
    try:
        parsed.func(client, parsed)
    except RuntimeError as e:
        _error(str(e))
