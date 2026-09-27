"""Camera sources for real cameras, folders, videos, and the simulator."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


def _capture(index: int):
    """Open a camera with the fast Windows backend when it is available."""
    if sys.platform.startswith("win"):
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)


class OpenCVCamera:
    def __init__(self, index: int = 0, warmup_frames: int = 0):
        self.index = index
        self.cap = _capture(index)
        self.ok = bool(self.cap.isOpened())
        if self.ok:
            for _ in range(warmup_frames):
                self.cap.read()
                time.sleep(0.03)

    def read(self):
        if not self.ok:
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def has_picture(self, tries: int = 10) -> bool:
        """Return True after reading a frame that is not effectively black."""
        for _ in range(max(0, tries)):
            frame = self.read()
            if frame is not None and float(frame.mean()) > 8:
                return True
        return False

    def close(self):
        try:
            self.cap.release()
        except Exception:
            pass


class PiCamera2Camera:
    """Raspberry Pi Camera Module source, loaded only on a Pi with picamera2.

    Picamera2 returns RGB arrays.  Scoutbot's camera contract is BGR, matching
    OpenCV and the dashboard JPEG encoder, so conversion happens at this edge.
    """

    def __init__(self, size=(640, 480), fps: float = 15):
        self.index = "picamera2"
        self.ok = False
        self.camera = None
        self.error = ""
        try:
            from picamera2 import Picamera2
            self.camera = Picamera2()
            width, height = (int(size[0]), int(size[1]))
            config = self.camera.create_video_configuration(main={"size": (width, height), "format": "RGB888"})
            self.camera.configure(config)
            self.camera.start()
            # Let auto-exposure settle before the first health sample.
            time.sleep(max(0.0, min(2.0, 2.0 / max(float(fps), 1.0))))
            self.ok = True
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.close()

    def read(self):
        if not self.ok or self.camera is None:
            return None
        try:
            rgb = self.camera.capture_array("main")
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def close(self):
        if self.camera is not None:
            try:
                self.camera.stop()
            except Exception:
                pass
            try:
                self.camera.close()
            except Exception:
                pass
        self.camera = None


def open_best_camera(
    preferred: int,
    candidates: Iterable[int] = range(4),
    verbose: bool = True,
) -> OpenCVCamera:
    """Find a camera with a visible image, favoring the configured index.

    A dark room is still a usable camera, so if every opened camera is black the
    first opened device is returned.  If no device opens, a closed camera is
    returned with ``ok`` false.
    """
    indexes = [preferred, *(index for index in candidates if index != preferred)]
    first_open: OpenCVCamera | None = None
    first_closed: OpenCVCamera | None = None

    for index in indexes:
        camera = OpenCVCamera(index)
        if not camera.ok:
            if first_closed is None:
                first_closed = camera
            else:
                camera.close()
            continue
        if first_open is None:
            first_open = camera
        if camera.has_picture():
            if index != preferred and verbose:
                print(
                    f"[camera] camera {preferred} has no picture; using camera {index} "
                    f"(set CAMERA_INDEX={index} in .env to skip this search)",
                    flush=True,
                )
            if camera is not first_open and first_open is not None:
                first_open.close()
            return camera
        if camera is not first_open:
            camera.close()

    if first_open is not None:
        return first_open
    if first_closed is not None:
        first_closed.close()
        first_closed.ok = False
        return first_closed
    camera = OpenCVCamera(preferred)
    camera.close()
    camera.ok = False
    return camera


class FolderCamera:
    """Loop images in a folder or a video at a fixed FPS for repeatable tests."""

    EXT = {".jpg", ".jpeg", ".png", ".bmp"}

    def __init__(self, path: str, fps: float = 10):
        path_obj = Path(path)
        self.period = 1.0 / max(fps, 0.1)
        self.next_t = 0.0
        self.i = 0
        self.cap = None
        self.files = []
        if path_obj.is_dir():
            self.files = sorted(
                item for item in path_obj.iterdir() if item.suffix.lower() in self.EXT
            )
        elif path_obj.exists():
            self.cap = cv2.VideoCapture(str(path_obj))
        self.ok = bool(self.files) or (self.cap is not None and self.cap.isOpened())
        if not self.ok:
            print(f"[camera] folder/video '{path}' has no images", flush=True)

    def read(self):
        now = time.monotonic()
        if now < self.next_t:
            time.sleep(self.next_t - now)
        self.next_t = time.monotonic() + self.period
        if self.cap is not None:
            ok, frame = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
            return frame if ok else None
        if not self.files:
            return None
        frame = cv2.imread(str(self.files[self.i % len(self.files)]))
        self.i += 1
        return frame

    def close(self):
        if self.cap is not None:
            self.cap.release()


class SyntheticCamera:
    """Draw a first-person simulator view for the dashboard, not decisions."""

    def __init__(self, world=None, size=(640, 360), fps: float = 15):
        self.world = world
        self.w, self.h = size
        self.period = 1.0 / fps
        self.next_t = 0.0
        self.ok = True

    def read(self):
        now = time.monotonic()
        if now < self.next_t:
            time.sleep(self.next_t - now)
        self.next_t = time.monotonic() + self.period
        image = np.zeros((self.h, self.w, 3), np.uint8)
        image[: self.h // 2] = (60, 45, 35)
        image[self.h // 2 :] = (70, 70, 70)
        if self.world is not None:
            cols = 64
            fov = 60.0
            for column in range(cols):
                angle = fov / 2 - fov * (column + 0.5) / cols
                distance = self.world.raycast(angle, max_cm=800)
                height = int(min(self.h, 9000 / max(distance, 1)))
                shade = int(max(40, 220 - distance * 0.35))
                x0 = int(column * self.w / cols)
                x1 = int((column + 1) * self.w / cols)
                cv2.rectangle(
                    image,
                    (x0, self.h // 2 - height // 2),
                    (x1, self.h // 2 + height // 2),
                    (shade, shade, shade),
                    -1,
                )
            for survivor in self.world.visible_survivors():
                x = int(self.w / 2 - survivor["bearing"] / 30.0 * self.w / 2)
                size = int(min(self.h * 0.9, 12000 / max(survivor["dist"], 1)))
                cv2.rectangle(
                    image,
                    (x - size // 4, self.h // 2 - size // 2),
                    (x + size // 4, self.h // 2 + size // 2),
                    (40, 120, 230),
                    -1,
                )
                cv2.circle(
                    image,
                    (x, self.h // 2 - size // 2 - size // 8),
                    max(3, size // 8),
                    (150, 190, 240),
                    -1,
                )
        cv2.putText(
            image,
            "SIMULATED VIEW " + time.strftime("%H:%M:%S"),
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
        return cv2.add(image, np.random.randint(0, 6, image.shape, dtype=np.uint8))

    def close(self):
        pass
