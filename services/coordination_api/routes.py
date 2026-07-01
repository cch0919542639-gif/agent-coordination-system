from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from services.coordination_api.repository import (
    create_assignment,
    create_task_event,
    find_active_assignment,
    find_agent,
    find_task,
    find_tasks_by_agent_and_status,
    update_task_status,
)
from services.coordination_api.models import Task

router = APIRouter()

VALID_TASK_STATUSES = {
    "draft", "ready", "assigned", "claimed", "in_progress",
    "blocked", "review", "needs_fix", "accepted", "done",
    "reassigned", "cancelled",
}


@router.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, body: dict):
    agent_id = body.get("agent_id", "")
    reason = body.get("assignment_reason", "")

    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    agent = find_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if task["status"] in ("assigned", "claimed", "in_progress", "done", "cancelled", "accepted"):
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot be assigned",
        )

    existing = find_active_assignment(task_id)
    if existing is not None:
        raise HTTPException(status_code=400, detail="Task already has an active assignment")

    assignment_id = create_assignment(task_id, agent_id, reason)
    update_task_status(task_id, "assigned")
    event_id = create_task_event(
        task_id, "task_assigned", "orchestrator", agent_id,
        {"agent_id": agent_id, "assignment_id": assignment_id, "reason": reason},
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "assigned",
        "assignment_id": assignment_id,
        "event_id": event_id,
    }


@router.get("/tasks")
async def list_tasks(agent_id: str = "", status: str = ""):
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id query parameter is required")
    if not status:
        raise HTTPException(status_code=400, detail="status query parameter is required")
    if status not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")

    tasks = find_tasks_by_agent_and_status(agent_id, status)
    return {"ok": True, "tasks": tasks}


@router.post("/tasks/{task_id}/claim")
async def claim_task(task_id: str, body: dict):
    agent_id = body.get("agent_id", "")

    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "assigned":
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot be claimed (must be 'assigned')",
        )

    assignment = find_active_assignment(task_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="No active assignment found for this task")

    if assignment["agent_id"] != agent_id:
        raise HTTPException(
            status_code=403,
            detail="Task is assigned to a different agent",
        )

    update_task_status(task_id, "in_progress")
    event_id = create_task_event(
        task_id, "task_claimed", "agent", agent_id,
        {"agent_id": agent_id, "assignment_id": assignment["assignment_id"]},
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "in_progress",
        "event_id": event_id,
    }
