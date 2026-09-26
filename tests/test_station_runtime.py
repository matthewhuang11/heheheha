"""Runtime command safety (KI-07) and a fast dashboard state (KI-08)."""
import time
import numpy as np
from scoutbot import settings
from scoutbot.runtime import Runtime
from scoutbot.types import ChatMessage, PersonDetection, Pose

def make(tmp_path, *extra):
    cfg = settings.load("laptop", ["hw.camera=synthetic", "voice.provider=fake", "sync.sinks=[]", "scene.provider=fake",
                                   "perception.yolo.where=off", "talk.enabled=false", f"survivors.data_dir={tmp_path}", *extra], load_env=False)
    return Runtime(cfg, start_workers=False)

def test_test_commands_refused_when_test_controls_off(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path, "server.test_controls=false")
    assert rt.command({"type": "sim", "offline": True})["ok"] is False and rt.shared.force_offline is False
    assert rt.command({"type": "sensor", "i": 1, "value": 5})["ok"] is False and rt.shared.slider_values[1] == 200.0
    rt.stop()

def test_test_commands_work_when_on(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path, "server.test_controls=true")
    assert rt.command({"type": "sim", "offline": True})["ok"] is True and rt.shared.force_offline is True
    assert rt.command({"type": "sensor", "i": 1, "value": 5}) is None and rt.shared.slider_values[1] == 5.0
    rt.stop()

def test_pi_profile_has_test_controls_off():
    assert settings.load("pi", load_env=False)["server"]["test_controls"] is False

def test_state_is_fast_with_many_long_chats(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path)
    for i in range(20):
        s, _ = rt.registry.sighting(PersonDetection(source="sim", where="center", distance="near", confidence=0.9, at=0),
                                    Pose(x_cm=i * 1000.0), 0.0, None)
        def add(sv):
            sv.chat += [ChatMessage(survivor_id=sv.id, role="survivor", text="help " * 40, source="typed") for _ in range(50)]
        rt.registry.update(s.id, add)
    st = rt.state(); assert len(st["survivors"]) == 20 and st["survivors"][0]["messages"] == 50
    t = time.perf_counter()
    for _ in range(50): rt.state()
    per = (time.perf_counter() - t) / 50
    assert per < 0.005, f"state() took {per*1000:.1f} ms"
    rt.stop()

def test_survivor_cache_refreshes_on_new_event(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path)
    assert rt.state()["survivors"] == []
    rt.registry.sighting(PersonDetection(source="sim", where="center", distance="near", confidence=0.9, at=0), Pose(), 0.0, None)
    assert len(rt.state()["survivors"]) == 1          # immediately, not after 0.5 s
    rt.stop()

def test_ping_echoes_time(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); rt = make(tmp_path)
    assert rt.command({"type": "ping", "t": 12.5}) == {"ok": True, "t": 12.5}
    rt.stop()

