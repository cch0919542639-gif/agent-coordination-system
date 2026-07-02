import os
from typing import Any, Dict, List, Optional

import httpx

BASE_URL_ENV = "COORDINATION_API_BASE_URL"
API_KEY_ENV = "COORDINATION_API_KEY"
DEFAULT_BASE_URL = "http://localhost:8000"


class CoordinationClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL)).rstrip("/")
        self.api_key = api_key or os.environ.get(API_KEY_ENV, "")
        self._client = httpx.Client(timeout=30)

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        resp = self._client.request(method, url, headers=headers, **kwargs)
        if resp.status_code >= 400:
            detail = resp.json().get("detail", resp.text)
            raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, json=body)

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        return self._request("GET", path, params=params)

    def poll(self, agent_id: str, status: str = "assigned") -> List[Dict[str, Any]]:
        data = self._get("/tasks", params={"agent_id": agent_id, "status": status})
        return data.get("tasks", [])

    def claim(self, task_id: str, agent_id: str) -> dict:
        return self._post(f"/tasks/{task_id}/claim", {"agent_id": agent_id})

    def heartbeat(self, task_id: str, agent_id: str, status: str = "in_progress") -> dict:
        return self._post(f"/tasks/{task_id}/heartbeat", {"agent_id": agent_id, "status": status})

    def progress(
        self,
        task_id: str,
        agent_id: str,
        current_step: str = "",
        changed_files: Optional[List[str]] = None,
        blocker_status: str = "none",
        next_step: str = "",
    ) -> dict:
        return self._post(
            f"/tasks/{task_id}/progress",
            {
                "agent_id": agent_id,
                "current_step": current_step,
                "changed_files": changed_files or [],
                "blocker_status": blocker_status,
                "next_step": next_step,
            },
        )

    def incident(
        self,
        task_id: str,
        agent_id: str,
        severity: str,
        summary: str,
        category: str = "",
        details: str = "",
        proposed_resolution: str = "",
    ) -> dict:
        return self._post(
            f"/tasks/{task_id}/incidents",
            {
                "agent_id": agent_id,
                "severity": severity,
                "category": category,
                "summary": summary,
                "details": details,
                "proposed_resolution": proposed_resolution,
            },
        )

    def artifact(
        self,
        task_id: str,
        artifact_type: str,
        path_or_url: str = "",
        repo_ref: str = "",
        commit_hash: str = "",
    ) -> dict:
        return self._post(
            f"/tasks/{task_id}/artifacts",
            {
                "artifact_type": artifact_type,
                "path_or_url": path_or_url,
                "repo_ref": repo_ref,
                "commit_hash": commit_hash,
            },
        )

    def submit(
        self,
        task_id: str,
        agent_id: str,
        artifact_ids: Optional[List[str]] = None,
        summary: str = "",
        validation_notes: Optional[List[str]] = None,
        residual_risks: Optional[List[str]] = None,
    ) -> dict:
        return self._post(
            f"/tasks/{task_id}/submit",
            {
                "agent_id": agent_id,
                "artifact_ids": artifact_ids or [],
                "summary": summary,
                "validation_notes": validation_notes or [],
                "residual_risks": residual_risks or [],
            },
        )
