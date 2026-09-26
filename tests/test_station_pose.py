"""KI-22: the pose uses a per-action speed calibration, interpolated during ramps; the sim uses the same one."""
import pytest
from scoutbot import settings
from scoutbot.survivors.pose import Calibration, DeadReckoning

def cfg_with(**motion):
    c = settings.load("base", load_env=False); c["motion"].update(motion); return c

def test_each_action_uses_its_own_measured_speed():
    cal = Calibration(cfg_with(forward_cm_s=30, slow_cm_s=20, backup_cm_s=12, turn_deg_s=90))
    assert cal.motion(0.6, 0.6)[0] == pytest.approx(30)          # FORWARD
    assert cal.motion(0.35, 0.35)[0] == pytest.approx(20)        # FORWARD_SLOW: measured, not 30 * 0.35/0.6 = 17.5
    assert cal.motion(-0.35, -0.35)[0] == pytest.approx(-12)     # BACK_UP
    v, w = cal.motion(-0.45, 0.45); assert v == 0 and w == pytest.approx(90)   # TURN_LEFT in place
    assert cal.motion(0.0, 0.0) == (0.0, 0.0)
    assert 0 < cal.motion(0.2, 0.2)[0] < 20                      # ramping up: interpolated

def test_pose_moves_the_measured_distance():
    dr = DeadReckoning(cfg_with(slow_cm_s=20))
    for i in range(11): p = dr.update((0.35, 0.35), i * 0.1)        # 1 s at 10 Hz
    assert p.x_cm == pytest.approx(20, abs=0.1) and p.y_cm == pytest.approx(0, abs=0.1)

def test_sim_world_matches_pose_calibration():
    from scoutbot.hw.simworld import World
    c = cfg_with(slow_cm_s=20); c["sim"]["noise"] = 0.0
    w = World(c, "room_basic", seed=1); x0 = w.x
    w.h = 0.0 if w.raycast(0, people=False) > 50 else 180.0
    w.set_wheels(0.35, 0.35); w.step(0.5)
    assert abs(w.x - x0) == pytest.approx(10, abs=0.2)
