"""New shared data shapes (spec section 3.4). Existing shapes (Sensors, SceneReport, Action) stay in robot/types.py."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from robot.types import Action

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

class Mode(str, Enum):
    STOPPED = "STOPPED"; AUTO = "AUTO"; MANUAL = "MANUAL"

class DriveCommand(BaseModel):
    action: Action
    seq: int = 0
    received_at: float = 0.0          # robot monotonic time

class PersonDetection(BaseModel):
    source: Literal["yolo", "gemini", "sim"]
    where: Literal["left", "center", "right"]
    distance: Literal["near", "mid", "far"]
    confidence: float
    bbox: tuple[float, float, float, float] | None = None   # normalized x1, y1, x2, y2
    at: float = 0.0

class Pose(BaseModel):
    x_cm: float = 0.0
    y_cm: float = 0.0
    heading_deg: float = 0.0
    uncertainty_cm: float = 30.0
    source: Literal["dead_reckoning", "sim", "imu"] = "dead_reckoning"

YNU = Literal["yes", "no", "unknown"]

class TriageFacts(BaseModel):
    model_config = ConfigDict(extra="ignore")
    responsive: YNU = "unknown"
    can_walk: YNU = "unknown"
    trapped: YNU = "unknown"
    visible_bleeding: YNU = "unknown"
    breathing_trouble: YNU = "unknown"
    hazards_nearby: list[str] = Field(default_factory=list, max_length=12)
    injuries_reported: list[str] = Field(default_factory=list, max_length=12)
    summary: str = Field(default="", max_length=240)

class Triage(BaseModel):
    category: Literal["IMMEDIATE", "DELAYED", "MINOR", "UNKNOWN"]
    rule: str
    facts: TriageFacts
    model: str
    preliminary: Literal[True] = True
    at: str = Field(default_factory=utc_now)

class ChatMessage(BaseModel):
    survivor_id: str
    role: Literal["survivor", "robot", "responder"]
    text: str
    source: Literal["typed", "speech", "gemini", "ollama", "responder", "canned"]
    at: str = Field(default_factory=utc_now)

class Survivor(BaseModel):
    id: str
    first_seen: str
    last_seen: str
    pose: Pose
    sightings: int = 1
    best_snapshot: str | None = None
    snapshots: list[str] = Field(default_factory=list)
    best_box_frac: float = 0.0
    triage: Triage | None = None
    chat: list[ChatMessage] = Field(default_factory=list)
    version: int = 1
    handled_at: str | None = None          # when a responder pressed "Continue search" (KI-38); None = not handled
