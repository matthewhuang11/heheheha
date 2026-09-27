"""Export YOLOv8n to a 320px ONNX that OpenCV DNN on the pi can load.

Run on the laptop:  tools/.venv/Scripts/python tools/export_model.py
"""
import shutil
from pathlib import Path

from ultralytics import YOLO

out_dir = Path(__file__).resolve().parent.parent / "pi" / "models"
out_dir.mkdir(parents=True, exist_ok=True)

onnx = YOLO("yolov8n.pt").export(format="onnx", imgsz=320, opset=12, simplify=True, dynamic=False)
dest = out_dir / "yolov8n-320.onnx"
shutil.move(onnx, dest)
print(f"wrote {dest}")
