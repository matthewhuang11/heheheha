"""A tiny 2D simulated room (spec 4.2): walls, boxes, survivors, and a robot that moves when the fake motors drive it.
The fake distance sensors are raycasts, so they react to the fake driving, and the map / survivor positions can be tested
end to end on the Mac. Units: cm and degrees. Heading 0 = +x, counter-clockwise positive. Left sensor = +30 deg."""
from __future__ import annotations
import math, random, threading, time
from pathlib import Path
import yaml
from robot.types import SceneReport, Sensors
from scoutbot.types import PersonDetection, Pose

ROBOT_R = 12.0          # robot radius for collisions
PERSON_R = 20.0
SENSOR_ANGLES = (30.0, 0.0, -30.0)     # left, center, right
BEAM_HALF = 7.5
CAM_HALF_FOV = 30.0
CAM_RANGE = 450.0
MAX_ECHO = 400.0

def _ray_seg(ox, oy, dx, dy, x1, y1, x2, y2):
    ex, ey = x2 - x1, y2 - y1
    den = dx * ey - dy * ex
    if abs(den) < 1e-9: return None
    t = ((x1 - ox) * ey - (y1 - oy) * ex) / den
    u = ((x1 - ox) * dy - (y1 - oy) * dx) / den
    return t if t >= 0 and 0 <= u <= 1 else None

def _ray_circle(ox, oy, dx, dy, cx, cy, r):
    fx, fy = ox - cx, oy - cy
    b = fx * dx + fy * dy; c = fx * fx + fy * fy - r * r; disc = b * b - c
    if disc < 0: return None
    t = -b - math.sqrt(disc)
    return t if t >= 0 else None

def _point_seg_dist(px, py, x1, y1, x2, y2):
    ex, ey = x2 - x1, y2 - y1; L = ex * ex + ey * ey
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * ex + (py - y1) * ey) / L))
    return math.hypot(px - (x1 + t * ex), py - (y1 + t * ey))

