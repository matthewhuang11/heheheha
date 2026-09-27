"""Exercise the autonomy state machine with fake sensors, no hardware needed.

Run from scoutbot/pi:  ../tools/.venv/Scripts/python ../tools/sim_autonomy.py
"""
import math
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import config

config.DATA_DIR = Path(tempfile.mkdtemp())  # keep the real survivor log untouched
import victims
victims.STORE = config.DATA_DIR / "victims.json"
victims.SNAPS = config.DATA_DIR
config.MISSION_S = 999
config.LISTEN_S = 1

import voice
voice.say = lambda text: True                      # no speaker on the laptop
voice.record = lambda name, s: (time.sleep(s), None)[1]

from autonomy import Autonomy
from motors import Drive


class FakeSonars:
    sim = False  # behave like real hardware

    def __init__(self):
        self.dist = {"left": 1.0, "right": 3.0}  # angled ~30 deg each side of forward

    def get(self, n):
        return self.dist.get(n)


class FakeDetector:
    detections = []


class FakeCamera:
    def latest(self):
        return None, 0


class FakeSenses:
    class sound:
        loud = False
        @classmethod
        def heard_within(cls, s):
            return cls.loud

    class buzzer:
        @staticmethod
        def beep(*a, **k):
            pass

    def snapshot(self):
        return {"temp_c": 24.0, "humidity": 50.0, "hot": False, "heard_sound": False}


log_lines = []
drive, son, det = Drive(), FakeSonars(), FakeDetector()
auto = Autonomy(drive, son, det, FakeCamera(), victims.VictimLog(), lambda m: log_lines.append(m), FakeSenses())


def wait_for(state, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if auto.state == state:
            return True
        time.sleep(0.05)
    raise AssertionError(f"expected {state}, stuck in {auto.state}")


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        sys.exit(1)


auto.start()
check("mission starts in explore", auto.state == "explore")
time.sleep(0.3)
check("explore drives forward", drive.cmd[0] > 0 and drive.cmd[0] == drive.cmd[1])

son.dist["left"] = 0.2  # obstacle ahead-left
wait_for("avoid")
time.sleep(0.2)
l, r = drive.cmd
check("left sonar blocked: turns toward the open side (right)", l > 0 > r)
son.dist["left"] = 1.5
wait_for("explore")
check("clears and resumes exploring", True)

son.dist = {"left": 3.0, "right": 0.2}  # obstacle ahead-right
wait_for("avoid")
time.sleep(0.2)
l, r = drive.cmd
check("right sonar blocked: turns left", l < 0 < r)
son.dist = {"left": 1.0, "right": 3.0}
wait_for("explore")

# only the right sensor alive, and it's blocked: turn left instead
son.dist = {"left": None, "right": 0.3}
wait_for("avoid")
time.sleep(0.2)
l, r = drive.cmd
check("one sensor alive, blocked: turns the other way (left)", l < 0 < r)
son.dist = {"left": 1.0, "right": 3.0}
wait_for("explore")

# a knock with nobody in view: stop and turn to look
FakeSenses.sound.loud = True
wait_for("scan")
FakeSenses.sound.loud = False
time.sleep(0.2)
check("hears a sound: turns in place to look", drive.cmd[0] > 0 > drive.cmd[1])

det.detections = [{"conf": 0.8, "dist_m": 2.5, "bearing_deg": 10.0, "box": [0, 0, 1, 1]}]
wait_for("approach")
time.sleep(0.3)
check("approach steers toward the person", drive.cmd[0] > drive.cmd[1] and drive.cmd[1] > 0 or drive.cmd[0] > drive.cmd[1])
det.detections = [{"conf": 0.8, "dist_m": 0.9, "bearing_deg": 3.0, "box": [0, 0, 1, 1]}]
wait_for("contact")
check("stops to talk when close and centered", drive.cmd == (0.0, 0.0))
wait_for("turn_away", timeout=4)
det.detections = []  # turning away takes them out of frame
vs = auto.log.all()
check("survivor saved and marked contacted", len(vs) == 1 and vs[0]["contacted"])
wait_for("explore", timeout=3)

# the same survivor comes back into view from the robot's new heading
p, v = drive.pose(), vs[0]
dx, dy = v["x"] - p["x"], v["y"] - p["y"]
bearing = (math.degrees(math.atan2(dx, dy)) - p["heading"] + 180) % 360 - 180
det.detections = [{"conf": 0.8, "dist_m": math.hypot(dx, dy), "bearing_deg": bearing, "box": [0, 0, 1, 1]}]
time.sleep(0.6)
check("doesn't re-approach the same survivor", auto.state == "explore")

det.detections = []
time.sleep(2.5)
p = drive.pose()
check(f"moved away from entry ({p['x']:.2f}, {p['y']:.2f})", math.hypot(p["x"], p["y"]) > 0.3)
son.dist["left"] = None  # one sensor unplugged mid-mission: keep going on the other
time.sleep(0.9)
check("keeps exploring on one working sensor", auto.state == "explore")
son.dist["right"] = None  # both gone
time.sleep(0.9)
check("holds still when every sensor dies", auto.state == "blind" and drive.cmd == (0.0, 0.0))
son.dist = {"left": 1.0, "right": 3.0}
wait_for("explore")
check("resumes when the sensors come back", True)

auto.go_home()
wait_for("done", timeout=30)
p = drive.pose()
check(f"retraced back to entry ({p['x']:.2f}, {p['y']:.2f}, {p['heading']:.0f} deg)", math.hypot(p["x"], p["y"]) < 0.15)

print("\n".join("  event: " + m for m in log_lines))
