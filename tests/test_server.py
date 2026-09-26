"""Robot server smoke test: page, REST, and WebSocket commands (sim profile, workers not started, no network)."""
from fastapi.testclient import TestClient
from scoutbot import settings
from scoutbot.runtime import Runtime
from scoutbot.server.app import create_app

def make(tmp_path):
    cfg = settings.load("sim", ["hw.camera=synthetic", "voice.provider=fake", f"survivors.data_dir={tmp_path}"], load_env=False)
    return Runtime(cfg, start_workers=False)

def test_page_and_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path); c = TestClient(create_app(rt))
    assert c.get("/").status_code == 200 and "Scoutbot" in c.get("/").text
    h = c.get("/api/health").json(); assert h["mode"] == "STOPPED"
    assert c.get("/api/survivors").json() == []
    assert c.get("/snapshots/../../etc/passwd").status_code == 404

def test_ws_modes_drive_and_estop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path); c = TestClient(create_app(rt))
    with c.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "drive", "action": "FORWARD"})              # not in MANUAL: refused
        m = ws.receive_json()
        while m["type"] != "reply": m = ws.receive_json()
        assert m["ok"] is False
        ws.send_json({"type": "mode", "mode": "MANUAL"}); ws.send_json({"type": "drive", "action": "FORWARD", "seq": 1})
        for _ in range(20):
            m = ws.receive_json()
            if m["type"] == "state" and m["mode"] == "MANUAL": break
        assert rt.shared.drive_cmd is not None and rt.shared.drive_cmd.action.value == "FORWARD"
        ws.send_json({"type": "estop"})
        for _ in range(20):
            m = ws.receive_json()
            if m["type"] == "state" and m["mode"] == "STOPPED": break
        assert m["mode"] == "STOPPED" and rt.shared.drive_cmd is None
    rt.stop()
