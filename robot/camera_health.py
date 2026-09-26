"""Is the camera frame usable? An unhealthy camera is treated exactly like a missing camera (sensors only, capped at SLOW).
Sharpness is advisory only: Laplacian-variance thresholds depend on the scene and must be tuned."""
import cv2, numpy as np

DARK, BRIGHT, LOW_CONTRAST, BLURRY = 25.0, 235.0, 12.0, 30.0

class CameraHealth:
    def __init__(self, frozen_s=2.0):
        self.prev = None; self.last_change = None; self.frozen_s = frozen_s
        self.last = {"healthy": False, "reasons": ["no frame yet"], "brightness": 0, "contrast": 0, "sharpness": 0, "frozen": False}
    def update(self, frame, now):
        g = cv2.cvtColor(cv2.resize(frame, (160, 120)), cv2.COLOR_BGR2GRAY)
        b, c = float(g.mean()), float(g.std()); sharp = float(cv2.Laplacian(g, cv2.CV_64F).var())
        if self.prev is None or float(np.abs(g.astype(np.int16) - self.prev).mean()) > 0.05: self.last_change = now
        self.prev = g.astype(np.int16)
        frozen = now - (self.last_change or now) > self.frozen_s
        reasons = []
        if b < DARK: reasons.append("too dark")
        if b > BRIGHT: reasons.append("washed out")
        if c < LOW_CONTRAST: reasons.append("no contrast (lens blocked?)")
        if frozen: reasons.append("frozen feed")
        self.last = {"healthy": not reasons, "reasons": reasons, "brightness": round(b, 1), "contrast": round(c, 1),
                     "sharpness": round(sharp, 1), "blurry": sharp < BLURRY, "frozen": frozen}
        return self.last
