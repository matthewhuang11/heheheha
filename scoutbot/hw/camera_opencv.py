"""Camera sources: a real webcam / USB camera / GoPro-as-webcam (OpenCV), a folder or video replay, and a synthetic
view for the sim when no webcam is available."""
from __future__ import annotations
import math, time
from pathlib import Path
import cv2, numpy as np

class OpenCVCamera:
    def __init__(self, index: int = 0, warmup_frames: int = 30):
        self.index = index; self.cap = cv2.VideoCapture(index); self.ok = bool(self.cap.isOpened())
        if self.ok:
            for _ in range(warmup_frames): self.cap.read(); time.sleep(0.03)   # macOS webcams start black
    def read(self):
        if not self.ok: return None
        ok, f = self.cap.read()
        return f if ok else None
    def close(self):
        try: self.cap.release()
        except Exception: pass

class FolderCamera:
    """Loops over the images in a folder (sorted), or over a video file, at a fixed FPS. Repeatable tests."""
    EXT = {".jpg", ".jpeg", ".png", ".bmp"}
    def __init__(self, path: str, fps: float = 10):
        p = Path(path); self.period = 1.0 / max(fps, 0.1); self.next_t = 0.0; self.i = 0; self.cap = None; self.files = []
        if p.is_dir(): self.files = sorted(x for x in p.iterdir() if x.suffix.lower() in self.EXT)
        elif p.exists(): self.cap = cv2.VideoCapture(str(p))
        self.ok = bool(self.files) or (self.cap is not None and self.cap.isOpened())
        if not self.ok: print(f"[camera] folder/video '{path}' has no images", flush=True)
    def read(self):
        now = time.monotonic()
        if now < self.next_t: time.sleep(self.next_t - now)
        self.next_t = time.monotonic() + self.period
        if self.cap is not None:
            ok, f = self.cap.read()
            if not ok: self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0); ok, f = self.cap.read()
            return f if ok else None
        if not self.files: return None
        f = cv2.imread(str(self.files[self.i % len(self.files)])); self.i += 1
        return f
    def close(self):
        if self.cap is not None: self.cap.release()

class SyntheticCamera:
    """A simple drawn first-person-ish view of the sim world, so the dashboard has video without a webcam.
    Not used for decisions in the sim (the sim scene/detections come from the world model directly)."""
    def __init__(self, world=None, size=(640, 360), fps: float = 15):
        self.world = world; self.w, self.h = size; self.period = 1.0 / fps; self.next_t = 0.0; self.ok = True
    def read(self):
        now = time.monotonic()
        if now < self.next_t: time.sleep(self.next_t - now)
        self.next_t = time.monotonic() + self.period
        img = np.zeros((self.h, self.w, 3), np.uint8)
        img[: self.h // 2] = (60, 45, 35); img[self.h // 2:] = (70, 70, 70)
        if self.world is not None:
            # one column per pixel group: raycast and draw a wall slice (a tiny ray-caster)
            cols = 64; fov = 60.0
            for c in range(cols):
                ang = fov / 2 - fov * (c + 0.5) / cols
                d = self.world.raycast(ang, max_cm=800)
                hgt = int(min(self.h, 9000 / max(d, 1)))
                shade = int(max(40, 220 - d * 0.35))
                x0 = int(c * self.w / cols); x1 = int((c + 1) * self.w / cols)
                cv2.rectangle(img, (x0, self.h // 2 - hgt // 2), (x1, self.h // 2 + hgt // 2), (shade, shade, shade), -1)
            for s in self.world.visible_survivors():
                x = int(self.w / 2 - s["bearing"] / 30.0 * self.w / 2)
                size = int(min(self.h * 0.9, 12000 / max(s["dist"], 1)))
                cv2.rectangle(img, (x - size // 4, self.h // 2 - size // 2), (x + size // 4, self.h // 2 + size // 2), (40, 120, 230), -1)
                cv2.circle(img, (x, self.h // 2 - size // 2 - size // 8), max(3, size // 8), (150, 190, 240), -1)
        cv2.putText(img, "SIMULATED VIEW " + time.strftime("%H:%M:%S"), (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        # a little noise so camera health does not think the feed is frozen
        img = cv2.add(img, np.random.randint(0, 6, img.shape, dtype=np.uint8))
        return img
    def close(self): pass
