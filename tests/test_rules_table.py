import pytest
from robot.types import Sensors, SceneReport, Action as A
from robot.brain import decide, evaluate, first_match

NOPE = {"visible": False, "where": "none", "distance": "none"}
def scene(**x):
    d = dict(path_ahead="clear", best_direction="none", terrain="flat", hazards=[], people=NOPE, objects=[], confidence=1, notes=""); d.update(x); return SceneReport(**d)
def go(L=200, C=200, R=200, sc="default", valid=(True, True, True), online=True, age=0.0, updated=10.0):
    s = Sensors(left=L, center=C, right=R, valid=valid, vlm_online=online, updated_at=updated)
    sc = scene() if sc == "default" else sc
    a, r, _ = decide(s, sc, 10.0, None if sc is None else 10.0 - age)
    return a, r
fire = {"type": "fire", "where": "center", "distance": "near"}
CASES = [
 (dict(), (A.FORWARD, 8)),
 (dict(updated=0.0), (A.STOP, 1)),
 (dict(valid=(False, False, False)), (A.STOP, 1)),
 (dict(L=30, C=20, R=30), (A.BACK_UP, 2)),
 (dict(L=100, C=20, R=50), (A.TURN_LEFT, 2)),
 (dict(L=50, C=20, R=100), (A.TURN_RIGHT, 2)),
 (dict(L=10, C=100), (A.TURN_RIGHT, 3)),
 (dict(C=100, R=10), (A.TURN_LEFT, 3)),
 (dict(L=10, C=20, R=100), (A.TURN_RIGHT, 2)),                       # rule 2 beats rule 3
 (dict(sc=scene(hazards=[fire])), (A.BACK_UP, 4)),
 (dict(sc=scene(hazards=[{**fire, "type": "smoke", "distance": "mid"}])), (A.BACK_UP, 4)),
 (dict(sc=scene(terrain="stairs_or_drop")), (A.BACK_UP, 4)),
 (dict(sc=scene(hazards=[{**fire, "distance": "far"}])), (A.FORWARD_SLOW, 7)),   # far hazard: slow, not stop
 (dict(sc=scene(hazards=[{**fire, "where": "left"}])), (A.BACK_UP, 4)),        # near hazard on any side
 (dict(sc=scene(people={"visible": True, "where": "center", "distance": "near"})), (A.STOP, 5)),
 (dict(sc=scene(people={"visible": True, "where": "center", "distance": "mid"})), (A.FORWARD_SLOW, 7)),
 (dict(sc=scene(hazards=[fire], people={"visible": True, "where": "center", "distance": "near"})), (A.BACK_UP, 4)),
 (dict(sc=scene(path_ahead="blocked", people={"visible": True, "where": "left", "distance": "near"})), (A.STOP, 5)),
 (dict(sc=scene(path_ahead="blocked", best_direction="left")), (A.TURN_LEFT, 6)),
 (dict(L=80, R=120, sc=scene(path_ahead="blocked")), (A.TURN_RIGHT, 6)),
 (dict(C=50), (A.FORWARD_SLOW, 7)),
 (dict(sc=scene(path_ahead="partially_blocked")), (A.FORWARD_SLOW, 7)),
 (dict(sc=scene(terrain="rubble")), (A.FORWARD_SLOW, 7)),
 (dict(online=False), (A.FORWARD_SLOW, 8)),
 (dict(online=False, sc=scene(hazards=[fire])), (A.FORWARD_SLOW, 8)),   # camera rules ignored when offline
 (dict(age=7.0), (A.FORWARD_SLOW, 8)),                                   # stale camera report
 (dict(C=25), (A.FORWARD_SLOW, 7)),
 (dict(C=60), (A.FORWARD, 8)),
 (dict(L=15), (A.FORWARD_SLOW, 7)),                                       # side 15-30 cm: slow
 (dict(L=35), (A.FORWARD, 8)),
 (dict(valid=(True, False, True)), (A.FORWARD_SLOW, 7)),                 # dead center sensor is never "far"
 (dict(sc=None, C=40), (A.FORWARD_SLOW, 7)),
]
@pytest.mark.parametrize("kw,want", CASES)
def test_case(kw, want): assert go(**kw) == want

def test_trace_matches_decision_and_has_all_rules():
    s = Sensors(left=200, center=18, right=90, updated_at=10.0)
    steps = evaluate(s, scene(), 10.0, 10.0)
    assert [x.rule for x in steps] == list(range(1, 9))
    assert first_match(steps).rule == decide(s, scene(), 10.0, 10.0)[1] == 2
