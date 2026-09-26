"""Run YOLO on the laptop against the robot's video stream and post detections back (spec 8.2, where: remote).
Use this if the Pi 4 is too slow. On the robot set perception.yolo.where=remote.

  python -m scoutbot.perception.worker_remote --robot http://<pi-ip>:8000
"""
from __future__ import annotations
import argparse, time
import cv2, httpx
from scoutbot import settings
from scoutbot.perception.yolo import Confirmer, YoloDetector

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--robot", required=True, help="e.g. http://192.168.1.50:8000")
    ap.add_argument("--profile", default="mac"); ap.add_argument("--token", default="")
    a = ap.parse_args(); cfg = settings.load(a.profile); y = cfg["perception"]["yolo"]
    det = YoloDetector(y); k, n = y.get("confirm", [2, 3]); conf = Confirmer(k, n)
    url = a.robot.rstrip("/") + "/video.mjpg"; post = a.robot.rstrip("/") + "/api/detections" + (f"?token={a.token}" if a.token else "")
    cap = cv2.VideoCapture(url); client = httpx.Client(timeout=2)
    print(f"[remote yolo] reading {url}", flush=True); times = []
    while True:
        ok, frame = cap.read()
        if not ok: time.sleep(0.5); cap = cv2.VideoCapture(url); continue
        t0 = time.monotonic(); dets = conf.push(det.detect(frame, t0)); times = (times + [time.monotonic() - t0])[-20:]
        try: client.post(post, json={"detections": [d.model_dump() for d in dets], "fps": round(len(times) / sum(times), 1)})
        except Exception as e: print("[remote yolo] post failed:", e, flush=True); time.sleep(0.5)

if __name__ == "__main__": main()
