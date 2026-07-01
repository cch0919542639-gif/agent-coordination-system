from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from services.coordination_api.database import get_db


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
    with get_db() as db:
        db.execute(
            """
            INSERT INTO assignments (assignment_id, task_id, agent_id, assigned_at, assignment_reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (assignment_id, task_id, agent_id, now, reason),
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
