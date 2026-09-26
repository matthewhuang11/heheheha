import json
import pytest
from robot.lifecycle import LifecycleController
from robot.types import Lifecycle
from robot.vlm.validate import ValidationError, validate


def report():
    return {"schema_version": 1, "path_ahead": "clear", "best_direction": "center", "terrain": "flat", "hazards": [], "people": {"visible": False, "where": "none", "distance": "none"}, "confidence": 0.5, "notes": ""}


def test_validator_accepts_only_exact_schema():
    accepted = validate(json.dumps(report()), observed_ms=1000, frame_observed_ms=1000, now_ms=1000)
    assert accepted.path_ahead == "clear"
    extra = report() | {"command": "FORWARD"}
    with pytest.raises(ValidationError):
        validate(extra, observed_ms=1000, frame_observed_ms=1000, now_ms=1000)
    malformed = report(); malformed["people"] = {"visible": False, "where": "left", "distance": "none"}
    with pytest.raises(ValidationError):
        validate(malformed, observed_ms=1000, frame_observed_ms=1000, now_ms=1000)


def test_latched_state_requires_physical_reset_then_self_test_and_start():
    controller = LifecycleController()
    assert controller.transition(Lifecycle.SELF_TEST)
    assert controller.transition(Lifecycle.READY, self_test_ok=True)
    assert controller.transition(Lifecycle.ACTIVE, local_start=True)
    controller.manual_kill()
    assert controller.state is Lifecycle.E_STOP_LATCHED
    assert not controller.transition(Lifecycle.SELF_TEST)
    assert controller.transition(Lifecycle.SELF_TEST, physical_reset=True)
    assert controller.transition(Lifecycle.READY, self_test_ok=True)
    assert not controller.transition(Lifecycle.ACTIVE)
    assert controller.transition(Lifecycle.ACTIVE, local_start=True)
