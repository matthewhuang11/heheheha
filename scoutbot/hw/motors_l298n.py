"""Real motors: L298N dual H-bridge, left pair of TT motors on channel A, right pair on channel B (spec 5.3).
Uses gpiozero (on the Pi: pip install gpiozero lgpio). Pins come from config hw.pins. Wheels off the ground first!"""
from __future__ import annotations
import atexit, threading, time
from robot.types import Action
from scoutbot.hw.base import Ramp, wheel_speeds

class L298NMotors:
    def __init__(self, cfg: dict):
        from gpiozero import Motor        # imported here so the Mac never needs gpiozero
        p = cfg["hw"]["pins"]; self.cfg = cfg
        self.left = Motor(forward=p["left"]["fwd"], backward=p["left"]["back"], enable=p["left"]["en"], pwm=True)
        self.right = Motor(forward=p["right"]["fwd"], backward=p["right"]["back"], enable=p["right"]["en"], pwm=True)
        self.ramp = Ramp(cfg["motion"].get("ramp_s", 0.15)); self.lock = threading.Lock()
        atexit.register(self.stop)
    @staticmethod
    def _out(m, v):
        v = max(-1.0, min(1.0, v))
        if v > 0: m.forward(v)
        elif v < 0: m.backward(-v)
        else: m.stop()
    def apply(self, action: Action) -> None:
        l, r = wheel_speeds(action, self.cfg)
        self.apply_wheels(l, r)
    def apply_wheels(self, left: float, right: float) -> None:
        with self.lock:
            ol, orr = self.ramp.set(max(-1.0, min(1.0, left)), max(-1.0, min(1.0, right)), time.monotonic())
            manual = self.cfg.get("manual", {})
            if ol: ol = (1 if ol > 0 else -1) * max(abs(ol), float(manual.get("min_start", 0.0)))
            if orr: orr = (1 if orr > 0 else -1) * max(abs(orr), float(manual.get("min_start", 0.0)))
            if manual.get("invert_left", False): ol = -ol
            if manual.get("invert_right", False): orr = -orr
            self._out(self.left, ol); self._out(self.right, orr)
    def stop(self) -> None:
        with self.lock:
            self.ramp.zero(time.monotonic())
            try: self.left.stop(); self.right.stop()
            except Exception: pass
    def current(self):
        with self.lock: return tuple(self.ramp.out)
    def close(self):
        self.stop()
        try: self.left.close(); self.right.close()
        except Exception: pass