class World:
    def __init__(self, cfg: dict, name: str | None = None, seed: int | None = None):
        name = name or cfg["sim"]["world"]
        p = Path(__file__).resolve().parents[2] / "config" / "worlds" / f"{name}.yaml"
        w = yaml.safe_load(p.read_text(encoding="utf-8")); self.name = name
        W, H = w["size"]; self.size = (W, H)
        segs = [(0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)]
        segs += [tuple(s) for s in w.get("walls", [])]
        for x, y, bw, bh in w.get("boxes", []):
            segs += [(x, y, x + bw, y), (x + bw, y, x + bw, y + bh), (x + bw, y + bh, x, y + bh), (x, y + bh, x, y)]
        self.segs = segs; self.boxes = w.get("boxes", []); self.walls = w.get("walls", [])
        self.survivors = [tuple(s) for s in w.get("survivors", [])]
        st = w.get("start", {"x": W / 2, "y": H / 2, "heading": 0})
        self.x, self.y, self.h = float(st["x"]), float(st["y"]), float(st["heading"])
        self.rng = random.Random(seed); self.noise = cfg["sim"].get("noise", 0.05)
        m = cfg["motion"]; self.k = m["forward_cm_s"] / max(cfg["speeds"]["FORWARD"][0], 1e-6)
        self.turn_k = m["turn_deg_s"] / max(abs(cfg["speeds"]["TURN_LEFT"][1]), 1e-6)
        # a fixed per-run wheel mismatch makes dead reckoning drift like a real robot
        self.bias = (1 + self.rng.uniform(-self.noise, self.noise), 1 + self.rng.uniform(-self.noise, self.noise))
        self.wheels = (0.0, 0.0); self.lock = threading.RLock(); self.contacts = 0; self._touching = False
        self._stop = threading.Event(); self.distance_travelled = 0.0

    # ---- motion ----
    def set_wheels(self, l: float, r: float):
        with self.lock: self.wheels = (l, r)
    def step(self, dt: float):
        with self.lock:
            l, r = self.wheels
            vl = l * self.k * self.bias[0]; vr = r * self.k * self.bias[1]
            v = (vl + vr) / 2; w = ((vr - vl) / 2) / self.k * self.turn_k        # deg/s
            if v == 0 and w == 0: self._touching = False; return
            nh = self.h + w * dt
            nx = self.x + v * dt * math.cos(math.radians(nh)); ny = self.y + v * dt * math.sin(math.radians(nh))
            if self._collides(nx, ny):
                if not self._touching: self.contacts += 1
                self._touching = True; self.h = nh            # can still rotate in place
                return
            self._touching = False; self.distance_travelled += abs(v * dt)
            self.x, self.y, self.h = nx, ny, nh % 360
    def _collides(self, x, y):
        if any(_point_seg_dist(x, y, *s) < ROBOT_R for s in self.segs): return True
        return any(math.hypot(x - sx, y - sy) < ROBOT_R + PERSON_R for sx, sy in self.survivors)
    def run(self, hz: float = 50):
        dt = 1.0 / hz; last = time.monotonic()
        while not self._stop.is_set():
            time.sleep(dt); now = time.monotonic(); self.step(now - last); last = now
    def start(self):
        threading.Thread(target=self.run, daemon=True, name="simworld").start(); return self
    def stop(self): self._stop.set()

    # ---- sensing ----
    def raycast(self, rel_deg: float, max_cm: float = 1000.0, people: bool = True) -> float:
        with self.lock: ox, oy, h = self.x, self.y, self.h
        a = math.radians(h + rel_deg); dx, dy = math.cos(a), math.sin(a); best = max_cm
        for s in self.segs:
            t = _ray_seg(ox, oy, dx, dy, *s)
            if t is not None and t < best: best = t
        if people:
            for sx, sy in self.survivors:
                t = _ray_circle(ox, oy, dx, dy, sx, sy, PERSON_R)
                if t is not None and t < best: best = t
        return best
    def sensors(self) -> Sensors:
        vals, ok = [], []
        for ang in SENSOR_ANGLES:
            d = min(self.raycast(ang + o) for o in (-BEAM_HALF, 0, BEAM_HALF))
            d = max(0.0, d - ROBOT_R)                    # sensors sit at the front edge
            if d > MAX_ECHO or self.rng.random() < 0.02: vals.append(0.0); ok.append(False)    # no echo
            else: vals.append(round(max(2.0, d * (1 + self.rng.gauss(0, 0.01))), 1)); ok.append(True)
        return Sensors(left=vals[0], center=vals[1], right=vals[2], valid=tuple(ok), updated_at=time.monotonic())
    def visible_survivors(self) -> list[dict]:
        with self.lock: ox, oy, h = self.x, self.y, self.h
        out = []
        for i, (sx, sy) in enumerate(self.survivors):
            dist = math.hypot(sx - ox, sy - oy); bearing = (math.degrees(math.atan2(sy - oy, sx - ox)) - h + 180) % 360 - 180
            if dist > CAM_RANGE or abs(bearing) > CAM_HALF_FOV: continue
            if self.raycast(bearing, people=False) < dist - PERSON_R: continue      # hidden behind a wall or box
            out.append({"i": i, "x": sx, "y": sy, "dist": dist, "bearing": bearing})
        return sorted(out, key=lambda s: s["dist"])
    def detections(self, now: float) -> list[PersonDetection]:
        dets = []
        for s in self.visible_survivors():
            where = "left" if s["bearing"] > 10 else "right" if s["bearing"] < -10 else "center"
            dist = "near" if s["dist"] < 100 else "mid" if s["dist"] < 250 else "far"
            frac = min(1.0, 12000 / max(s["dist"], 1) / 360)
            cx = 0.5 - s["bearing"] / 60.0
            dets.append(PersonDetection(source="sim", where=where, distance=dist, confidence=0.9,
                                        bbox=(max(0, cx - frac / 4), max(0, 0.5 - frac / 2), min(1, cx + frac / 4), min(1, 0.5 + frac / 2)), at=now))
        return dets
    def scene_report(self) -> SceneReport:
        c = self.raycast(0); l = self.raycast(25); r = self.raycast(-25)
        path = "blocked" if c < 60 else "partially_blocked" if c < 120 else "clear"
        best = max((("left", l), ("center", c), ("right", r)), key=lambda t: t[1])[0] if max(l, c, r) > 80 else "none"
        dets = self.detections(time.monotonic())
        people = ({"visible": True, "where": dets[0].where, "distance": dets[0].distance} if dets
                  else {"visible": False, "where": "none", "distance": "none"})
        return SceneReport(path_ahead=path, best_direction=best, terrain="flat", hazards=[], people=people,
                           objects=["wall"] + (["person"] if dets else []), confidence=0.9, notes=f"simulated scene ({self.name})")
    def pose(self) -> Pose:
        with self.lock: return Pose(x_cm=self.x, y_cm=self.y, heading_deg=self.h, uncertainty_cm=0, source="sim")
    def layout(self) -> dict:
        return {"size": self.size, "walls": self.walls, "boxes": self.boxes, "survivors": self.survivors, "name": self.name}

class SimDistance:
    def __init__(self, world: World): self.world = world
    def read(self) -> Sensors:
        time.sleep(0.06); return self.world.sensors()
    def close(self): pass
