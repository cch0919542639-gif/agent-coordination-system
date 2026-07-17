#!/usr/bin/env python3
"""Idempotent event-routing runtime entry point for Phase 12.

Reads newly recorded monitor events from the event ledger and produces
delivery records according to project routing policy.  Preserves existing
acknowledgement, retry, and failed state.

Flow: event ledger -> routing policy -> delivery state

Never performs HTTP calls, webhooks, subprocess/agent launches, task
claims, review decisions, commits, pushes, or project task-card mutation.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from event_ledger import Event, load_events  # noqa: E402
from event_routing import (  # noqa: E402
    DeliveryRecord,
    NotificationPayload,
    append_delivery_records,
    load_delivery_state_map,
    route_event,
)


def route_pending_events(output_json: bool = False) -> int:
    """Process all pending events and produce delivery records.

    Returns 0 on success, 1 on error.
    """
    events = load_events()
    pending_events = [e for e in events if e.delivery_state == "pending"]

    if not pending_events:
        if output_json:
            print(json.dumps({
                "routed": 0,
                "skipped": 0,
                "details": [],
            }, indent=2))
        else:
            print("No pending events to route.")
        return 0

    existing_delivery = load_delivery_state_map()
    routed_records: list[DeliveryRecord] = []
    skipped = 0
    details: list[dict] = []

    for event in pending_events:
        results = route_event(
            project_id=event.project_id,
            task_id=event.task_id,
            event_type=event.event_type,
            ref=event.ref,
            commit=event.commit,
            owner="",
            reviewer="",
            artifact_paths=None,
        )

        for payload, record in results:
            if payload.payload_id in existing_delivery:
                skipped += 1
                details.append({
                    "event_id": event.event_id,
                    "task_id": event.task_id,
                    "event_type": event.event_type,
                    "project_id": event.project_id,
                    "status": "already_exists",
                })
                continue
            routed_records.append(record)
            details.append({
                "event_id": event.event_id,
                "task_id": event.task_id,
                "event_type": event.event_type,
                "project_id": event.project_id,
                "destination": record.destination,
                "status": "new",
                "payload_id": record.payload_id,
            })

    added = append_delivery_records(routed_records)

    if output_json:
        print(json.dumps({
            "routed": added,
            "skipped": skipped,
            "details": details,
        }, indent=2))
    else:
        border = "=" * 60
        print(border)
        print("  Event Routing Runner")
        print(border)
        print(f"  Pending events:  {len(pending_events)}")
        print(f"  New deliveries:  {added}")
        print(f"  Skipped (dup):   {skipped}")
        if details:
            print()
            print("  Details")
            print("  " + "-" * 56)
            for d in details:
                status_marker = "+" if d["status"] == "new" else "="
                print(f"  [{status_marker}] {d['project_id']} / {d['task_id']}")
                print(f"    event_type={d['event_type']} status={d['status']}")
                if "destination" in d:
                    print(f"    destination={d['destination']}")
        print(border)

    return 0
