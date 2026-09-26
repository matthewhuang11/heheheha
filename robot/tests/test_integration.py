"""Public runtime integration checks using the same interfaces laptop callers use."""
from robot.app import ControlLoop, RESEARCH_STATUS
from robot.fakes.motors import FakeMotors
from robot.state import WorldState
from robot.types import DistanceFact, Lifecycle, SceneReport


def fact() -> DistanceFact:
    return DistanceFact(100.0, 1000, 1600)


def clear_scene() -> SceneReport:
    return SceneReport(1, "clear", "center", "flat", (), False, "none", "none", 1.0, "", 1000, 7000)


def active_state(*, with_scene: bool) -> WorldState:
    state = WorldState()
    for channel in ("left", "center", "right"):
        state.update_sensor(channel, fact())
    state.update_scene(clear_scene() if with_scene else None, "online" if with_scene else "offline")
    state.update_lifecycle(Lifecycle.ACTIVE)
    return state


def test_control_loop_permits_clear_baseline_motion():
    motors = FakeMotors()
    requested, result, rule = ControlLoop(active_state(with_scene=True), motors).tick(1000)
    assert (requested.value, result.action.value, rule) == ("FORWARD", "FORWARD", 8)
    assert motors.motor_enabled


def test_control_loop_latches_baseline_vlm_loss():
    state, motors = active_state(with_scene=False), FakeMotors()
    requested, result, rule = ControlLoop(state, motors).tick(1000)
    assert requested.value == result.action.value == "STOP"
    assert result.latched_fault == "VLM_FAULT"
    assert not motors.motor_enabled
    assert state.snapshot(1000).lifecycle is Lifecycle.FAILSAFE_LATCHED


def test_research_only_status_is_publicly_exposed():
    assert RESEARCH_STATUS == "RESEARCH TEST ONLY – NOT FOR RESCUE OR PUBLIC USE"
