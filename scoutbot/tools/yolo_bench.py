"""Benchmark YOLO person detection and export a Pi-ready NCNN model."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from scoutbot.hw.camera_opencv import open_best_camera
from scoutbot.perception.yolo import YoloDetector
from scoutbot.settings import get, load


FRAME_COUNT = 50


def parser():
    parser = argparse.ArgumentParser(
        description="Benchmark YOLO person detection on 50 frames."
    )
    parser.add_argument("--profile", default="mac")
    parser.add_argument("--folder")
    parser.add_argument("--model", help="override perception.yolo.model, for example yolov8n_ncnn_model")
    parser.add_argument("--imgsz", type=int, choices=[320, 640], default=320)
    parser.add_argument("--export-ncnn", action="store_true")
    parser.add_argument(
        "--log-boxes",
        action="store_true",
        help="print every detected person box height as a fraction of image height",
    )
    return parser


def export_ncnn(detector: YoloDetector, imgsz: int) -> str:
    output = detector.model.export(format="ncnn", imgsz=imgsz)
    folder = str(output)
    print(f"NCNN export: {folder}")
    print(f"pi.yaml: model: {folder}")
    return folder


def main(argv=None):
    args = parser().parse_args(argv)
    cfg = load(args.profile)
    ycfg = dict(get(cfg, "perception.yolo", {}), imgsz=args.imgsz)
    if args.model:
        ycfg["model"] = args.model
    detector = YoloDetector(ycfg)
    if args.export_ncnn:
        export_ncnn(detector, args.imgsz)
        return

    files = sorted(Path(args.folder).glob("*")) if args.folder else []
    camera = None if files else open_best_camera(get(cfg, "hw.camera_index", 0))
    if camera is not None and not camera.ok:
        raise SystemExit("no camera available")
    times: list[float] = []
    try:
        for index in range(FRAME_COUNT):
            frame = cv2.imread(str(files[index % len(files)])) if files else camera.read()
            if frame is None:
                raise SystemExit("no frame available")
            started = time.monotonic()
            detections = detector.detect(frame, started)
            times.append(time.monotonic() - started)
            if args.log_boxes:
                for detection in detections:
                    if detection.bbox is not None:
                        height = detection.bbox[3] - detection.bbox[1]
                        print(
                            f"box frame={index} where={detection.where} "
                            f"height_frac={height:.3f} confidence={detection.confidence:.2f}"
                        )
    finally:
        if camera is not None:
            camera.close()

    fps = len(times) / max(sum(times), 1e-6)
    print(f"YOLO: {fps:.2f} FPS ({args.imgsz}px)")
    if fps < 3:
        print("use perception.yolo.where=remote")


if __name__ == "__main__":
    main()
