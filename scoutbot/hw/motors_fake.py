"""Fake motors: print what the wheels would do, and drive the simulated robot when the sim world is on."""
from __future__ import annotations
import threading, time
from robot.types import Action
from scoutbot.hw.base import Ramp, wheel_speeds

class FakeMotors:
    def __init__(self, cfg: dict, world=None, quiet: bool = False):
        self.cfg = cfg; self.world = world; self.ramp = Ramp(cfg["motion"].get("ramp_s", 0.15))
        self.lock = threading.Lock(); self._last_print = 0.0; self._last_text = ""; self.quiet = quiet
        self.last_apply = None
    def apply(self, action: Action) -> None:
        l, r = wheel_speeds(action, self.cfg)
        self.apply_wheels(l, r, label=action.value if hasattr(action, "value") else str(action))
    def apply_wheels(self, left: float, right: float, label: str = "WHEELS") -> None:
        now = time.monotonic()
        with self.lock:
            out = self.ramp.set(max(-1.0, min(1.0, left)), max(-1.0, min(1.0, right)), now); self.last_apply = now
            if self.world is not None: self.world.set_wheels(*out)
        text = f"LEFT {out[0]:+.2f} RIGHT {out[1]:+.2f}  ({label})"
        if not self.quiet and (text != self._last_text and now - self._last_print > 1.0):
            print("[motors]", text, flush=True); self._last_print = now; self._last_text = text
    def stop(self) -> None:
        with self.lock:
            self.ramp.zero(time.monotonic())
            if self.world is not None: self.world.set_wheels(0.0, 0.0)
    def current(self) -> tuple[float, float]:
        with self.lock: return tuple(self.ramp.out)
    def close(self): self.stop()
