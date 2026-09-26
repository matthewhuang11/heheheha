"""Remote YOLO (R3): bad /api/detections bodies -> 400; the worker's reconnect backoff is quiet."""
from fastapi.testclient import TestClient
from scoutbot import settings
from scoutbot.perception.worker_remote import Backoff
from scoutbot.runtime import Runtime
from scoutbot.server.app import create_app

def test_bad_detection_bodies_are_400(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = settings.load("sim", ["hw.camera=synthetic", "voice.provider=fake", f"survivors.data_dir={tmp_path}"], load_env=False)
    rt = Runtime(cfg, start_workers=False); c = TestClient(create_app(rt))
    for body in (b"not json", b'{"detections": [{"where": "up"}]}', b'{"detections": 5}', b'{"detections": [], "fps": "fast"}'):
        assert c.post("/api/detections", content=body, headers={"content-type": "application/json"}).status_code == 400
    ok = c.post("/api/detections", json={"detections": [{"source": "yolo", "where": "left", "distance": "near", "confidence": 0.8,
                                                          "bbox": [0.1, 0.1, 0.3, 0.9], "at": 0}], "fps": 7.5})
    assert ok.status_code == 200 and rt.shared.det_status.startswith("remote") and rt.shared.detections[0].where == "left"
    rt.stop()

def test_backoff_prints_once_and_grows():
    out = []; b = Backoff(0.5, 5, log=lambda *a, **k: out.append(a[0]))
    delays = [b.fail("robot video", ConnectionError()) for _ in range(6)]
    assert delays == [0.5, 1, 2, 4, 5, 5] and len(out) == 1
    b.ok(); assert len(out) == 2 and "back" in out[1] and b.delay == 0.5
    b.ok(); assert len(out) == 2
