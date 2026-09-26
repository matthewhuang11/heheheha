"""Run YOLO on the laptop against the robot's video stream and post detections back (spec 8.2, where: remote).
Use this if the Pi 4 is too slow. On the robot set perception.yolo.where=remote.

  python -m scoutbot.perception.worker_remote --robot http://<pi-ip>:8000 [--token T] [--profile laptop]

When the robot is down or restarts, the worker waits and reconnects by itself, printing one message per outage
(not one per frame), with a backoff of 0.5 s growing to 5 s."""
from __future__ import annotations
import argparse, time
from scoutbot import settings

class Backoff:
    """Quiet reconnect: first failure prints a message, repeats are silent; the delay doubles up to max_s."""
    def __init__(self, start_s: float = 0.5, max_s: float = 5.0, log=print):
        self.start, self.max, self.delay, self.down, self.log = start_s, max_s, start_s, None, log
    def fail(self, what: str, err: Exception) -> float:
        if self.down is None:
            self.down = what
            self.log(f"[remote yolo] {what} failed ({type(err).__name__}); retrying quietly every {self.start:g}-{self.max:g} s", flush=True)
        d = self.delay; self.delay = min(self.max, self.delay * 2); return d
    def ok(self):
        if self.down is not None: self.log(f"[remote yolo] {self.down} is back", flush=True)
        self.down = None; self.delay = self.start

def parser():
    ap = argparse.ArgumentParser(prog="python -m scoutbot.perception.worker_remote", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--robot", required=True, help="e.g. http://192.168.1.50:8000")
    ap.add_argument("--profile", default="laptop"); ap.add_argument("--token", default="")
    return ap

def main(argv=None):
    import cv2, httpx
    from scoutbot.perception.yolo import Confirmer, YoloDetector
    a = parser().parse_args(argv); cfg = settings.load(a.profile); y = cfg["perception"]["yolo"]
    det = YoloDetector(y); k, n = y.get("confirm", [2, 3]); conf = Confirmer(k, n)
    q = f"?token={a.token}" if a.token else ""
    url = a.robot.rstrip("/") + "/video.mjpg" + q; post = a.robot.rstrip("/") + "/api/detections" + q
    client = httpx.Client(timeout=2); times: list[float] = []
    video, net = Backoff(), Backoff()
    print(f"[remote yolo] reading {a.robot.rstrip('/')}/video.mjpg", flush=True)
    cap = None
    while True:
        try:
            if cap is None or not cap.isOpened():
                cap = cv2.VideoCapture(url)
                if not cap.isOpened(): raise ConnectionError("video stream not reachable")
            ok, frame = cap.read()
            if not ok: raise ConnectionError("no frame from video stream")
            video.ok()
        except Exception as e:
            if cap is not None: cap.release()
            cap = None; time.sleep(video.fail("robot video", e)); continue
        t0 = time.monotonic(); dets = conf.push(det.detect(frame, t0)); times = (times + [time.monotonic() - t0])[-20:]
        try:
            r = client.post(post, json={"detections": [d.model_dump() for d in dets], "fps": round(len(times) / sum(times), 1)})
            if r.status_code == 401: raise SystemExit("[remote yolo] the robot wants a token: add --token <SCOUTBOT_TOKEN>")
            r.raise_for_status(); net.ok()
        except SystemExit: raise
        except Exception as e:
            time.sleep(net.fail("posting detections", e))

if __name__ == "__main__": main()
