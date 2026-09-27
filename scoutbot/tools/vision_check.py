"""One safe, wheels-off-ground vision readiness check for a camera profile."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from robot.camera_health import CameraHealth
from scoutbot.hw.camera_opencv import PiCamera2Camera, SyntheticCamera, open_best_camera
from scoutbot.settings import get, load


def parser():
    p = argparse.ArgumentParser(description="Sample camera quality and print the Scoutbot vision setup checklist.")
    p.add_argument("--profile", default="pi")
    p.add_argument("--frames", type=int, default=30)
    p.add_argument("--save-dir", default="data/vision-check")
    p.add_argument("--skip-yolo", action="store_true", help="skip the on-device YOLO benchmark")
    return p


def open_camera(cfg):
    kind = get(cfg, "hw.camera", "opencv")
    if kind == "picamera2":
        return PiCamera2Camera(get(cfg, "hw.camera_size", [640, 480]), get(cfg, "hw.camera_fps", 15))
    if kind == "opencv":
        return open_best_camera(get(cfg, "hw.camera_index", 0))
    if kind == "synthetic":
        return SyntheticCamera(fps=get(cfg, "hw.camera_fps", 15))
    raise SystemExit(f"vision_check supports hw.camera=opencv, picamera2, or synthetic, not {kind!r}")


def assess(values: list[float], contrasts: list[float], sharpness: list[float], fps: float, health: dict,
           yolo: tuple[bool, str] = (False, "not run")) -> list[tuple[str, bool, str]]:
    return [
        ("camera health", bool(health.get("healthy")), "; ".join(health.get("reasons", [])) or "healthy"),
        ("brightness", 40 <= float(np.mean(values)) <= 220, f"mean {np.mean(values):.1f} (pass 40..220)"),
        ("contrast", float(np.mean(contrasts)) > 12, f"std {np.mean(contrasts):.1f} (pass >12)"),
        ("sharpness", float(np.mean(sharpness)) > 30, f"Laplacian variance {np.mean(sharpness):.1f} (advisory >30)"),
        ("capture FPS", fps >= 10, f"{fps:.1f} FPS (pass >=10)"),
        ("dashboard delay", False, "manual: wave/stopwatch test required (<500 ms LAN)"),
        ("YOLO FPS", yolo[0], yolo[1]),
    ]


def yolo_check(cfg: dict, profile: str) -> tuple[bool, str]:
    yolo = get(cfg, "perception.yolo", {})
    where = yolo.get("where", "robot")
    if where == "remote":
        return True, "remote worker selected: verify it is connected to /video.mjpg"
    if where in (False, None, "off"):
        return False, "YOLO is disabled"
    cmd = [sys.executable, "-m", "scoutbot.tools.yolo_bench", "--profile", profile,
           "--imgsz", str(yolo.get("imgsz", 320)), "--model", str(yolo.get("model", "yolov8n.pt"))]
    run = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=180)
    output = (run.stdout + "\n" + run.stderr).strip()
    match = re.search(r"YOLO:\s*([0-9.]+)\s*FPS", output)
    if match:
        fps = float(match.group(1))
        return fps >= 3, f"{fps:.2f} FPS (pass >=3)"
    return False, (output[-240:] or f"yolo_bench exited {run.returncode}")


def main(argv=None):
    args = parser().parse_args(argv)
    if args.frames < 2:
        raise SystemExit("--frames must be at least 2")
    cfg = load(args.profile); camera = open_camera(cfg)
    if not getattr(camera, "ok", False):
        raise SystemExit(f"camera unavailable: {getattr(camera, 'error', '')}")
    out = Path(args.save_dir); out.mkdir(parents=True, exist_ok=True)
    values: list[float] = []; contrasts: list[float] = []; sharpness: list[float] = []; times: list[float] = []
    health_check = CameraHealth(); health = {"healthy": False, "reasons": ["no frames"]}
    try:
        for i in range(args.frames):
            frame = camera.read(); now = time.monotonic()
            if frame is None:
                raise SystemExit("camera returned no frame")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            values.append(float(gray.mean())); contrasts.append(float(gray.std()))
            sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var())); times.append(now)
            health = health_check.update(frame, now)
            if i in (0, args.frames - 1): cv2.imwrite(str(out / f"sample-{i:02d}.jpg"), frame)
    finally:
        camera.close()
    fps = (len(times) - 1) / max(times[-1] - times[0], 1e-6)
    yolo = (False, "skipped by --skip-yolo") if args.skip_yolo else yolo_check(cfg, args.profile)
    checks = assess(values, contrasts, sharpness, fps, health, yolo)
    print(f"[vision_check] camera={get(cfg, 'hw.camera')} index={getattr(camera, 'index', '?')} samples={out}")
    for label, passed, detail in checks:
        print(f"[{'PASS' if passed else 'CHECK'}] {label}: {detail}")
    return checks


if __name__ == "__main__":
    main()
