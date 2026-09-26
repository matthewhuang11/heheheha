from robot.types import Action as A
from scoutbot.safety.gate import Gate
from scoutbot.types import Mode

g = lambda: Gate()
FAR = (200, 200, 200)

def chk(gate, action, mode=Mode.MANUAL, lcr=FAR, fresh=True, now=10.0, yolo=False):
    return gate.check(action, mode, *lcr, fresh, now, yolo)

def test_stopped_mode_always_stops():
    for a in A: assert chk(g(), a, Mode.STOPPED).action == A.STOP

def test_stale_or_all_invalid_stops_in_both_modes():
    for m in (Mode.AUTO, Mode.MANUAL):
        assert chk(g(), A.FORWARD, m, fresh=False).action == A.STOP
        assert chk(g(), A.TURN_LEFT, m, lcr=(None, None, None)).action == A.STOP

def test_forward_into_close_obstacle_is_vetoed():
    r = chk(g(), A.FORWARD, lcr=(200, 20, 200)); assert r.action == A.STOP and "blocked" in r.veto
    r = chk(g(), A.FORWARD_SLOW, Mode.AUTO, lcr=(200, 20, 200)); assert r.action == A.STOP

def test_full_speed_capped_when_center_limited_or_no_echo():
    assert chk(g(), A.FORWARD, lcr=(200, 45, 200)).action == A.FORWARD_SLOW
    assert chk(g(), A.FORWARD, lcr=(200, None, 200)).action == A.FORWARD_SLOW
    assert chk(g(), A.FORWARD, lcr=(200, 150, 200)).action == A.FORWARD

def test_manual_turn_into_close_side_is_vetoed():
    assert chk(g(), A.TURN_LEFT, lcr=(10, 200, 200)).action == A.STOP
    assert chk(g(), A.TURN_RIGHT, lcr=(200, 200, 10)).action == A.STOP
    assert chk(g(), A.TURN_RIGHT, lcr=(10, 200, 200)).action == A.TURN_RIGHT   # turning away is fine

def test_backup_is_time_limited():
    gate = g()
    assert chk(gate, A.BACK_UP, now=0.0).action == A.BACK_UP
    assert chk(gate, A.BACK_UP, now=1.4).action == A.BACK_UP
    r = chk(gate, A.BACK_UP, now=1.6); assert r.action == A.STOP and "backed up" in r.veto
    assert chk(gate, A.BACK_UP, now=1.8).action == A.STOP        # resting
    assert chk(gate, A.BACK_UP, now=2.2).action == A.BACK_UP     # can back up again

def test_yolo_person_hold_blocks_forward_only():
    assert chk(g(), A.FORWARD, Mode.AUTO, yolo=True).action == A.STOP
    assert chk(g(), A.TURN_LEFT, Mode.AUTO, yolo=True).action == A.TURN_LEFT
