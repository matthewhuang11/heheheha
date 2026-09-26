#!/usr/bin/env python3
"""Replay V1 control JSONL against its recorded snapshots without motors."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from robot.brain.decide import decide
from robot.brain.safety import gate
from robot.types import DistanceFact, Lifecycle, Snapshot

def replay(path: str | Path) -> list[dict]:
    outcomes = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event_type") != "control_tick":
            continue
        now = event["monotonic_ms"]
        def fact(name: str) -> DistanceFact:
            value = event["sensors"][name]
            return DistanceFact(value["distance_cm"], now - value["age_ms"], now + max(1, 500 - value["age_ms"]), value["validity"])
        snapshot = Snapshot(now, Lifecycle(event["lifecycle_state"]), fact("left"), fact("center"), fact("right"), vlm_status=event["vlm_status"])
        decision = decide(snapshot)
        gated = gate(decision.action, snapshot)
        outcomes.append({"sequence": event["sequence"], "requested_action": decision.action.value, "final_action": gated.action.value})
    return outcomes

if __name__ == "__main__":
    rows = replay(sys.argv[1])
    print(json.dumps(rows, separators=(",", ":")))
