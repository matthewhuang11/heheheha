"""Fake distance sensors for testing on the Mac: dashboard sliders, random readings (reuses robot/sim.py), or a script."""
from __future__ import annotations
import bisect, random, time
from robot.sim import random_sensors
from robot.types import Sensors

class SliderDistance:
    """Values come from the dashboard sliders (shared.slider_values / slider_valid)."""
    def __init__(self, shared): self.shared = shared
    def read(self) -> Sensors:
        time.sleep(0.06)
        with self.shared.lock:
            v = list(self.shared.slider_values); ok = tuple(self.shared.slider_valid)
        return Sensors(left=v[0], center=v[1], right=v[2], valid=ok, updated_at=time.monotonic())
    def close(self): pass

class RandomDistance:
    """New random scenario every `every_s` seconds (same generator as robot/sim.py), small jitter in between."""
    def __init__(self, every_s: float = 1.0, seed: int | None = None):
        self.rng = random.Random(seed); self.every = every_s; self.cur = random_sensors(self.rng); self.t = 0.0
    def read(self) -> Sensors:
        time.sleep(0.06); now = time.monotonic()
        if now - self.t >= self.every: self.cur = random_sensors(self.rng); self.t = now
        j = lambda v: None if v is None else max(2.0, v + self.rng.uniform(-2, 2))
        return Sensors(left=j(self.cur.left), center=j(self.cur.center), right=j(self.cur.right), valid=self.cur.valid, updated_at=now)
    def close(self): pass

class ScriptedDistance:
    """Plays a list of steps from config: [{for_s: 2, lcr: [200, 40, 200]}, {for_s: 1, lcr: [200, null, 200]}], looping."""
    def __init__(self, script: list[dict]):
        self.script = script or [{"for_s": 3, "lcr": [200, 200, 200]}, {"for_s": 2, "lcr": [200, 20, 200]}]; self.t0 = time.monotonic()
    def read(self) -> Sensors:
        time.sleep(0.06); now = time.monotonic(); total = sum(s["for_s"] for s in self.script)
        t = (now - self.t0) % total
        for s in self.script:
            if t < s["for_s"]: break
            t -= s["for_s"]
        l, c, r = s["lcr"]
        return Sensors(left=l if l is not None else 0, center=c if c is not None else 0, right=r if r is not None else 0,
                       valid=(l is not None, c is not None, r is not None), updated_at=now)
    def close(self): pass

class ReplayDistance:
    """Plays back sensors.jsonl written by --record (C15), in real time, looping. Use it with the folder camera:
    --set hw.camera=folder --set hw.camera_folder=data/recordings/<time> --set hw.distance=replay --set hw.replay=data/recordings/<time>"""
    def __init__(self, path: str):
        import json
        from pathlib import Path
        p = Path(path); p = p / "sensors.jsonl" if p.is_dir() else p
        self.rows = []
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                try: self.rows.append(json.loads(line))
                except ValueError: continue
        if not self.rows: print(f"[distance] replay: no sensor lines in {p}", flush=True)
        self.t_first = self.rows[0]["t"] if self.rows else 0.0; self.span = (self.rows[-1]["t"] - self.t_first + 0.1) if self.rows else 1.0
        self.times = [r["t"] for r in self.rows]; self.t0 = time.monotonic(); self.i = 0
    def read(self) -> Sensors:
        time.sleep(0.06); now = time.monotonic()
        if not self.rows: return Sensors(left=0, center=0, right=0, valid=(False, False, False), updated_at=now)
        t = self.t_first + (now - self.t0) % self.span
        self.i = max(0, bisect.bisect_right(self.times, t) - 1)      # newest recorded line at or before t
        r = self.rows[self.i]; v = r["raw"]; ok = r["valid"]
        return Sensors(left=v[0] or 0, center=v[1] or 0, right=v[2] or 0, valid=tuple(ok), updated_at=now)
    def close(self): pass
