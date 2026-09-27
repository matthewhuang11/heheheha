"""Grabs frames on a background thread so readers always get the newest one."""
import subprocess
import threading
import time

import cv2
import numpy as np

import config


class PiCam:
    """Camera Module 3 on the csi port, read as raw yuv420 frames piped out of rpicam-vid.

    Same read()/release() shape as cv2.VideoCapture. Needs only rpicam-apps (already on the
    pi), not picamera2. Width should be a multiple of 64 so the frames come out unpadded.
    """

    def __init__(self, w=config.CAMERA_W, h=config.CAMERA_H):
        self.w, self.h = w, h
        self.size = w * h * 3 // 2
        cmd = ["rpicam-vid", "-t", "0", "-n", "--codec", "yuv420", "--width", str(w), "--height", str(h),
               "--framerate", str(config.CAMERA_FPS), "--autofocus-mode", "continuous", "-o", "-"]
        if config.CAMERA_ROTATE == 180:
            cmd += ["--rotation", "180"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self):
        buf = self.p.stdout.read(self.size)  # buffered pipe: blocks for a whole frame, or eof
        if len(buf) < self.size:
            return False, None  # rpicam-vid exited: no camera detected, or it's in use
        yuv = np.frombuffer(buf, np.uint8).reshape(self.h * 3 // 2, self.w)
        return True, cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

    def release(self):
        self.p.kill()
        self.p.wait()


class Camera:
    def __init__(self, src=config.CAMERA_SRC):
        self.src = int(src) if str(src).isdigit() else src
        self.frame = None
        self.frame_id = 0
        self.ok = False
        self._lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def _open(self):
        if self.src == "picam":
            return PiCam()
        if self.src == "gopro":
            import gopro
            url = gopro.start()
            if url is None:
                return cv2.VideoCapture()  # not attached yet: an unopened capture, retried by _run
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
        cap = cv2.VideoCapture(self.src)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_H)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _run(self):
        cap = self._open()
        while True:
            ok, frame = cap.read()
            if not ok:
                # camera unplugged or not there yet: keep retrying instead of crashing
                self.ok = False
                cap.release()
                time.sleep(3.0 if self.src in ("gopro", "picam") else 1.0)
                cap = self._open()
                continue
            with self._lock:
                self.frame = frame
                self.frame_id += 1
                self.ok = True

    def latest(self):
        with self._lock:
            return (None, 0) if self.frame is None else (self.frame.copy(), self.frame_id)
