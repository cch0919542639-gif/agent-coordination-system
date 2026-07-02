#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Tuple

import httpx

BASE_URL_ENV = "COORDINATION_API_BASE_URL"
API_KEY_ENV = "COORDINATION_API_KEY"
DEFAULT_BASE_URL = "http://localhost:8000"
REPO_SYNC_DB_PATH_ENV = "COORDINATION_DB_PATH"

PASS = "PASS"
FAIL = "FAIL"

_results: List[Tuple[str, str, str]] = []


def _result(group: str, name: str, status: str, detail: str = "") -> None:
    _results.append((group, name, status))
    prefix = f"[{group}] {name}"
    if status == PASS:
        print(f"  {prefix}: {PASS}")
    else:
        print(f"  {prefix}: {FAIL}  {detail}", file=sys.stderr)


def _req(
    client: httpx.Client,
    method: str,
    path: str,
    expect_status: int,
    **kwargs: Any,
) -> Tuple[httpx.Response, bool, str]:
    url = f"{_base_url}{path}"
    headers = kwargs.pop("headers", {})
    if _api_key:
        headers.setdefault("X-API-Key", _api_key)
    try:
        resp = client.request(method, url, headers=headers, **kwargs)
    except httpx.ConnectError as e:
        return httpx.Response(503), False, f"connection failed: {e}"
    ok = resp.status_code == expect_status
    detail = f"got {resp.status_code}, expected {expect_status}" if not ok else ""
    return resp, ok, detail


def smoke_health(client: httpx.Client) -> None:
    g = "health"
    resp, ok, detail = _req(client, "GET", "/health", 200)
    _result(g, "health endpoint", PASS if ok else FAIL, detail)
    if ok:
        body = resp.json()
        _result(g, "status field", PASS if body.get("status") == "ok" else FAIL, str(body))
        _result(g, "version field", PASS if body.get("version") == "0.1.0" else FAIL, str(body))


def smoke_auth_disabled(client: httpx.Client, no_key_client: httpx.Client) -> None:
    g = "auth-disabled"
    resp, ok, detail = _req(no_key_client, "GET", "/health", 200)
    _result(g, "no key allowed when disabled", PASS if ok else FAIL, detail)
    resp, ok, detail = _req(client, "GET", "/health", 200)
    _result(g, "valid key allowed when disabled", PASS if ok else FAIL, detail)


def smoke_auth_required(client: httpx.Client, no_key_client: httpx.Client) -> None:
    g = "auth-required"
    resp, ok, detail = _req(no_key_client, "GET", "/health", 401)
    _result(g, "reject missing key", PASS if ok else FAIL, detail)
    resp, ok, detail = _req(client, "GET", "/health", 200)
    _result(g, "accept valid key", PASS if ok else FAIL, detail)
    bad_key_client = httpx.Client(headers={"X-API-Key": "invalid-key-do-not-use"}, timeout=10)
    resp, ok, detail = _req(bad_key_client, "GET", "/health", 401)
    _result(g, "reject invalid key", PASS if ok else FAIL, detail)


def smoke_lifecycle(
    client: httpx.Client,
    task_id: str,
    agent_id: str,
    api_key_orch: str,
) -> None:
    g = "lifecycle"
    orch_client = httpx.Client(headers={"X-API-Key": api_key_orch}) if api_key_orch else client

    resp, ok, detail = _req(
        orch_client, "POST", f"/tasks/{task_id}/assign",
        200, json={"agent_id": agent_id, "assignment_reason": "Smoke test"},
    )
    _result(g, "assign", PASS if ok else FAIL, detail)

    resp, ok, detail = _req(
        client, "GET", f"/tasks?agent_id={agent_id}&status=assigned", 200,
    )
    _result(g, "poll", PASS if ok else FAIL, detail)

    resp, ok, detail = _req(
        client, "POST", f"/tasks/{task_id}/claim", 200,
        json={"agent_id": agent_id},
    )
    _result(g, "claim", PASS if ok else FAIL, detail)

    resp, ok, detail = _req(
        client, "POST", f"/tasks/{task_id}/progress", 200,
        json={"agent_id": agent_id, "current_step": "Smoke test", "blocker_status": "none"},
    )
    _result(g, "progress", PASS if ok else FAIL, detail)

    resp, ok, detail = _req(
        client, "POST", f"/tasks/{task_id}/submit", 200,
        json={"agent_id": agent_id, "summary": "Smoke test complete"},
    )
    _result(g, "submit", PASS if ok else FAIL, detail)

    resp, ok, detail = _req(
        orch_client, "POST", f"/tasks/{task_id}/review", 200,
        json={"reviewer_id": "orchestrator", "decision": "accepted", "summary": "Smoke accepted"},
    )
    _result(g, "review", PASS if ok else FAIL, detail)


