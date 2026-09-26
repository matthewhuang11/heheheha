import numpy as np
from robot.types import Sensors, SceneReport, Action as A
from robot.brain import decide, Context
from robot.config import Policy
from robot.sensing import SensorFilter
from robot.scene_filter import SceneFilter
from robot.camera_health import CameraHealth
from robot.controller import Controller
from robot.metrics import Metrics

NOPE = {"visible": False, "where": "none", "distance": "none"}
def scene(**x):
    d = dict(path_ahead="clear", best_direction="none", terrain="flat", hazards=[], people=NOPE, objects=[], confidence=1, notes=""); d.update(x); return SceneReport(**d)
fire = {"type": "fire", "where": "center", "distance": "near"}

def test_policy_derivation():
    p = Policy.from_speed(); assert p.stop_cm == 25 and p.slow_cm == 60
    assert Policy.from_speed(v_cm_s=60).stop_cm > 50          # faster robot -> longer stop distance

def test_median_kills_single_glitch():
    f = SensorFilter()
    for i, v in enumerate([100, 100, 5, 100, 100]): out = f.push(v, i * .1)
    assert out == 100

def test_one_dropped_ping_is_not_no_echo_but_three_are():
    f = SensorFilter()
    for i, v in enumerate([100, 100, 100, None, 100]): out = f.push(v, i * .1)
    assert out == 100
    for i, v in enumerate([None, None, None]): out = f.push(v, 1 + i * .1)
    assert out is None

def test_out_of_range_rejected():
    f = SensorFilter()
    for i in range(5): out = f.push(450, i * .1)
    assert out is None

def test_ttc():
    f = SensorFilter()
    for i, v in enumerate([200, 190, 180, 170, 160, 150, 140, 130]): f.push(v, i * .1)
    assert 1 < f.ttc(0.7) < 2      # ~100 cm/s closing, 130 cm away

def test_ctx_ttc_and_cliff_and_latch():
    s = Sensors(left=200, center=80, right=200, updated_at=10)
    assert decide(s, None, 10, None, Context(ttc=0.5))[:2] == (A.TURN_LEFT, 2)
    assert decide(s, None, 10, None, Context(cliff=40))[:2] == (A.BACK_UP, 2)
    s2 = Sensors(left=200, center=28, right=200, updated_at=10)
    assert decide(s2, None, 10)[1] == 7 and decide(s2, None, 10, None, Context(latched=frozenset({"center"})))[1] == 2

def test_camera_unhealthy_is_like_missing():
    assert decide(Sensors(updated_at=10), scene(), 10, 10, Context(camera_healthy=False))[:2] == (A.FORWARD_SLOW, 8)

def test_camera_unsure_or_unknown_slows():
    assert decide(Sensors(updated_at=10), scene(confidence=.2), 10, 10)[:2] == (A.FORWARD_SLOW, 7)
    assert decide(Sensors(updated_at=10), scene(path_ahead="unknown"), 10, 10)[:2] == (A.FORWARD_SLOW, 7)
    assert decide(Sensors(updated_at=10), scene(terrain="water"), 10, 10)[:2] == (A.FORWARD_SLOW, 7)

def test_scene_filter_fire_is_remembered_but_clear_needs_two():
    f = SceneFilter(); f.push(scene(hazards=[fire], path_ahead="blocked"), 0.0)
    f.push(scene(), 2.0)
    cur = f.current(2.0); assert any(h.type == "fire" for h in cur.hazards) and cur.path_ahead == "blocked"   # fire held 4s, blocked persists 1 more report
    f.push(scene(), 4.0); cur = f.current(6.5)
    assert not cur.hazards and cur.path_ahead == "clear"

def test_scene_filter_minor_hazard_needs_two_of_three():
    f = SceneFilter(); glass = {"type": "glass", "where": "center", "distance": "near"}
    f.push(scene(), 0); f.push(scene(hazards=[glass]), 2); f.push(scene(), 4)
    assert f.current(4).hazards == []
    f.push(scene(hazards=[glass]), 6); f.push(scene(hazards=[glass]), 8)
    assert len(f.current(8).hazards) == 1

def test_camera_health():
    h = CameraHealth(); black = np.zeros((120, 160, 3), np.uint8)
    assert not h.update(black, 0)["healthy"]
    rng = np.random.default_rng(0)
    good = lambda: rng.integers(60, 200, (120, 160, 3), dtype=np.uint8)
    assert h.update(good(), 1)["healthy"]
    g = good(); h.update(g, 2); r = h.update(g, 5); assert r["frozen"] and not r["healthy"]

def raw(L=200, C=200, R=200, t=0.0): return Sensors(left=L, center=C, right=R, updated_at=t)
def run(c, seq, sc=None):
    out = []
    for i, (L, C, R) in enumerate(seq):
        t = i * .1; out.append(c.step(raw(L, C, R, t), sc, t if sc else None, True, t))
    return out

def test_controller_filters_glitch_and_stops_on_real_obstacle():
    c = Controller(); d = run(c, [(200, 200, 200)] * 5 + [(200, 5, 200)] + [(200, 200, 200)] * 3)
    assert all(x.action in (A.FORWARD, A.FORWARD_SLOW) for x in d)      # single 5 cm glitch ignored
    c = Controller(); d = run(c, [(200, 200, 200)] * 5 + [(200, 10, 200)] * 4)
    assert d[-1].action in (A.TURN_LEFT, A.TURN_RIGHT) and d[-1].rule == 2

def test_hysteresis_keeps_avoiding_until_clear():
    c = Controller(); d = run(c, [(200, 200, 200)] * 5 + [(200, 20, 200)] * 5 + [(200, 28, 200)] * 5)
    assert d[-1].rule == 2                        # 28 cm still "near" once latched (leave at 33)
    d = run(c, [(200, 40, 200)] * 6); assert d[-1].rule != 2

def test_turn_hold_prevents_flicker():
    c = Controller()
    for i in range(5): d = c.step(raw(10, 200, 100, i * .05), None, None, True, i * .05)
    assert d.action == A.TURN_RIGHT
    held = []
    for i in range(3):
        t = 0.25 + i * .05; held.append(c.step(raw(200, 200, 100, t), None, None, True, t))
    assert held[-1].action == A.TURN_RIGHT and any("holding" in n for n in held[-1].notes)
    t = 1.5; assert c.step(raw(200, 200, 100, t), None, None, True, t).action == A.FORWARD_SLOW   # hold expired

def test_stuck_recovery_then_stop():
    c = Controller(); t = 0.0
    for k in range(12):
        for C in ([10] * 8 + [200] * 8):
            c.step(raw(100, C, 100, t), None, None, True, t); t += .1
    assert c.events["flips"] >= 1 and c.events["stuck"] >= 1

def test_metrics_disagreement_and_near_miss():
    m = Metrics(); c = Controller(); sc = scene(hazards=[fire]); t = 0.0
    for i in range(8):
        d = c.step(raw(200, 200, 200, t), sc, 0.0 + 0, True, t); m.tick(t, t, (200, 200, 200), d, True, True); t += .1
    assert m.disagree["hazard seen, sensors far"] == 1

def test_temperature_correction():
    from robot.sensing import echo_to_cm
    assert abs(echo_to_cm(0.0058, 20) - 99.5) < 1 and echo_to_cm(0.0058, 35) > echo_to_cm(0.0058, 20)
