"""Dependency-free strict validator for vlm-contract/v1."""
from __future__ import annotations
import json
from robot.types import SceneReport

_PATHS = {"clear", "partially_blocked", "blocked", "unknown"}
_DIRECTIONS = {"left", "center", "right", "none"}
_TERRAINS = {"flat", "rubble", "uneven", "stairs_or_drop", "water", "unknown"}
_HAZARDS = {"fire", "smoke", "water", "wire", "glass", "drop_off", "unstable_debris", "other"}
_DISTANCES = {"near", "mid", "far"}
_REQUIRED = {"schema_version", "path_ahead", "best_direction", "terrain", "hazards", "people", "confidence", "notes"}

class ValidationError(ValueError):
    pass

def validate(raw: str | dict, *, observed_ms: int, frame_observed_ms: int, now_ms: int, ttl_ms: int = 6000) -> SceneReport:
    """Accept exactly one V1 report, without coercion or partial trust."""
    if now_ms - frame_observed_ms > ttl_ms or now_ms < frame_observed_ms:
        raise ValidationError("frame timestamp is unusable")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError) as error:
        raise ValidationError("malformed JSON") from error
    if not isinstance(value, dict) or set(value) != _REQUIRED or value.get("schema_version") != 1:
        raise ValidationError("wrong schema")
    if value["path_ahead"] not in _PATHS or value["best_direction"] not in _DIRECTIONS or value["terrain"] not in _TERRAINS:
        raise ValidationError("invalid enum")
    if type(value["confidence"]) not in (int, float) or not 0 <= value["confidence"] <= 1:
        raise ValidationError("invalid confidence")
    if not isinstance(value["notes"], str) or len(value["notes"]) > 240 or any(ord(c) < 32 or ord(c) == 127 for c in value["notes"]):
        raise ValidationError("invalid notes")
    hazards = value["hazards"]
    if not isinstance(hazards, list) or len(hazards) > 12:
        raise ValidationError("invalid hazards")
    for hazard in hazards:
        if not isinstance(hazard, dict) or set(hazard) != {"type", "where", "distance"} or hazard["type"] not in _HAZARDS or hazard["where"] not in _DIRECTIONS - {"none"} or hazard["distance"] not in _DISTANCES:
            raise ValidationError("invalid hazard")
    people = value["people"]
    if not isinstance(people, dict) or set(people) != {"visible", "where", "distance"} or type(people["visible"]) is not bool:
        raise ValidationError("invalid people")
    if people["visible"] and (people["where"] not in _DIRECTIONS - {"none"} or people["distance"] not in _DISTANCES):
        raise ValidationError("inconsistent visible person")
    if not people["visible"] and (people["where"], people["distance"]) != ("none", "none"):
        raise ValidationError("inconsistent absent person")
    return SceneReport(1, value["path_ahead"], value["best_direction"], value["terrain"], tuple(hazards), people["visible"], people["where"], people["distance"], float(value["confidence"]), value["notes"], observed_ms, frame_observed_ms + ttl_ms)
