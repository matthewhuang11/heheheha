"""Person detection with a YOLOv8n ONNX model through OpenCV DNN (no torch on the pi)."""
import math
import threading
import time
from pathlib import Path

import cv2
import numpy as np

import config

PERSON = 0


class Detector:
    def __init__(self, camera):
        self.camera = camera
        self.detections = []  # list of dicts, newest inference only
        self.fps = 0.0
        self.error = None
        self.net = None
        if Path(config.MODEL_PATH).exists():
            self.net = cv2.dnn.readNetFromONNX(config.MODEL_PATH)
        else:
            self.error = f"model missing: {config.MODEL_PATH}"
        threading.Thread(target=self._run, daemon=True).start()

    def _infer(self, frame):
        h, w = frame.shape[:2]
        s = config.MODEL_SIZE
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (s, s), swapRB=True, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()[0].T  # (N, 84): cx, cy, w, h, 80 class scores

        scores = out[:, 4 + PERSON]
        keep = scores > config.CONF_THRESHOLD
        out, scores = out[keep], scores[keep]
        if len(out) == 0:
            return []

        sx, sy = w / s, h / s
        boxes = [[(cx - bw / 2) * sx, (cy - bh / 2) * sy, bw * sx, bh * sy]
                 for cx, cy, bw, bh in out[:, :4]]
        idx = cv2.dnn.NMSBoxes(boxes, scores.tolist(), config.CONF_THRESHOLD, 0.45)

        f_px = (w / 2) / math.tan(math.radians(config.CAMERA_HFOV_DEG / 2))
        dets = []
        for i in np.array(idx).flatten():
            x, y, bw, bh = boxes[i]
            # monocular estimate from apparent body size; swap for a depth/tof reading when we have one
            x, y, bw, bh = float(x), float(y), float(bw), float(bh)
            dist = f_px * config.PERSON_LENGTH_M / max(bw, bh, 1)
            bearing = math.degrees(math.atan(((x + bw / 2) - w / 2) / f_px))
            dets.append({
                "box": [int(x), int(y), int(bw), int(bh)],
                "conf": round(float(scores[i]), 2),
                "dist_m": round(dist, 2),
                "bearing_deg": round(bearing, 1),
            })
        return dets

    def _run(self):
        last_id = 0
        while True:
            if self.net is None:
                time.sleep(1)
                continue
            frame, fid = self.camera.latest()
            if frame is None or fid == last_id:
                time.sleep(0.01)
                continue
            last_id = fid
            t0 = time.time()
            try:
                self.detections = self._infer(frame)
                self.error = None
            except Exception as e:  # keep the loop alive; surface the error on the dashboard
                self.error = str(e)
                self.detections = []
            # cap the rate: flat out, yolo pins all four cores and cooks a bare pi past 80 c
            time.sleep(max(0.0, 1 / config.DETECT_FPS - (time.time() - t0)))
            dt = time.time() - t0
            self.fps = round(0.8 * self.fps + 0.2 * (1 / dt if dt else 0), 1)


def draw(frame, detections):
    orange, ink = (44, 107, 255), (18, 15, 13)  # bgr of the dashboard accent and its background
    for d in detections:
        x, y, w, h = d["box"]
        # targeting brackets: four corners instead of a full box, so the person stays visible
        k = max(10, int(min(w, h) * 0.22))
        for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
            cv2.line(frame, (cx, cy), (cx + dx * k, cy), orange, 3, cv2.LINE_AA)
            cv2.line(frame, (cx, cy), (cx, cy + dy * k), orange, 3, cv2.LINE_AA)
        # label pill above the top-left corner
        label = f"person  {d['dist_m']:.1f} m"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        ly = y - 8 if y - th - 14 > 0 else y + h + th + 12
        cv2.rectangle(frame, (x, ly - th - 7), (x + tw + 12, ly + 5), orange, -1)
        cv2.putText(frame, label, (x + 6, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.5, ink, 1, cv2.LINE_AA)
    return frame
