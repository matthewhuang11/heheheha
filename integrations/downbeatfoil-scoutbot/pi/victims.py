"""Turns raw detections into a persistent list of located survivors.

Store-and-forward: everything is written to disk on the robot the moment it's found.
`status` goes "pending" -> "processed" once HQ (gemini or the local model) has read the
snapshot + audio and written a triage report.
"""
import json
import math
import threading
import time
import uuid

import cv2

import config

STORE = config.DATA_DIR / "victims.json"
SNAPS = config.DATA_DIR / "snaps"
SNAPS.mkdir(exist_ok=True)


def portrait(frame, det):
    """Frame the person, not the room: a 4:3 crop around their box with some context,
    so the survivor card shows a face and posture instead of a small figure in a wide shot."""
    H, W = frame.shape[:2]
    x, y, w, h = det["box"]
    cx, cy = x + w / 2, y + h / 2
    cw = max(w * 1.5, h * 1.5 * 4 / 3, 160)   # ~25% margin each side, never tiny
    ch = cw * 3 / 4
    cw, ch = min(cw, W), min(ch, H)
    x0 = int(min(max(cx - cw / 2, 0), W - cw))
    y0 = int(min(max(cy - ch / 2, 0), H - ch))
    crop = frame[y0:y0 + int(ch), x0:x0 + int(cw)]
    return cv2.resize(crop, (640, 480), interpolation=cv2.INTER_CUBIC)


def save_snap(vid, frame, det):
    cv2.imwrite(str(SNAPS / f"{vid}.jpg"), portrait(frame, det), [cv2.IMWRITE_JPEG_QUALITY, 88])
    cv2.imwrite(str(SNAPS / f"{vid}_full.jpg"), frame)  # whole scene, for gemini's hazard read


def locate(det, pose):
    """World position (m east, m north of entry) of a detection seen from `pose`."""
    ang = math.radians(pose["heading"] + det["bearing_deg"])
    return (pose["x"] + det["dist_m"] * math.sin(ang), pose["y"] + det["dist_m"] * math.cos(ang))


class VictimLog:
    def __init__(self):
        self._lock = threading.Lock()
        self.victims = json.loads(STORE.read_text()) if STORE.exists() else []
        self._streak = 0

    def _save(self):
        STORE.write_text(json.dumps(self.victims, indent=2))

    def _nearest(self, x, y):
        best = min(self.victims, key=lambda v: math.hypot(v["x"] - x, v["y"] - y), default=None)
        if best and math.hypot(best["x"] - x, best["y"] - y) < config.SAME_VICTIM_RADIUS_M:
            return best
        return None

    def nearest(self, x, y):
        with self._lock:
            v = self._nearest(x, y)
            return dict(v) if v else None

    def _add(self, det, x, y, frame):
        vid = uuid.uuid4().hex[:6]
        if frame is not None:
            save_snap(vid, frame, det)
        v = {
            "id": vid,
            "x": round(x, 2),
            "y": round(y, 2),
            "dist_m": det["dist_m"],
            "conf": det["conf"],
            "found_at": time.time(),
            "last_seen": time.time(),
            "sightings": 1,
            "contacted": False,      # robot spoke to them and recorded an answer
            "audio": None,           # filename in data/audio
            "transcript": None,
            "conversation": [],      # typed chat from the dashboard, when online
            "report": None,
            "report_source": None,
            "status": "pending",
        }
        self.victims.append(v)
        self._save()
        return vid

    def update(self, detections, pose, frame):
        """Call once per inference cycle. Returns a victim id when a new one is confirmed."""
        if not detections:
            self._streak = 0
            return None
        self._streak += 1
        if self._streak < config.CONFIRM_HITS:
            return None

        d = max(detections, key=lambda d: d["conf"])
        x, y = locate(d, pose)
        with self._lock:
            v = self._nearest(x, y)
            if v is None:
                return self._add(d, x, y, frame)
            v["last_seen"] = time.time()
            v["sightings"] += 1
            # keep the closest, most confident look at them for the report
            if d["conf"] > v["conf"] and frame is not None:
                v["conf"] = d["conf"]
                save_snap(v["id"], frame, d)
            self._save()
            return None

    def find_or_add(self, det, pose, frame):
        x, y = locate(det, pose)
        with self._lock:
            v = self._nearest(x, y)
            return v["id"] if v else self._add(det, x, y, frame)

    def get(self, vid):
        with self._lock:
            v = next((v for v in self.victims if v["id"] == vid), None)
            return dict(v) if v else None

    def patch(self, vid, **fields):
        with self._lock:
            for v in self.victims:
                if v["id"] == vid:
                    v.update(fields)
                    self._save()
                    return dict(v)

    def all(self):
        with self._lock:
            return [dict(v) for v in self.victims]

    def clear(self):
        with self._lock:
            self.victims = []
            self._save()
