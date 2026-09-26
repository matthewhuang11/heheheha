"""Dead-reckoning pose estimate (spec 9.1): integrate the wheel outputs actually sent to the motors, using the measured
calibration speeds. With no wheel encoders this drifts ~30% of distance travelled, so uncertainty grows with distance and
the dashboard draws it as a circle. An IMU/encoder estimator can replace this later behind the same update()/pose().

KI-22: speed is a per-action calibration, not one factor. Measured points (motion.* in config, A owns the numbers):
FORWARD_SLOW wheel fraction -> slow_cm_s, FORWARD fraction -> forward_cm_s, BACK_UP fraction -> backup_cm_s, and
turn_deg_s for the TURN fraction. Between points (e.g. while the ramp speeds up) the speed is interpolated linearly."""
from __future__ import annotations
import math, threading
from scoutbot.types import Pose

class Calibration:
    """wheel fraction (-1..1) -> linear speed in cm/s, and turn fraction -> deg/s. Shared by the pose and the sim world."""
    def __init__(self, cfg: dict):
        m, sp = cfg["motion"], cfg["speeds"]
        fwd = (abs(sp["FORWARD"][0]), m["forward_cm_s"]); slow = (abs(sp["FORWARD_SLOW"][0]), m.get("slow_cm_s", m["forward_cm_s"]))
        back = (abs(sp["BACK_UP"][0]), m.get("backup_cm_s", m["forward_cm_s"]))
        self.fwd_pts = sorted({(0.0, 0.0), slow, fwd})
        self.back_pts = [(0.0, 0.0), back]
        self.turn_frac = max(abs(sp["TURN_LEFT"][1]), 1e-6); self.turn_deg_s = m["turn_deg_s"]
    @staticmethod
    def _interp(pts, x):
        """Piecewise linear through pts (sorted, starting at (0, 0)); past the last point, extend the last segment."""
        for i in range(1, len(pts)):
            (x0, y0), (x1, y1) = pts[i - 1], pts[i]
            if x <= x1 or i == len(pts) - 1:
                return y1 if x1 <= x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return 0.0
    def speed(self, frac: float) -> float:
        """cm/s for one wheel at this output fraction (negative = backwards)."""
        if frac >= 0: return self._interp(self.fwd_pts, frac)
        return -self._interp(self.back_pts, -frac)
    def motion(self, left: float, right: float) -> tuple[float, float]:
        """(forward cm/s, turn deg/s CCW) for these wheel outputs. The forward part uses the mean wheel fraction, so an
        in-place turn (equal and opposite wheels) never drifts forward or back."""
        return self.speed((left + right) / 2), (right - left) / 2 / self.turn_frac * self.turn_deg_s

class DeadReckoning:
    def __init__(self, cfg: dict, start: Pose | None = None, base_uncertainty: float = 30.0, drift: float = 0.3):
        self.cal = Calibration(cfg)
        s = start or Pose(); self.x, self.y, self.h = s.x_cm, s.y_cm, s.heading_deg
        self.base = base_uncertainty; self.drift = drift; self.odometer = 0.0; self.t = None; self.lock = threading.Lock()
    def update(self, wheels: tuple[float, float], now: float) -> Pose:
        with self.lock:
            dt = 0.0 if self.t is None else min(0.5, max(0.0, now - self.t)); self.t = now
            v, w = self.cal.motion(*wheels)
            self.h = (self.h + w * dt) % 360
            self.x += v * dt * math.cos(math.radians(self.h)); self.y += v * dt * math.sin(math.radians(self.h))
            self.odometer += abs(v * dt)
            return self._pose()
    def _pose(self) -> Pose:
        return Pose(x_cm=round(self.x, 1), y_cm=round(self.y, 1), heading_deg=round(self.h, 1),
                    uncertainty_cm=round(self.base + self.drift * self.odometer, 1), source="dead_reckoning")
    def pose(self) -> Pose:
        with self.lock: return self._pose()
