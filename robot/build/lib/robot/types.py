"""Shared immutable data shapes for the controlled DRR V1 runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional


class Action(str, Enum):
    STOP = "STOP"
    FORWARD = "FORWARD"
    FORWARD_SLOW = "FORWARD_SLOW"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"


class Lifecycle(str, Enum):
    BOOTING = "BOOTING"
    SELF_TEST = "SELF_TEST"
    READY = "READY"
    ACTIVE = "ACTIVE"
    FAILSAFE_LATCHED = "FAILSAFE_LATCHED"
    E_STOP_LATCHED = "E_STOP_LATCHED"
    SHUTDOWN = "SHUTDOWN"


@dataclass(frozen=True)
class DistanceFact:
    distance_cm: Optional[float]
    observed_ms: int
    expires_ms: int
    validity: str = "valid"
    source_id: str = "ultrasonic"
    invalid_reason: str = "none"

    def usable(self, now_ms: int) -> bool:
        return (self.validity == "valid" and self.distance_cm is not None
                and 2.0 <= self.distance_cm <= 400.0 and now_ms < self.expires_ms)


@dataclass(frozen=True)
class SceneReport:
    schema_version: int
    path_ahead: str
    best_direction: str
    terrain: str
    hazards: tuple[dict, ...]
    people_visible: bool
    people_where: str
    people_distance: str
    confidence: float
    notes: str
    observed_ms: int
    expires_ms: int

    def usable(self, now_ms: int) -> bool:
        return now_ms < self.expires_ms


@dataclass(frozen=True)
class Snapshot:
    monotonic_now_ms: int
    lifecycle: Lifecycle
    left: DistanceFact
    center: DistanceFact
    right: DistanceFact
    scene: Optional[SceneReport] = None
    vlm_status: str = "offline"
    motor_fault: bool = False
    manual_kill: bool = False
    decision_started_ms: Optional[int] = None
    last_renewed_ms: Optional[int] = None
    turn_attempts_ms: tuple[int, ...] = ()
    forward_travel_ms: tuple[int, ...] = ()

    @property
    def sensors(self) -> tuple[DistanceFact, DistanceFact, DistanceFact]:
        return self.left, self.center, self.right

    def all_sensors_usable(self) -> bool:
        return all(sensor.usable(self.monotonic_now_ms) for sensor in self.sensors)


@dataclass(frozen=True)
class Decision:
    action: Action
    rule_id: int


@dataclass(frozen=True)
class GateResult:
    action: Action
    permit_issued_at_ms: Optional[int]
    veto_reasons: FrozenSet[str] = field(default_factory=frozenset)
    latched_fault: Optional[str] = None

    @property
    def permitted(self) -> bool:
        return self.action is not Action.STOP and self.permit_issued_at_ms is not None
