from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from services.coordination_api.database import LEASE_DURATION_SECONDS, get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def find_task(task_id: str) -> Optional[Dict]:
    with get_db() as db:
        row = db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def find_agent(agent_id: str) -> Optional[Dict]:
    with get_db() as db:
        row = db.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def find_active_assignment(task_id: str) -> Optional[Dict]:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM assignments WHERE task_id = ? AND closed_at IS NULL",
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def create_assignment(task_id: str, agent_id: str, reason: str) -> str:
    assignment_id = _new_id()
    now = _now()
    from datetime import timedelta, timezone
    lease_exp = (datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_SECONDS)).isoformat()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at, assignment_reason, lease_expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (assignment_id, task_id, agent_id, now, reason, lease_exp),
        )
        db.commit()
    return assignment_id


def update_task_status(task_id: str, status: str) -> None:
    now = _now()
    with get_db() as db:
        db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
            (status, now, task_id),
        )
        db.commit()


def create_task_event(
    task_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str,
    payload: Optional[Dict] = None,
) -> str:
    event_id = _new_id()
    now = _now()
    payload_json = json.dumps(payload or {})
    with get_db() as db:
        db.execute(
            """
            INSERT INTO task_events (event_id, task_id, event_type, actor_type, actor_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, task_id, event_type, actor_type, actor_id, payload_json, now),
        )
        db.commit()
    return event_id


def create_incident(
    task_id: str,
    agent_id: str,
    severity: str,
    category: str,
    summary: str,
    details: str,
    proposed_resolution: str,
) -> str:
    incident_id = _new_id()
    now = _now()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO incidents
                (incident_id, task_id, agent_id, severity, category, summary,
                 details, proposed_resolution, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (incident_id, task_id, agent_id, severity, category, summary,
             details, proposed_resolution, now),
        )
        db.commit()
    return incident_id


def refresh_lease(task_id: str) -> None:
    from datetime import timedelta, timezone
    lease_exp = (datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_SECONDS)).isoformat()
    with get_db() as db:
        db.execute(
            "UPDATE assignments SET lease_expires_at = ? WHERE task_id = ? AND closed_at IS NULL",
            (lease_exp, task_id),
        )
        db.commit()


def find_expired_assignments() -> List[Dict]:
    now = _now()
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM assignments WHERE closed_at IS NULL AND lease_expires_at IS NOT NULL AND lease_expires_at < ?",
            (now,),
        ).fetchall()
    return [dict(r) for r in rows]


def recover_expired_claim(task_id: str) -> Optional[str]:
    now = _now()
    assignment = find_active_assignment(task_id)
    if assignment is None:
        return None
    lease_exp = assignment.get("lease_expires_at")
    if lease_exp is None or lease_exp > now:
        return None
    old_id = assignment["assignment_id"]
    with get_db() as db:
        db.execute(
            "UPDATE assignments SET closed_at = ? WHERE assignment_id = ?",
            (now, old_id),
        )
        db.commit()
    return old_id


def close_assignment(task_id: str) -> None:
    now = _now()
    with get_db() as db:
        db.execute(
            "UPDATE assignments SET closed_at = ? WHERE task_id = ? AND closed_at IS NULL",
            (now, task_id),
        )
        db.commit()


def create_artifact(
    task_id: str,
    artifact_type: str,
    path_or_url: str,
    repo_ref: str,
    commit_hash: str,
) -> str:
    artifact_id = _new_id()
    now = _now()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO artifacts (artifact_id, task_id, artifact_type, path_or_url, repo_ref, commit_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, task_id, artifact_type, path_or_url, repo_ref, commit_hash, now),
        )
        db.commit()
    return artifact_id


def find_artifact(artifact_id: str) -> Optional[Dict]:
    with get_db() as db:
        row = db.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
    return dict(row) if row else None


def find_artifacts_by_task(task_id: str) -> List[Dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM artifacts WHERE task_id = ? ORDER BY created_at", (task_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def create_review(
    task_id: str,
    reviewer_id: str,
    decision: str,
    summary: str = "",
    findings: Optional[List[Dict]] = None,
    required_changes: Optional[List[str]] = None,
) -> str:
    review_id = _new_id()
    now = _now()
    findings_json = json.dumps(findings or [])
    changes_json = json.dumps(required_changes or [])
    with get_db() as db:
        db.execute(
            """
            INSERT INTO reviews (review_id, task_id, reviewer_id, decision, summary, findings, required_changes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (review_id, task_id, reviewer_id, decision, summary, findings_json, changes_json, now),
        )
        db.commit()
    return review_id


def find_incident(incident_id: str) -> Optional[Dict]:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
    return dict(row) if row else None


def resolve_incident(incident_id: str, resolver_id: str, resolution_summary: str) -> None:
    now = _now()
    with get_db() as db:
        db.execute(
            """
            UPDATE incidents
            SET status = 'resolved', resolved_at = ?, resolution_summary = ?, resolver_id = ?
            WHERE incident_id = ?
            """,
            (now, resolution_summary, resolver_id, incident_id),
        )
        db.commit()


def find_tasks_by_agent_and_status(agent_id: str, status: str) -> List[Dict]:
    with get_db() as db:
        rows = db.execute(
            """
            SELECT t.* FROM tasks t
            JOIN assignments a ON a.task_id = t.task_id
            WHERE a.agent_id = ? AND t.status = ? AND a.closed_at IS NULL
            """,
            (agent_id, status),
        ).fetchall()
    return [dict(r) for r in rows]
