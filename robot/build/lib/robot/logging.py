"""Minimal append-only JSONL event writer for replay-safe control evidence."""
from __future__ import annotations
import json
from pathlib import Path
from uuid import uuid4
from robot.types import Decision, GateResult, Snapshot

class JsonlLogger:
    def __init__(self, path: str | Path, run_id: str | None = None) -> None:
        self.path, self.run_id, self.sequence = Path(path), run_id or str(uuid4()), 0
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def control_tick(self, snapshot: Snapshot, decision: Decision, result: GateResult) -> None:
        now = snapshot.monotonic_now_ms
        sensor = lambda value: {"validity": value.validity, "distance_cm": value.distance_cm, "age_ms": max(0, now - value.observed_ms)}
        event = {"log_schema_version": "log/v1", "event_type": "control_tick", "event_id": str(uuid4()), "run_id": self.run_id, "sequence": self.sequence, "monotonic_ms": now, "lifecycle_state": snapshot.lifecycle.value, "sensors": {"left": sensor(snapshot.left), "center": sensor(snapshot.center), "right": sensor(snapshot.right)}, "vlm_status": snapshot.vlm_status, "decision": {"requested_action": decision.action.value, "rule_id": decision.rule_id}, "safety": {"final_action": result.action.value, "motion_permit": "issued" if result.permitted else "denied", "veto_reasons": sorted(result.veto_reasons)}}
        with self.path.open("a", encoding="utf-8") as sink:
            sink.write(json.dumps(event, separators=(",", ":")) + "\n")
        self.sequence += 1
