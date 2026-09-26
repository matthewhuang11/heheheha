"""YOLO person detection (spec 8). Ultralytics is imported lazily so the rest of the system runs without it.
Where it runs is one setting: perception.yolo.where = robot | remote | sim | off."""
from __future__ import annotations
import threading, time
from collections import deque
from pathlib import Path
from scoutbot.types import PersonDetection

def box_to_detection(x1, y1, x2, y2, conf, ycfg: dict, now: float, source: str = "yolo") -> PersonDetection:
    """Normalized box (0..1) -> which third of the image, and near/mid/far from the box height."""
    cx = (x1 + x2) / 2; h = y2 - y1
    where = "left" if cx < 1 / 3 else "right" if cx > 2 / 3 else "center"
    dist = "near" if h > ycfg.get("near_frac", 0.5) else "mid" if h > ycfg.get("mid_frac", 0.2) else "far"
    return PersonDetection(source=source, where=where, distance=dist, confidence=float(conf), bbox=(x1, y1, x2, y2), at=now)

DIST_RANK = {"far": 0, "mid": 1, "near": 2}

def nearest(dets: list[PersonDetection]) -> PersonDetection | None:
    return max(dets, key=lambda d: (DIST_RANK[d.distance], d.confidence)) if dets else None

class Confirmer:
    """A person must appear in k of the last n frames before it counts (cuts flicker and one-frame false alarms)."""
    def __init__(self, k: int = 2, n: int = 3):
        self.k, self.n = k, n; self.hist = deque(maxlen=n)
    def push(self, dets: list[PersonDetection]) -> list[PersonDetection]:
        self.hist.append(bool(dets))
        return dets if sum(self.hist) >= self.k and dets else []

class YoloDetector:
    def __init__(self, ycfg: dict):
        from ultralytics import YOLO            # pip install ultralytics
        self.cfg = ycfg
        model_path = ycfg.get("model", "yolov8n.pt")
        self.model = YOLO(model_path, task="detect") if Path(model_path).is_dir() else YOLO(model_path)
        dev = ycfg.get("device", "auto"); self.device = None if dev == "auto" else dev
        if self.device is None:
            try:
                import torch
                if torch.backends.mps.is_available(): self.device = "mps"
            except Exception: pass
    def detect(self, frame, now: float) -> list[PersonDetection]:
        h, w = frame.shape[:2]
        kw = dict(imgsz=self.cfg.get("imgsz", 320), conf=self.cfg.get("min_conf", 0.45), classes=[0], verbose=False)
        if self.device: kw["device"] = self.device
        res = self.model.predict(frame, **kw)[0]
        out = []
        for b in res.boxes:
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
            out.append(box_to_detection(x1 / w, y1 / h, x2 / w, y2 / h, float(b.conf[0]), self.cfg, now))
        return out

class PerceptionWorker:
    """Runs detection on the newest frame as fast as it can and writes CONFIRMED detections to shared state."""
    def __init__(self, cfg: dict, shared, world=None):
        self.cfg = cfg; self.y = cfg["perception"]["yolo"]; self.shared = shared; self.world = world
        k, n = self.y.get("confirm", [2, 3]); self.conf = Confirmer(k, n); self.detector = None; self._stop = threading.Event()
    def _status(self, s):
        with self.shared.lock: self.shared.det_status = s; self.shared.services["yolo"] = s
    def run(self):
        where = self.y.get("where", "robot")
        if where in (False, None, "off", "false", "none"): where = "off"   # YAML reads a bare `off` as False
        if where == "off": self._status("off"); return
        if where == "remote": self._status("remote (laptop worker)"); return
        if where == "sim":
            self._status("sim")
            while not self._stop.is_set():
                now = time.monotonic(); dets = self.conf.push(self.world.detections(now) if self.world else [])
                with self.shared.lock: self.shared.detections = dets; self.shared.det_at = now; self.shared.det_fps = 10.0
                time.sleep(0.1)
            return
        try:
            self._status("loading model"); self.detector = YoloDetector(self.y); self._status("running")
        except Exception as e:
            self._status(f"unavailable: {type(e).__name__}: {e}"[:160]); print("[yolo]", self.shared.det_status, flush=True); return
        last_seq = -1; times = deque(maxlen=20)
        while not self._stop.is_set():
            with self.shared.lock: frame = self.shared.frame; seq = self.shared.frame_seq
            if frame is None or seq == last_seq: time.sleep(0.01); continue
            last_seq = seq; t0 = time.monotonic()
            try: raw = self.detector.detect(frame, t0)
            except Exception as e:
                self._status(f"error: {e}"[:160]); time.sleep(0.5); continue
            dets = self.conf.push(raw); now = time.monotonic(); times.append(now - t0)
            with self.shared.lock:
                self.shared.detections = dets; self.shared.det_at = now
                self.shared.det_fps = round(len(times) / max(sum(times), 1e-6), 1)
    def start(self):
        threading.Thread(target=self.run, daemon=True, name="perception").start(); return self
    def stop(self): self._stop.set()
