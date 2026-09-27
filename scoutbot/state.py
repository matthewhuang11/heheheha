"""Thread-safe latest-value store shared by every worker, plus a tiny event bus.
Workers never call each other: they write facts here and read facts from here (spec 3.3)."""
from __future__ import annotations
import itertools, queue, threading, time
from collections import deque
from robot.types import Sensors
from scoutbot.types import Mode, Pose

class Shared:
    def __init__(self):
        self.lock = threading.RLock()
        # camera
        self.frame = None; self.jpeg = None; self.frame_at = None; self.frame_seq = 0
        self.cam_health = {"healthy": False, "reasons": ["no frame yet"]}
        self.capture_fps = 0.0
        # distance sensors (raw, from the driver)
        self.raw_sensors = Sensors(updated_at=0)
        self.slider_values = [200.0, 200.0, 200.0]; self.slider_valid = [True, True, True]
        # scene (Gemini / fake / sim)
        self.scene = None; self.scene_at = None; self.vlm_failures = 0; self.vlm_latency = None; self.vlm_error = ""; self.vlm_calls = 0
        # person detections (confirmed only)
        self.detections = []; self.det_at = None; self.det_status = "starting"; self.det_fps = None
        # modes / commands
        self.mode = Mode.STOPPED; self.mode_reason = "boot: press Start"
        self.drive_cmd = None
        self.manual_neutral_seen = False; self.manual_last_seq = -1
        self.manual_wheels = (0.0, 0.0); self.manual_veto = None
        self.link_at = None
        # decision
        self.decision = {"action": "STOP", "rule": 0, "reason": "starting", "notes": []}
        self.final_action = "STOP"; self.veto = None
        self.filtered = [None, None, None]
        # pose / map
        self.pose = Pose(); self.true_pose = None; self.sim_contacts = 0
        # network + services
        self.internet = True; self.force_offline = False
        self.services = {"gemini": "unknown", "ollama": "unknown", "yolo": "unknown", "voice": "unknown"}
        self.sync_status = {}
        # timers for the dashboard
        self.last_motor_apply = None; self.watchdog_trips = 0
        self.started = time.monotonic()

    def online(self) -> bool:
        with self.lock: return self.internet and not self.force_offline

class Bus:
    """Publish/subscribe for events the dashboard or other workers need (chat, survivors, logs)."""
    def __init__(self, history: int = 200):
        self._subs: list[queue.Queue] = []; self._lock = threading.Lock()
        self._seq = itertools.count(1); self.recent = deque(maxlen=history)
    def publish(self, topic: str, payload) -> None:
        ev = {"seq": next(self._seq), "topic": topic, "payload": payload, "t": time.time()}
        with self._lock:
            self.recent.append(ev)
            for q in list(self._subs):
                try: q.put_nowait(ev)
                except queue.Full: pass
    def subscribe(self, maxsize: int = 500) -> queue.Queue:
        q = queue.Queue(maxsize=maxsize)
        with self._lock: self._subs.append(q)
        return q
    def unsubscribe(self, q) -> None:
        with self._lock:
            if q in self._subs: self._subs.remove(q)
