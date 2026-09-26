"""Rough map (spec 9.3): breadcrumb trail, obstacle dots from distance readings, survivor pins (drawn by the dashboard).
It is a sketch, not a real map, and the dashboard labels it 'approximate'."""
from __future__ import annotations
import math, threading
from collections import deque
from scoutbot.types import Pose

SENSOR_ANGLES = (30.0, 0.0, -30.0)

class MapBuilder:
    def __init__(self, crumb_cm: float = 20.0, max_obstacles: int = 2000, max_trail: int = 3000, sensor_angles=SENSOR_ANGLES):
        self.trail = deque(maxlen=max_trail); self.obstacles = deque(maxlen=max_obstacles); self.crumb = crumb_cm
        self.angles = tuple(float(a) for a in sensor_angles)
        self.true_trail = deque(maxlen=max_trail); self.lock = threading.Lock(); self._tick = 0
    def update(self, pose: Pose, lcr: tuple, true_pose: Pose | None = None):
        with self.lock:
            if not self.trail or math.hypot(pose.x_cm - self.trail[-1][0], pose.y_cm - self.trail[-1][1]) >= self.crumb:
                self.trail.append((round(pose.x_cm, 1), round(pose.y_cm, 1)))
            if true_pose is not None and (not self.true_trail or math.hypot(true_pose.x_cm - self.true_trail[-1][0], true_pose.y_cm - self.true_trail[-1][1]) >= self.crumb):
                self.true_trail.append((round(true_pose.x_cm, 1), round(true_pose.y_cm, 1)))
            self._tick += 1
            if self._tick % 3: return                      # obstacle dots at ~3 Hz is plenty
            for ang, d in zip(self.angles, lcr):
                if d is None or d > 300: continue
                a = math.radians(pose.heading_deg + ang); r = d + 12
                self.obstacles.append((round(pose.x_cm + r * math.cos(a), 1), round(pose.y_cm + r * math.sin(a), 1)))
    def snapshot(self) -> dict:
        with self.lock: return {"trail": list(self.trail), "obstacles": list(self.obstacles), "true_trail": list(self.true_trail)}
