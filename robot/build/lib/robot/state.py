"""Thread-safe latest-value store. It has no hardware-control methods."""
from __future__ import annotations
from dataclasses import replace
from threading import RLock
from robot.types import DistanceFact, Lifecycle, SceneReport, Snapshot

class WorldState:
    def __init__(self, now_ms: int = 0) -> None:
        invalid = DistanceFact(None, now_ms, now_ms, "unavailable", invalid_reason="source_error")
        self._lock = RLock()
        self._snapshot = Snapshot(now_ms, Lifecycle.BOOTING, invalid, invalid, invalid)

    def update_sensor(self, channel: str, fact: DistanceFact) -> None:
        if channel not in {"left", "center", "right"}:
            raise ValueError("unknown protective channel")
        with self._lock:
            self._snapshot = replace(self._snapshot, **{channel: fact})

    def update_scene(self, scene: SceneReport | None, status: str) -> None:
        if status not in {"online", "degraded", "offline"}:
            raise ValueError("invalid VLM health")
        with self._lock:
            self._snapshot = replace(self._snapshot, scene=scene, vlm_status=status)

    def update_lifecycle(self, lifecycle: Lifecycle, *, manual_kill=False, motor_fault=False) -> None:
        with self._lock:
            self._snapshot = replace(self._snapshot, lifecycle=lifecycle, manual_kill=manual_kill, motor_fault=motor_fault)

    def snapshot(self, now_ms: int) -> Snapshot:
        with self._lock:
            return replace(self._snapshot, monotonic_now_ms=now_ms)
