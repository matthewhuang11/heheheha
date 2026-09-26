"""The three hardware interfaces (spec section 5). If the hardware team's code implements these, it plugs in with no
other changes. Every implementation is picked by name in the config (hw.camera / hw.distance / hw.motors)."""
from __future__ import annotations
from typing import Protocol
import numpy as np
from robot.types import Action, Sensors

class Camera(Protocol):
    def read(self) -> np.ndarray | None: ...      # newest BGR frame, or None if nothing new / failed
    def close(self) -> None: ...

class DistanceSensors(Protocol):
    def read(self) -> Sensors: ...                # raw left/center/right cm, valid flags, updated_at (monotonic)
    def close(self) -> None: ...

class Motors(Protocol):
    def apply(self, action: Action) -> None: ...  # called >= 10 Hz by the control loop; each call feeds the dead-man
    def stop(self) -> None: ...                   # immediate, idempotent, safe from any thread
    def current(self) -> tuple[float, float]: ... # wheel fractions actually being output now (after ramp)
    def close(self) -> None: ...

class Ramp:
    """Moves wheel outputs toward targets over ramp_s so the robot does not jerk or tip. Stop is always instant."""
    def __init__(self, ramp_s: float = 0.15):
        self.ramp_s = max(ramp_s, 1e-3); self.out = [0.0, 0.0]; self.target = [0.0, 0.0]; self.t = None
    def set(self, left: float, right: float, now: float) -> tuple[float, float]:
        self.target = [left, right]
        if left == 0 and right == 0: self.out = [0.0, 0.0]; self.t = now; return tuple(self.out)
        dt = 0.0 if self.t is None else max(0.0, now - self.t); self.t = now
        step = dt / self.ramp_s
        for i in range(2):
            d = self.target[i] - self.out[i]
            # reversing direction passes through zero first
            if self.out[i] * self.target[i] < 0: d = -self.out[i]
            self.out[i] += max(-step, min(step, d))
        return tuple(self.out)
    def zero(self, now: float):
        self.out = [0.0, 0.0]; self.target = [0.0, 0.0]; self.t = now

def wheel_speeds(action: Action | str, cfg: dict) -> tuple[float, float]:
    name = action.value if isinstance(action, Action) else str(action)
    l, r = cfg["speeds"].get(name, [0, 0])
    return float(l) * cfg["motion"].get("trim_left", 1.0), float(r) * cfg["motion"].get("trim_right", 1.0)

def build(cfg: dict, shared, world=None):
    """Create (camera, distance, motors) from the config."""
    hw = cfg["hw"]
    cam_kind = hw["camera"]
    if cam_kind == "opencv":
        from scoutbot.hw.camera_opencv import open_best_camera
        camera = open_best_camera(hw["camera_index"])
        if not camera.ok and world is not None:           # no webcam: fall back to a synthetic view in the sim
            from scoutbot.hw.camera_opencv import SyntheticCamera
            camera = SyntheticCamera(world)
    elif cam_kind == "folder":
        from scoutbot.hw.camera_opencv import FolderCamera
        camera = FolderCamera(hw["camera_folder"], hw.get("camera_fps", 10))
    elif cam_kind == "synthetic":
        from scoutbot.hw.camera_opencv import SyntheticCamera
        camera = SyntheticCamera(world)
    else: raise SystemExit(f"unknown hw.camera '{cam_kind}'")

    d = hw["distance"]
    if d == "sliders":
        from scoutbot.hw.distance_fake import SliderDistance; distance = SliderDistance(shared)
    elif d == "random":
        from scoutbot.hw.distance_fake import RandomDistance; distance = RandomDistance(hw.get("random_every_s", 1.0))
    elif d == "scripted":
        from scoutbot.hw.distance_fake import ScriptedDistance; distance = ScriptedDistance(hw.get("script", []))
    elif d == "simworld":
        if world is None: raise SystemExit("hw.distance=simworld needs the sim world (use --profile sim)")
        from scoutbot.hw.simworld import SimDistance; distance = SimDistance(world)
    elif d == "hcsr04":
        from scoutbot.hw.distance_hcsr04 import HCSR04Array; distance = HCSR04Array(hw["pins"]["trig"], hw["pins"]["echo"])
    elif d == "tof":
        from scoutbot.hw.distance_tof import ToFArray; distance = ToFArray(hw["tof_xshut"])
    else: raise SystemExit(f"unknown hw.distance '{d}'")

    m = hw["motors"]
    if m == "fake":
        from scoutbot.hw.motors_fake import FakeMotors; motors = FakeMotors(cfg, world)
    elif m == "l298n":
        from scoutbot.hw.motors_l298n import L298NMotors; motors = L298NMotors(cfg)
    else: raise SystemExit(f"unknown hw.motors '{m}'")
    return camera, distance, motors
