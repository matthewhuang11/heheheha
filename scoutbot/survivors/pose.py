"""Dead-reckoning pose estimate (spec 9.1): integrate the wheel outputs actually sent to the motors, using the measured
calibration speeds. With no wheel encoders this drifts ~30% of distance travelled, so uncertainty grows with distance and
the dashboard draws it as a circle. An IMU/encoder estimator can replace this later behind the same update()/pose()."""
from __future__ import annotations
import math, threading
from scoutbot.types import Pose

class DeadReckoning:
    def __init__(self, cfg: dict, start: Pose | None = None, base_uncertainty: float = 30.0, drift: float = 0.3):
        m = cfg["motion"]; self.k = m["forward_cm_s"] / max(cfg["speeds"]["FORWARD"][0], 1e-6)
        self.turn_frac = max(abs(cfg["speeds"]["TURN_LEFT"][1]), 1e-6); self.turn_deg_s = m["turn_deg_s"]
        s = start or Pose(); self.x, self.y, self.h = s.x_cm, s.y_cm, s.heading_deg
        self.base = base_uncertainty; self.drift = drift; self.odometer = 0.0; self.t = None; self.lock = threading.Lock()
    def update(self, wheels: tuple[float, float], now: float) -> Pose:
        with self.lock:
            dt = 0.0 if self.t is None else min(0.5, max(0.0, now - self.t)); self.t = now
            l, r = wheels; v = (l + r) / 2 * self.k; w = (r - l) / 2 / self.turn_frac * self.turn_deg_s
            self.h = (self.h + w * dt) % 360
            self.x += v * dt * math.cos(math.radians(self.h)); self.y += v * dt * math.sin(math.radians(self.h))
            self.odometer += abs(v * dt)
            return self._pose()
    def _pose(self) -> Pose:
        return Pose(x_cm=round(self.x, 1), y_cm=round(self.y, 1), heading_deg=round(self.h, 1),
                    uncertainty_cm=round(self.base + self.drift * self.odometer, 1), source="dead_reckoning")
    def pose(self) -> Pose:
        with self.lock: return self._pose()
