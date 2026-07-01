from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Agent:
    agent_id: str
    name: str
    created_at: str


@dataclass
class Phase:
    phase_id: str
    name: str
    objective: str = ""
    status: str = "planning"
    entry_criteria: List[str] = field(default_factory=list)
    exit_criteria: List[str] = field(default_factory=list)
    frozen_spec_ref: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Task:
    task_id: str
    phase_id: str
    title: str = ""
    objective: str = ""
    description: str = ""
    priority: str = "medium"
    status: str = "draft"
    allowed_scope: List[str] = field(default_factory=list)
    forbidden_scope: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    expected_artifacts: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Assignment:
    assignment_id: str
    task_id: str
    agent_id: str
    assigned_at: str
    assignment_reason: str = ""
    closed_at: Optional[str] = None


@dataclass
class TaskEvent:
    event_id: str
    task_id: str
    event_type: str
    actor_type: str
    actor_id: str
    payload: Dict = field(default_factory=dict)
    created_at: str = ""


@dataclass
class Incident:
    incident_id: str
    task_id: str
    agent_id: str
    severity: str
    category: str = ""
    summary: str = ""
    details: str = ""
    proposed_resolution: str = ""
    status: str = "open"
    resolved_at: Optional[str] = None
    resolution_summary: str = ""
    resolver_id: str = ""
    created_at: str = ""


@dataclass
class Review:
    review_id: str
    task_id: str
    reviewer_id: str
    decision: str
    summary: str = ""
    findings: List[Dict] = field(default_factory=list)
    required_changes: List[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class Artifact:
    artifact_id: str
    task_id: str
    artifact_type: str
    path_or_url: str = ""
    repo_ref: str = ""
    commit_hash: str = ""
    created_at: str = ""
