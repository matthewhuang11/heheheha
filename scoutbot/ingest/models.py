"""Validation models for the public ingestion API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scoutbot.types import Survivor


class SightingEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)
    time: str = Field(min_length=1, max_length=64)
    survivor_id: str = Field(min_length=1, max_length=128)
    x_cm: float
    y_cm: float
    uncertainty_cm: float = Field(ge=0)
    source: Literal["yolo", "gemini", "sim"]
    confidence: float = Field(ge=0, le=1)


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=128)
    time: str = Field(min_length=1, max_length=64)
    mode: Literal["STOPPED", "AUTO", "MANUAL"]
    action: Literal["STOP", "FORWARD", "FORWARD_SLOW", "TURN_LEFT", "TURN_RIGHT", "BACK_UP"]
    rule: int | str
    left_cm: float
    center_cm: float
    right_cm: float
    internet: bool
    x_cm: float
    y_cm: float


class IngestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["survivor", "sighting", "telemetry"]
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_payload(self):
        parsed: BaseModel
        if self.kind == "survivor":
            parsed = Survivor.model_validate(self.payload)
        elif self.kind == "sighting":
            parsed = SightingEvent.model_validate(self.payload)
        else:
            parsed = TelemetryEvent.model_validate(self.payload)
        self.payload = parsed.model_dump(mode="json")
        return self


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[IngestItem] = Field(min_length=1, max_length=500)