def smoke_incident(client: httpx.Client, task_id: str, agent_id: str) -> None:
    g = "incident"
    resp, ok, detail = _req(
        client, "POST", f"/tasks/{task_id}/incidents", 200,
        json={
            "agent_id": agent_id,
            "severity": "low",
            "summary": "Smoke test incident",
            "category": "environment_failure",
        },
    )
    _result(g, "open incident", PASS if ok else FAIL, detail)
    if ok:
        incident_id = resp.json().get("incident_id", "")
        _result(g, "incident id returned", PASS if incident_id else FAIL)


def smoke_heartbeat(client: httpx.Client, task_id: str, agent_id: str) -> None:
    g = "heartbeat"
    resp, ok, detail = _req(
        client, "POST", f"/tasks/{task_id}/heartbeat", 200,
        json={"agent_id": agent_id, "status": "in_progress"},
    )
    _result(g, "heartbeat", PASS if ok else FAIL, detail)

    resp, ok, detail = _req(client, "GET", "/heartbeat/expired", 200)
    _result(g, "expired list", PASS if ok else FAIL, detail)


def smoke_repo_sync(db_path: str) -> None:
    g = "repo-sync"
    cmd = [sys.executable, "-m", "scripts.repo_sync", "--db-path", db_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _result(g, "invocation", FAIL, result.stderr.strip())
    else:
        _result(g, "invocation", PASS)


def print_summary() -> None:
    print()
    print("=" * 50)
    print("SMOKE TEST SUMMARY")
    print("=" * 50)
    total = len(_results)
    passed = sum(1 for _, _, s in _results if s == PASS)
    failed = total - passed
    for group, name, status in _results:
        line = f"  [{group}] {name}: {status}"
        print(line)
    print(f"\n{passed}/{total} passed, {failed} failed")
    if failed > 0:
        print("SOME CHECKS FAILED — review output above", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch-day smoke-test helper for the coordination API."
    )
    parser.add_argument(
        "--task-id", default="smoke-task-01",
        help="Task ID to use for lifecycle tests (default: smoke-task-01)",
    )
    parser.add_argument(
        "--agent-id", default="agent-smoke",
        help="Agent ID to use for lifecycle tests (default: agent-smoke)",
    )
    parser.add_argument(
        "--orchestrator-api-key", default="",
        help="Orchestrator API key for assign/review (default: same as agent key)",
    )
    parser.add_argument(
        "--db-path", default=None,
        help="Database path for repo-sync test (default: $COORDINATION_DB_PATH or coordination.db)",
    )
    parser.add_argument(
        "--skip-auth-test", action="store_true",
        help="Skip auth enforcement test (use when auth is disabled)",
    )
    args = parser.parse_args()

    global _base_url, _api_key
    _base_url = os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL).rstrip("/")
    _api_key = os.environ.get(API_KEY_ENV, "")
    db_path = args.db_path or os.environ.get(REPO_SYNC_DB_PATH_ENV, "coordination.db")

    agent_id = args.agent_id
    task_id = args.task_id
    orch_key = args.orchestrator_api_key or _api_key

    no_key_client = httpx.Client(timeout=10)
    client = httpx.Client(headers={"X-API-Key": _api_key}, timeout=10) if _api_key else no_key_client

    print(f"Coordination API smoke test")
    print(f"  Base URL: {_base_url}")
    print(f"  API Key:  {'<set>' if _api_key else '<not set>'}")
    print(f"  Task ID:  {task_id}")
    print(f"  Agent ID: {agent_id}")
    print(f"  DB Path:  {db_path}")
    print()

    if _api_key and not args.skip_auth_test:
        smoke_auth_required(client, no_key_client)
    elif not _api_key:
        smoke_auth_disabled(client, no_key_client)
    else:
        print("[auth] skipped (--skip-auth-test)")

    smoke_health(client)
    smoke_lifecycle(client, task_id, agent_id, orch_key)
    smoke_incident(client, task_id, agent_id)
    smoke_heartbeat(client, task_id, agent_id)
    smoke_repo_sync(db_path)

    print_summary()
    _, failed = len(_results), sum(1 for _, _, s in _results if s == FAIL)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
