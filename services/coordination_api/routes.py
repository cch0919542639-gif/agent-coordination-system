from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from services.coordination_api.repository import (
    close_assignment,
    create_artifact,
    create_assignment,
    create_incident,
    create_review,
    create_task_event,
    find_active_assignment,
    find_agent,
    find_artifact,
    find_artifacts_by_task,
    find_expired_assignments,
    find_incident,
    find_task,
    find_tasks_by_agent_and_status,
    recover_expired_claim,
    refresh_lease,
    resolve_incident,
    update_task_status,
)
from services.coordination_api.models import Task

router = APIRouter()

VALID_TASK_STATUSES = {
    "draft", "ready", "assigned", "claimed", "in_progress",
    "blocked", "review", "needs_fix", "accepted", "done",
    "reassigned", "cancelled",
}

ALLOWED_PROGRESS_STATUSES = {"claimed", "in_progress"}
ALLOWED_INCIDENT_STATUSES = {"claimed", "in_progress", "blocked"}
ALLOWED_SUBMIT_STATUSES = {"in_progress", "blocked"}
ALLOWED_HEARTBEAT_STATUSES = {"claimed", "in_progress"}

VALID_REVIEW_DECISIONS = {"accepted", "needs_fix", "reassign", "rejected"}
DECISION_STATUS_MAP = {
    "accepted": "accepted",
    "needs_fix": "in_progress",
    "reassign": "assigned",
    "rejected": "cancelled",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


@router.post("/tasks/{task_id}/progress")
async def report_progress(task_id: str, body: dict):
    agent_id = body.get("agent_id", "")

    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in ALLOWED_PROGRESS_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot accept progress (must be 'claimed' or 'in_progress')",
        )

    assignment = find_active_assignment(task_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="No active assignment found for this task")

    if assignment["agent_id"] != agent_id:
        raise HTTPException(
            status_code=403,
            detail="Task is assigned to a different agent",
        )

    new_status = task["status"]
    if new_status == "claimed":
        new_status = "in_progress"
        update_task_status(task_id, new_status)

    event_id = create_task_event(
        task_id, "progress_reported", "agent", agent_id,
        {
            "agent_id": agent_id,
            "current_step": body.get("current_step", ""),
            "changed_files": body.get("changed_files", []),
            "blocker_status": body.get("blocker_status", "none"),
            "next_step": body.get("next_step", ""),
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": new_status,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/tasks/{task_id}/incidents")
async def open_incident(task_id: str, body: dict):
    agent_id = body.get("agent_id", "")

    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    severity = body.get("severity", "")
    if severity not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="severity must be 'low', 'medium', or 'high'")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in ALLOWED_INCIDENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot accept incidents "
                   f"(must be 'claimed', 'in_progress', or 'blocked')",
        )

    assignment = find_active_assignment(task_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="No active assignment found for this task")

    if assignment["agent_id"] != agent_id:
        raise HTTPException(
            status_code=403,
            detail="Task is assigned to a different agent",
        )

    if task["status"] != "blocked":
        update_task_status(task_id, "blocked")

    incident_id = create_incident(
        task_id, agent_id, severity,
        body.get("category", ""),
        body.get("summary", ""),
        body.get("details", ""),
        body.get("proposed_resolution", ""),
    )
    event_id = create_task_event(
        task_id, "incident_opened", "agent", agent_id,
        {
            "agent_id": agent_id,
            "incident_id": incident_id,
            "severity": severity,
            "category": body.get("category", ""),
            "summary": body.get("summary", ""),
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "blocked",
        "incident_id": incident_id,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/tasks/{task_id}/artifacts")
async def attach_artifact(task_id: str, body: dict):
    artifact_type = body.get("artifact_type", "")
    if not artifact_type:
        raise HTTPException(status_code=400, detail="artifact_type is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    artifact_id = create_artifact(
        task_id, artifact_type,
        body.get("path_or_url", ""),
        body.get("repo_ref", ""),
        body.get("commit_hash", ""),
    )
    event_id = create_task_event(
        task_id, "artifact_attached", "agent", body.get("agent_id", "unknown"),
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "path_or_url": body.get("path_or_url", ""),
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "artifact_id": artifact_id,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/tasks/{task_id}/submit")
async def submit_for_review(task_id: str, body: dict):
    agent_id = body.get("agent_id", "")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in ALLOWED_SUBMIT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot be submitted "
                   f"(must be 'in_progress' or 'blocked')",
        )

    assignment = find_active_assignment(task_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="No active assignment found for this task")

    if assignment["agent_id"] != agent_id:
        raise HTTPException(
            status_code=403,
            detail="Task is assigned to a different agent",
        )

    artifact_ids = body.get("artifact_ids", [])
    summary = body.get("summary", "")

    if not artifact_ids and not summary:
        raise HTTPException(
            status_code=400,
            detail="Submission requires at least one artifact or a delivery summary",
        )

    if artifact_ids:
        for aid in artifact_ids:
            artifact = find_artifact(aid)
            if artifact is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Artifact '{aid}' not found",
                )
            if artifact["task_id"] != task_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Artifact '{aid}' does not belong to this task",
                )

    update_task_status(task_id, "review")
    event_id = create_task_event(
        task_id, "submitted_for_review", "agent", agent_id,
        {
            "agent_id": agent_id,
            "artifact_ids": artifact_ids,
            "summary": summary,
            "validation_notes": body.get("validation_notes", []),
            "residual_risks": body.get("residual_risks", []),
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "review",
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/tasks/{task_id}/review")
async def review_task(task_id: str, body: dict):
    reviewer_id = body.get("reviewer_id", "")
    if not reviewer_id:
        raise HTTPException(status_code=400, detail="reviewer_id is required")

    decision = body.get("decision", "")
    if not decision:
        raise HTTPException(status_code=400, detail="decision is required")
    if decision not in VALID_REVIEW_DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{decision}'; must be one of {sorted(VALID_REVIEW_DECISIONS)}",
        )

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "review":
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot be reviewed (must be 'review')",
        )

    accepted_artifact_ids = body.get("accepted_artifact_ids", [])
    if accepted_artifact_ids:
        for aid in accepted_artifact_ids:
            artifact = find_artifact(aid)
            if artifact is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Artifact '{aid}' not found",
                )
            if artifact["task_id"] != task_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Artifact '{aid}' does not belong to this task",
                )

    new_status = DECISION_STATUS_MAP[decision]
    if decision == "reassign":
        close_assignment(task_id)
    update_task_status(task_id, new_status)

    review_id = create_review(
        task_id, reviewer_id, decision,
        summary=body.get("summary", ""),
        findings=body.get("findings", []),
        required_changes=body.get("required_changes", []),
    )

    event_type = "review_completed"
    event_id = create_task_event(
        task_id, event_type, "reviewer", reviewer_id,
        {
            "reviewer_id": reviewer_id,
            "review_id": review_id,
            "decision": decision,
            "summary": body.get("summary", ""),
            "findings": body.get("findings", []),
            "required_changes": body.get("required_changes", []),
            "accepted_artifact_ids": accepted_artifact_ids,
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": new_status,
        "review_id": review_id,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/tasks/{task_id}/reassign")
async def reassign_task(task_id: str, body: dict):
    from_agent_id = body.get("from_agent_id", "")
    to_agent_id = body.get("to_agent_id", "")
    reason = body.get("reason", "")

    if not from_agent_id:
        raise HTTPException(status_code=400, detail="from_agent_id is required")
    if not to_agent_id:
        raise HTTPException(status_code=400, detail="to_agent_id is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] in ("done", "cancelled", "accepted"):
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot be reassigned",
        )

    to_agent = find_agent(to_agent_id)
    if to_agent is None:
        raise HTTPException(status_code=404, detail="Target agent not found")

    assignment = find_active_assignment(task_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="No active assignment found for this task")

    if assignment["agent_id"] != from_agent_id:
        raise HTTPException(
            status_code=400,
            detail=f"from_agent_id '{from_agent_id}' does not match the current assignee '{assignment['agent_id']}'",
        )

    old_assignment_id = assignment["assignment_id"]
    close_assignment(task_id)
    new_assignment_id = create_assignment(task_id, to_agent_id, f"Reassigned: {reason}")
    update_task_status(task_id, "assigned")

    event_id = create_task_event(
        task_id, "task_reassigned", "orchestrator", from_agent_id,
        {
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "reason": reason,
            "previous_assignment_id": old_assignment_id,
            "new_assignment_id": new_assignment_id,
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "assigned",
        "previous_assignment_id": old_assignment_id,
        "new_assignment_id": new_assignment_id,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/tasks/{task_id}/heartbeat")
async def heartbeat(task_id: str, body: dict):
    agent_id = body.get("agent_id", "")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in ALLOWED_HEARTBEAT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task['status']}' and cannot accept heartbeats "
                   f"(must be 'claimed' or 'in_progress')",
        )

    assignment = find_active_assignment(task_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="No active assignment found for this task")

    if assignment["agent_id"] != agent_id:
        raise HTTPException(
            status_code=403,
            detail="Task is assigned to a different agent",
        )

    refresh_lease(task_id)
    event_id = create_task_event(
        task_id, "heartbeat_received", "agent", agent_id,
        {
            "agent_id": agent_id,
            "status": body.get("status", task["status"]),
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.get("/heartbeat/expired")
async def list_expired():
    expired = find_expired_assignments()
    return {"ok": True, "expired_assignments": expired}


@router.post("/tasks/{task_id}/recover")
async def recover_task(task_id: str, body: dict):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    old_id = recover_expired_claim(task_id)
    if old_id is None:
        raise HTTPException(
            status_code=400,
            detail="Task has no expired claim to recover",
        )

    update_task_status(task_id, "assigned")
    event_id = create_task_event(
        task_id, "lease_expired", "orchestrator", body.get("orchestrator_id", "system"),
        {
            "recovered_assignment_id": old_id,
            "previous_status": task["status"],
        },
    )

    return {
        "ok": True,
        "task_id": task_id,
        "status": "assigned",
        "recovered_assignment_id": old_id,
        "event_id": event_id,
        "updated_at": _now(),
    }


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident_endpoint(incident_id: str, body: dict):
    resolver_id = body.get("resolver_id", "")
    if not resolver_id:
        raise HTTPException(status_code=400, detail="resolver_id is required")

    incident = find_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident["status"] != "open":
        raise HTTPException(
            status_code=400,
            detail=f"Incident is in status '{incident['status']}' and is not open",
        )

    resolution_summary = body.get("resolution_summary", "")
    resolve_incident(incident_id, resolver_id, resolution_summary)

    task_id = incident["task_id"]
    event_id = create_task_event(
        task_id, "incident_resolved", "reviewer", resolver_id,
        {
            "incident_id": incident_id,
            "resolver_id": resolver_id,
            "resolution_summary": resolution_summary,
        },
    )

    return {
        "ok": True,
        "incident_id": incident_id,
        "task_id": task_id,
        "status": "resolved",
        "event_id": event_id,
        "updated_at": _now(),
    }
