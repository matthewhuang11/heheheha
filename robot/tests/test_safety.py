from robot.brain.decide import decide
from robot.brain.safety import gate
from robot.fakes.motors import FakeMotors
from robot.types import Action, DistanceFact, Lifecycle, SceneReport, Snapshot


def distance(cm=100, *, valid=True):
    return DistanceFact(cm if valid else None, 900, 1500, "valid" if valid else "invalid", invalid_reason="none" if valid else "no_echo")


def scene(**changes):
    values = dict(schema_version=1, path_ahead="clear", best_direction="center", terrain="flat", hazards=(), people_visible=False, people_where="none", people_distance="none", confidence=1.0, notes="", observed_ms=900, expires_ms=6000)
    values.update(changes)
    return SceneReport(**values)


def snapshot(**changes):
    values = dict(monotonic_now_ms=1000, lifecycle=Lifecycle.ACTIVE, left=distance(), center=distance(), right=distance(), scene=scene(), vlm_status="online", decision_started_ms=1000, last_renewed_ms=1000)
    values.update(changes)
    return Snapshot(**values)


def test_clear_scene_can_proceed_and_motor_requires_fresh_permit():
    value = snapshot()
    result = gate(decide(value).action, value)
    assert result.action is Action.FORWARD and result.permitted
    motors = FakeMotors()
    assert motors.execute(result, Lifecycle.ACTIVE, 1000) is Action.FORWARD
    assert motors.execute(result, Lifecycle.ACTIVE, 1151) is Action.STOP


def test_invalid_one_protective_sensor_fails_closed():
    value = snapshot(right=distance(valid=False))
    assert decide(value).action is Action.STOP
    result = gate(Action.FORWARD_SLOW, value)
    assert "sensor_invalid" in result.veto_reasons
    assert result.latched_fault == "SENSOR_FAULT"


def test_clearance_boundaries_are_conservative():
    assert gate(Action.FORWARD, snapshot(center=distance(59))).action is Action.STOP
    assert gate(Action.FORWARD_SLOW, snapshot(center=distance(39))).action is Action.STOP
    assert gate(Action.FORWARD_SLOW, snapshot(left=distance(24))).action is Action.STOP
    assert gate(Action.TURN_LEFT, snapshot(left=distance(24))).action is Action.STOP


def test_person_and_vlm_loss_stop_motion():
    assert decide(snapshot(scene=scene(people_visible=True, people_where="left", people_distance="far"))).action is Action.STOP
    result = gate(Action.FORWARD, snapshot(scene=None, vlm_status="offline"))
    assert result.action is Action.STOP and "vlm_fault" in result.veto_reasons
    assert result.latched_fault == "VLM_FAULT"


def test_side_obstacle_turns_away_without_vlm_direction_authority():
    decision = decide(snapshot(left=distance(24), scene=scene(best_direction="left")))
    assert decision.action is Action.TURN_RIGHT


def test_reverse_and_nonactive_never_permit_motion():
    assert gate("BACK_UP", snapshot()).action is Action.STOP
    assert gate(Action.FORWARD, snapshot(lifecycle=Lifecycle.READY)).action is Action.STOP


def test_decision_and_renewal_timeouts_stop_motion():
    assert "decision_timeout" in gate(Action.FORWARD, snapshot(decision_started_ms=-2001)).veto_reasons
    assert "renewal_expired" in gate(Action.FORWARD, snapshot(last_renewed_ms=499)).veto_reasons
