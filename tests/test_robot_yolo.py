import sys
import types

from scoutbot.perception.yolo import YoloDetector
from scoutbot.tools.yolo_bench import export_ncnn


class FakeYolo:
    calls = []

    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs
        self.exports = []
        self.calls.append((model, kwargs))

    def export(self, **kwargs):
        self.exports.append(kwargs)
        return "yolov8n_ncnn_model"


def test_yolo_detector_marks_exported_folder_as_detection_model(monkeypatch, tmp_path):
    model_dir = tmp_path / "yolov8n_ncnn_model"
    model_dir.mkdir()
    FakeYolo.calls = []
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=FakeYolo))

    YoloDetector({"model": str(model_dir), "device": "cpu"})

    assert FakeYolo.calls == [(str(model_dir), {"task": "detect"})]


def test_ncnn_export_uses_requested_image_size(capsys):
    model = FakeYolo("yolov8n.pt")
    detector = types.SimpleNamespace(model=model)

    folder = export_ncnn(detector, 320)

    assert folder == "yolov8n_ncnn_model"
    assert model.exports == [{"format": "ncnn", "imgsz": 320}]
    assert "pi.yaml: model: yolov8n_ncnn_model" in capsys.readouterr().out
