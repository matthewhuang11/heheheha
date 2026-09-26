"""Save sample frames from the best available OpenCV camera."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from scoutbot.hw.camera_opencv import open_best_camera
from scoutbot.settings import get, load


FRAME_COUNT = 20
BLACK_MEAN = 8.0


def parser():
    parser = argparse.ArgumentParser(
        description="Save 20 camera frames and report selected index, resolution, FPS, and black frames."
    )
    parser.add_argument("--profile", default="mac")
    return parser


def main(argv=None):
    args = parser().parse_args(argv)
    cfg = load(args.profile)
    camera = open_best_camera(get(cfg, "hw.camera_index", 0))
    output_dir = Path("data/camcheck")
    output_dir.mkdir(parents=True, exist_ok=True)
    durations: list[float] = []
    means: list[float] = []
    width = height = 0
    try:
        for index in range(FRAME_COUNT):
            started = time.monotonic()
            frame = camera.read()
            durations.append(time.monotonic() - started)
            if frame is None:
                raise SystemExit(f"camera {camera.index} returned no frame")
            means.append(float(frame.mean()))
            cv2.imwrite(str(output_dir / f"{index:02d}.jpg"), frame)
            if index == 0:
                height, width = frame.shape[:2]
    finally:
        camera.close()

    fps = len(durations) / max(sum(durations), 0.001)
    black = all(mean <= BLACK_MEAN for mean in means)
    print(
        f"[camcheck] index {camera.index}, {width}x{height}, {fps:.1f} FPS, "
        f"black={'yes' if black else 'no'}, saved {output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
