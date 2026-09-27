from math import isclose
from robot.config import DEFAULT
from robot.types import Action
from scoutbot.control.mix import mix
from scoutbot.safety.deadman import manual_axes
from scoutbot.safety.gate import Gate
from scoutbot.types import DriveCommand, Mode

CFG = {
    "max_forward": 0.60, "slow_factor": 0.58, "max_reverse": 0.35,
    "max_turn_in_place": 0.45, "deadzone": 0.08, "expo": 0.0,
    "trim_left": 1.0, "trim_right": 1.0,
}
FAR = (200.0, 200.0, 200.0)


def test_mix_forward_turn_normalizes_and_applies_caps():
    assert mix(0.0, 0.0, CFG) == (0.0, 0.0)
    assert mix(1.0, 0.0, CFG) == (0.6, 0.6)
    assert mix(0.0, 1.0, CFG) == (0.45, -0.45)
    left, right = mix(1.0, 1.0, CFG)
    assert left > right > -1 and left <= 1


def test_mix_deadzone_trim_and_invert_are_applied_last():
    assert mix(0.08, 0.08, CFG) == (0.0, 0.0)
    left, right = mix(1, 0, {**CFG, "trim_left": 0.5, "invert_right": True})
    assert isclose(left, 0.3) and isclose(right, -0.6)


def test_manual_axes_expire_to_neutral():
    cmd = DriveCommand(v=.4, w=-.2, received_at=10)
    assert manual_axes(cmd, 10.2, .3) == (.4, -.2)
    assert manual_axes(cmd, 10.31, .3) == (0.0, 0.0)


def test_analog_gate_blocks_obstacles_and_turns_toward_walls():
    gate = Gate(DEFAULT)
    v, w, veto = gate.check_analog(.8, -.6, Mode.MANUAL, 10, 20, 10, True, 1.0)
    assert v == 0 and w == 0 and "ahead" in veto and "left" in veto

    v, w, veto = gate.check_analog(.8, 0, Mode.MANUAL, 200, 50, 200, True, 2.0)
    assert 0 < v < .8 and w == 0 and "capped at slow" in veto

    v, w, veto = gate.check_analog(.8, 0, Mode.MANUAL, 200, None, 200, True, 2.0)
    assert 0 < v < .8 and w == 0 and "capped at slow" in veto


def test_analog_gate_stale_and_reverse_bursts_stop():
    gate = Gate(DEFAULT, backup_max_s=1.5, backup_rest_s=.5)
    assert gate.check_analog(.4, .2, Mode.MANUAL, *FAR, False, 1.0)[:2] == (0.0, 0.0)
    assert gate.check_analog(-.8, 0, Mode.MANUAL, *FAR, True, 2.0, .35)[0] == -.35
    assert gate.check_analog(-.2, 0, Mode.MANUAL, *FAR, True, 3.6)[:2] == (0.0, 0.0)
    assert gate.check_analog(-.2, 0, Mode.MANUAL, *FAR, True, 3.8)[:2] == (0.0, 0.0)
    assert gate.check_analog(-.2, 0, Mode.MANUAL, *FAR, True, 4.2)[0] < 0