def test_record_then_replay(tmp_path, monkeypatch):
    import threading
    from scoutbot.hw.distance_fake import ReplayDistance
    from scoutbot.hw.camera_opencv import FolderCamera
    monkeypatch.chdir(tmp_path); rt = make(tmp_path, "record.enabled=true", "record.fps=20", f"record.dir={tmp_path / 'rec'}")
    th = threading.Thread(target=rt.record_loop, daemon=True); th.start()
    from robot.types import Sensors
    for i in range(6):
        with rt.shared.lock:
            rt.shared.raw_sensors = Sensors(left=100 + i, center=50, right=0, valid=(True, True, False), updated_at=time.monotonic())
            rt.shared.jpeg = open(__file__, "rb").read()[:10]; rt.shared.frame_seq += 1      # any bytes: we only check files appear
        time.sleep(0.07)
    rt.stop(); th.join(1)
    rec = tmp_path / "rec"; lines = (rec / "sensors.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 5 and list(rec.glob("*.jpg"))
    r = ReplayDistance(str(rec)).read()
    assert r.valid == (True, True, False) and 100 <= r.left <= 105 and r.center == 50
    assert ReplayDistance(str(tmp_path / "missing")).read().valid == (False, False, False)

def test_continue_search_suppresses_fuser_and_gate_paths(tmp_path, monkeypatch):
    """KI-38: raw detections enter Fuser, which suppresses only the handled person's brain and YOLO gate holds."""
    from robot.types import Action, SceneReport, Sensors
    from scoutbot.types import Mode
    monkeypatch.chdir(tmp_path); rt = make(tmp_path, "survivors.handled_s=60")
    near = PersonDetection(source="yolo", where="center", distance="near", confidence=0.9, at=0)
    survivor, _ = rt.registry.sighting(near, rt.pose.pose(), 0.0, None)
    assert rt.command({"type": "handled", "survivor_id": survivor.id})["ok"] is True
    now = time.monotonic(); raw_seen = []
    original_fuse = rt.fuser.fuse
    def record_fuse(scene, person, person_position=None, scene_position=None):
        raw_seen.append((person, person_position, scene_position))
        return original_fuse(scene, person, person_position, scene_position)
    monkeypatch.setattr(rt.fuser, "fuse", record_fuse)
    scene = SceneReport(path_ahead="clear", best_direction="center", terrain="flat", hazards=[], objects=[], confidence=0.9, notes="",
                        people={"visible": True, "where": "center", "distance": "near"})
    with rt.shared.lock:
        rt.shared.raw_sensors = Sensors(left=200, center=200, right=200, valid=(True, True, True), updated_at=now)
        rt.shared.detections = [near]; rt.shared.det_at = now; rt.shared.scene = scene; rt.shared.scene_at = now
        rt.shared.mode = Mode.AUTO
    rt.control_tick(now)
    assert raw_seen and raw_seen[-1][0] == near and rt.fuser.is_suppressed(raw_seen[-1][1])
    assert rt.shared.veto != "person ahead (YOLO)"           # Fuser suppression releases only the person hold
    assert rt.registry.get(survivor.id).handled_at is not None
    assert rt.command({"type": "handled", "survivor_id": "S-9999"})["ok"] is False
    rt.stop()


def test_continue_search_keeps_other_people_and_expires(tmp_path, monkeypatch):
    from robot.types import Action, SceneReport
    from scoutbot.types import Mode
    monkeypatch.chdir(tmp_path); rt = make(tmp_path, "survivors.handled_s=60")
    near = PersonDetection(source="yolo", where="center", distance="near", confidence=0.9, at=0)
    survivor, _ = rt.registry.sighting(near, rt.pose.pose(), 0.0, None)
    rt.command({"type": "handled", "survivor_id": survivor.id})
    now = time.monotonic(); scene = SceneReport(path_ahead="clear", best_direction="center", terrain="flat", hazards=[], objects=[], confidence=0.9, notes="",
                                                  people={"visible": False, "where": "none", "distance": "none"})
    rt.fuser.suppress(rt._handled_positions(now))
    handled_position = rt._detection_position(near)
    out = rt.fuser.fuse(scene, near, handled_position)
    assert out.people.visible is False
    assert rt.gate.check(Action.FORWARD, Mode.AUTO, 200, 200, 200, True, now,
                         yolo_person_near=not rt.fuser.is_suppressed(handled_position)).action == Action.FORWARD

    other_position = (handled_position[0] + 500, handled_position[1])
    out = rt.fuser.fuse(scene, near, other_position)
    assert out.people.visible is True
    assert rt.gate.check(Action.FORWARD, Mode.AUTO, 200, 200, 200, True, now,
                         yolo_person_near=not rt.fuser.is_suppressed(other_position)).action == Action.STOP

    rt.fuser.suppress(rt._handled_positions(now + 61))
    assert not rt.fuser.is_suppressed(handled_position)
    assert rt.gate.check(Action.FORWARD, Mode.AUTO, 200, 200, 200, True, now + 61,
                         yolo_person_near=not rt.fuser.is_suppressed(handled_position)).action == Action.STOP
    rt.stop()
