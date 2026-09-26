"""Survivor registry (spec 9.2): turn confirmed person detections into survivor records, merge repeat sightings,
save snapshots, and write every change to data/survivors.jsonl FIRST, then to the sync outbox.

Merge rule (refined from the spec after testing in the sim): the spec's max(100 cm, 1.5 x uncertainty) merges every
survivor into one after a few metres of driving, because total uncertainty keeps growing. What matters is the drift
BETWEEN two sightings, so the merge radius is: merge_cm + 0.3 x (distance driven since that survivor was last seen)
+ slack for how rough the distance guess is (near 30 cm, mid 80 cm, far 120 cm). The nearest survivor inside it wins.
Two people detected in the same frame are never merged into one survivor (pass exclude=)."""
from __future__ import annotations
import json, math, threading, time
from pathlib import Path
import cv2
from scoutbot.types import PersonDetection, Pose, Survivor, utc_now

SLACK = {"near": 30.0, "mid": 80.0, "far": 120.0}
DRIFT = 0.3            # matches the ~30% dead-reckoning drift
WEIGHT = {"near": 3.0, "mid": 2.0, "far": 1.0}
PERSIST_EVERY_S = 2.0

class Registry:
    def __init__(self, cfg: dict, bus=None, outbox=None, data_dir: str | Path | None = None):
        sc = cfg["survivors"]; self.cfg = sc; self.bus = bus; self.outbox = outbox
        self.dir = Path(data_dir or sc.get("data_dir", "data")); (self.dir / "snapshots").mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "survivors.jsonl"; self.lock = threading.RLock()
        self.items: dict[str, Survivor] = {}; self._w: dict[str, float] = {}; self._odo_seen: dict[str, float] = {}
        self._saved_at: dict[str, float] = {}; self._dirty: set[str] = set(); self._n = 0
        self._load()

    def _load(self):
        if not self.path.exists(): return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try: s = Survivor.model_validate_json(line)
            except Exception: continue
            self.items[s.id] = s; self._w[s.id] = max(1.0, s.sightings); self._odo_seen[s.id] = 0.0
            self._n = max(self._n, int(s.id.split("-")[1]))
        if self.items: print(f"[survivors] reloaded {len(self.items)} from {self.path}", flush=True)

    def all(self) -> list[Survivor]:
        with self.lock: return [s.model_copy(deep=True) for s in sorted(self.items.values(), key=lambda s: s.id)]
    def get(self, sid: str) -> Survivor | None:
        with self.lock:
            s = self.items.get(sid); return s.model_copy(deep=True) if s else None

    @staticmethod
    def estimate(det: PersonDetection, pose: Pose, sc: dict) -> tuple[float, float]:
        b = {"left": sc.get("bearing_deg", 25), "right": -sc.get("bearing_deg", 25), "center": 0}[det.where]
        d = sc["dist_cm"][det.distance]; a = math.radians(pose.heading_deg + b)
        return pose.x_cm + d * math.cos(a), pose.y_cm + d * math.sin(a)

    def sighting(self, det: PersonDetection, pose: Pose, odometer: float, frame=None, exclude: set | None = None) -> tuple[Survivor | None, bool]:
        """Record one confirmed detection. Returns (survivor, is_new), or (None, False) when a FAR sighting matches nobody:
        "far" means anything past ~2.5 m, so its position guess is too rough to start a new record (tested in the sim,
        it made duplicates in the wrong place). Far sightings still update survivors already on the list; the robot
        creates the record once it is close enough for a mid or near sighting."""
        x, y = self.estimate(det, pose, self.cfg); now = time.monotonic()
        with self.lock:
            best, best_d = None, None
            for sid, s in self.items.items():
                if exclude and sid in exclude: continue
                radius = self.cfg.get("merge_cm", 100) + DRIFT * max(0.0, odometer - self._odo_seen.get(sid, odometer)) + SLACK[det.distance]
                d = math.hypot(s.pose.x_cm - x, s.pose.y_cm - y)
                if d <= radius and (best_d is None or d < best_d): best, best_d = s, d
            box = 0.0 if det.bbox is None else det.bbox[3] - det.bbox[1]
            if best is None and det.distance == "far":
                return None, False
            if best is None:
                self._n += 1; sid = f"S-{self._n:04d}"; ts = utc_now()
                s = Survivor(id=sid, first_seen=ts, last_seen=ts, sightings=1,
                             pose=Pose(x_cm=round(x, 1), y_cm=round(y, 1), heading_deg=0, uncertainty_cm=pose.uncertainty_cm + SLACK[det.distance], source=pose.source))
                self.items[sid] = s; self._w[sid] = WEIGHT[det.distance]; self._odo_seen[sid] = odometer
                if frame is not None: self._snapshot(s, frame, box)
                self._persist(s, now, sighting=(det, x, y)); new = True
            else:
                s = best; w0 = self._w.get(s.id, 1.0); w = WEIGHT[det.distance]
                nx = (s.pose.x_cm * w0 + x * w) / (w0 + w); ny = (s.pose.y_cm * w0 + y * w) / (w0 + w)
                s.pose = Pose(x_cm=round(nx, 1), y_cm=round(ny, 1), heading_deg=0,
                              uncertainty_cm=round(min(s.pose.uncertainty_cm, pose.uncertainty_cm + SLACK[det.distance]), 1), source=pose.source)
                self._w[s.id] = min(w0 + w, 30.0); self._odo_seen[s.id] = odometer
                s.sightings += 1; s.last_seen = utc_now(); new = False
                snap = frame is not None and box > max(0.05, s.best_box_frac * 1.2)
                if snap: self._snapshot(s, frame, box)
                if snap or now - self._saved_at.get(s.id, 0) >= PERSIST_EVERY_S: self._persist(s, now, sighting=(det, x, y))
                else: self._dirty.add(s.id)
            return s.model_copy(deep=True), new

    def _snapshot(self, s: Survivor, frame, box: float):
        n = int(s.snapshots[-1].rsplit("_", 1)[1][:4]) + 1 if s.snapshots else 1      # never reuse a name after old ones are dropped
        name = f"{s.id}_{n:04d}.jpg"
        try: cv2.imwrite(str(self.dir / "snapshots" / name), frame)
        except Exception as e: print("[survivors] snapshot failed:", e, flush=True); return
        s.snapshots.append(name); s.best_snapshot = name; s.best_box_frac = box
        while len(s.snapshots) > self.cfg.get("max_snapshots", 5):
            old = s.snapshots.pop(0)
            try: (self.dir / "snapshots" / old).unlink()
            except OSError: pass

    def update(self, sid: str, fn) -> Survivor | None:
        """Apply fn(survivor) under the lock and persist (used for chat and triage)."""
        with self.lock:
            s = self.items.get(sid)
            if s is None: return None
            fn(s); self._persist(s, time.monotonic()); return s.model_copy(deep=True)

    def flush(self):
        with self.lock:
            for sid in list(self._dirty): self._persist(self.items[sid], time.monotonic())

    def _persist(self, s: Survivor, now: float, sighting=None):
        s.version += 1; self._saved_at[s.id] = now; self._dirty.discard(s.id)
        with open(self.path, "a", encoding="utf-8") as f: f.write(s.model_dump_json() + "\n")       # local first
        if self.outbox is not None:
            self.outbox.put_survivor(s)
            if sighting is not None:
                det, x, y = sighting
                self.outbox.add_rows("sightings", [{"time": utc_now(), "survivor_id": s.id, "x_cm": round(x, 1), "y_cm": round(y, 1),
                                                    "uncertainty_cm": s.pose.uncertainty_cm, "source": det.source, "confidence": det.confidence}])
        if self.bus is not None: self.bus.publish("survivor", s.model_dump())
