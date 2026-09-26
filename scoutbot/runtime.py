"""Starts every worker and runs the control loop (spec 3.3). The control loop is the ONLY thing that drives the motors,
and every action goes through the safety gate. The existing brain (robot/controller.py) is called unchanged."""
from __future__ import annotations
import json, threading, time
from pathlib import Path
import cv2
from robot.brain import Context, camera_note
from robot.camera_health import CameraHealth
from robot.config import DEFAULT
from robot.controller import Controller
from robot.types import Action, SceneReport, Sensors
from scoutbot.hw.base import build as build_hw
from scoutbot.perception.fusion import Fuser, fresh_person
from scoutbot.perception.yolo import PerceptionWorker
from scoutbot.safety.deadman import MotorWatchdog, link_check, manual_action
from scoutbot.safety.gate import Gate
from scoutbot.safety.modes import ModeController
from scoutbot.state import Bus, Shared
from scoutbot.survivors.mapping import MapBuilder
from scoutbot.survivors.pose import DeadReckoning
from scoutbot.survivors.registry import Registry
from scoutbot.types import DriveCommand, Mode, PersonDetection, utc_now

def _shrink(frame, width=640):
    h, w = frame.shape[:2]
    return cv2.resize(frame, (width, max(1, int(h * width / w)))) if w > width else frame

def static_scene() -> SceneReport:
    return SceneReport(path_ahead="clear", best_direction="center", terrain="flat", hazards=[],
                       people={"visible": False, "where": "none", "distance": "none"}, objects=[], confidence=0.9, notes="fake scene provider")

class Runtime:
    def __init__(self, cfg: dict, start_workers: bool = True):
        self.cfg = cfg; self.shared = Shared(); self.bus = Bus(); self._stop = threading.Event()
        sim_needed = cfg["hw"]["distance"] == "simworld" or cfg["scene"]["provider"] == "sim" or cfg["perception"]["yolo"]["where"] == "sim" or cfg["hw"]["camera"] == "synthetic"
        self.world = None
        if sim_needed:
            from scoutbot.hw.simworld import World
            self.world = World(cfg)
        self.camera, self.distance, self.motors = build_hw(cfg, self.shared, self.world)
        self.controller = Controller(DEFAULT); self.gate = Gate(DEFAULT, cfg["safety"].get("backup_max_s", 1.5))
        self.fuser = Fuser(); self.modes = ModeController(self.shared, self.bus); self.health = CameraHealth()
        self.watchdog = MotorWatchdog(self.motors, cfg["safety"].get("motor_watchdog_s", 0.5))
        self.pose = DeadReckoning(cfg, start=self.world.pose() if self.world else None)
        self.map = MapBuilder(sensor_angles=cfg["hw"].get("sensor_angles", (30, 0, -30)))   # [robot] wiring: KI-39
        data_dir = Path(cfg["survivors"].get("data_dir", "data")); data_dir.mkdir(parents=True, exist_ok=True)
        from scoutbot.sync import resolve_sinks
        from scoutbot.sync.outbox import Outbox, SyncWorker
        self.outbox = Outbox(data_dir, resolve_sinks(cfg))
        self.registry = Registry(cfg, self.bus, self.outbox, data_dir)
        from scoutbot.voice.speaker import Speaker
        self.voice = Speaker(cfg, self.shared)
        self.talk = None
        if cfg["talk"].get("enabled", True):
            from scoutbot.talk.worker import TalkWorker
            self.talk = TalkWorker(cfg, self.shared, self.bus, self.registry, self.voice)
        self.perception = PerceptionWorker(cfg, self.shared, self.world)
        from scoutbot.net import NetWorker
        self.net = NetWorker(cfg, self.shared, self.bus); self.sync = SyncWorker(cfg, self.shared, self.outbox)
        self.log_path = Path("logs"); self.log_path.mkdir(exist_ok=True); self.log_file = self.log_path / "scoutbot_run.jsonl"
        self._last_log = 0.0; self._last_tel = 0.0; self._det_seen = None; self._scene_seen = None
        self._surv_cache = None; self._surv_at = 0.0; self._surv_seq = 0
        self.handled: dict[str, float] = {}      # survivor id -> monotonic expiry of "Continue search" (KI-38)
        with self.shared.lock: self.shared.services["gemini_scene"] = cfg["scene"]["provider"]
        if start_workers: self.start()

    # ---------------- workers ----------------
    def start(self):
        if self.world: self.world.start()
        for fn, name in ((self.distance_loop, "distance"), (self.scene_loop, "scene"), (self.control_loop, "control"),
                         (self.survivor_loop, "survivors")):
            threading.Thread(target=fn, daemon=True, name=name).start()
        if self.cfg.get("record", {}).get("enabled"): threading.Thread(target=self.record_loop, daemon=True, name="record").start()
        self.watchdog.start(); self.perception.start(); self.voice.start(); self.net.start(); self.sync.start()
        if self.talk: self.talk.start()
        print(f"[scoutbot] profile={self.cfg['profile']} camera={self.cfg['hw']['camera']} distance={self.cfg['hw']['distance']} "
              f"motors={self.cfg['hw']['motors']} scene={self.cfg['scene']['provider']} yolo={self.cfg['perception']['yolo']['where']}", flush=True)

    def stop(self):
        self._stop.set()
        try: self.motors.stop()
        except Exception: pass
        for w in (self.watchdog, self.perception, self.voice, self.net, self.sync, self.talk, self.world):
            try:
                if w: w.stop()
            except Exception: pass
        self.registry.flush()
        for h in (self.camera, self.distance, self.motors):
            try: h.close()
            except Exception: pass

    def camera_loop(self):
        """Runs on the MAIN thread (macOS prefers camera capture there)."""
        misses = 0
        while not self._stop.is_set():
            f = self.camera.read()
            if f is None:
                misses += 1
                if misses == 50: print("[camera] no frames: check CAMERA_INDEX / camera permission", flush=True)
                with self.shared.lock: self.shared.cam_health = {"healthy": False, "reasons": ["no frames from camera"]}
                time.sleep(0.05); continue
            misses = 0; small = _shrink(f); ok, enc = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 80])
            now = time.monotonic(); h = self.health.update(small, now)
            with self.shared.lock:
                self.shared.frame = small; self.shared.jpeg = enc.tobytes() if ok else self.shared.jpeg
                self.shared.frame_at = now; self.shared.frame_seq += 1; self.shared.cam_health = h

    def distance_loop(self):
        while not self._stop.is_set():
            try: s = self.distance.read()
            except Exception as e:
                print("[distance] read failed:", e, flush=True); time.sleep(0.2); continue
            with self.shared.lock: self.shared.raw_sensors = s

    def scene_loop(self):
        prov = self.cfg["scene"]["provider"]; interval = self.cfg["scene"].get("interval_s", 2.0)
        describe = None
        if prov == "gemini":
            from robot.vlm import describe
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                if prov == "sim": rep = self.world.scene_report()
                elif prov == "fake": rep = static_scene()
                else:
                    with self.shared.lock: frame = self.shared.frame; healthy = self.shared.cam_health.get("healthy", False)
                    if not self.shared.online() or frame is None or not healthy:
                        self._stop.wait(0.5); continue          # offline or no usable frame: no Gemini call
                    rep = describe(frame.copy())
                lat = time.monotonic() - t0
                with self.shared.lock:
                    self.shared.scene = rep; self.shared.scene_at = time.monotonic(); self.shared.vlm_failures = 0
                    self.shared.vlm_error = ""; self.shared.vlm_latency = round(lat, 2); self.shared.vlm_calls += 1
            except Exception as e:
                with self.shared.lock:
                    self.shared.vlm_failures += 1; self.shared.vlm_error = f"{type(e).__name__}: {e}"[:300]
                print("[scene] Gemini error:", self.shared.vlm_error, flush=True)
            self._stop.wait(max(0.2, interval - (time.monotonic() - t0)))

    # ---------------- control ----------------
    def control_tick(self, now: float | None = None):
        now = time.monotonic() if now is None else now; cfg = self.cfg; sh = self.shared
        with sh.lock:
            raw = sh.raw_sensors.model_copy(); scene, scene_at = sh.scene, sh.scene_at
            dets, det_at = list(sh.detections), sh.det_at; mode = sh.mode; cmd = sh.drive_cmd; link_at = sh.link_at
            cam_h = sh.cam_health.get("healthy", False); failures = sh.vlm_failures
        online = sh.online(); prov = cfg["scene"]["provider"]
        raw.vlm_online = failures < 3 and (online or prov in ("sim", "fake"))
        cam_ok = cam_h or prov in ("sim", "fake")
        self.fuser.suppress(self._handled_positions(now))   # KI-38: Fuser owns handled-person suppression each tick
        person = fresh_person(dets, det_at, now, cfg["perception"]["yolo"].get("max_age_s", 1.0))
        person_position = self._detection_position(person) if person else None
        scene_position = self._scene_person_position(scene, now) if scene is not None and scene.people.visible else None
        fused = self.fuser.fuse(scene, person, person_position, scene_position)
        dec = self.controller.step(raw, fused, scene_at, cam_ok, now)
        lost = link_check(mode, link_at, now, cfg["safety"])
        if lost: self.modes.request(Mode.STOPPED, lost); mode = Mode.STOPPED
        if mode == Mode.AUTO: want = dec.action
        elif mode == Mode.MANUAL: want = manual_action(cmd, now, cfg["safety"].get("manual_cmd_valid_s", 0.3))
        else: want = Action.STOP
        L, C, R = dec.filtered.values()
        cam_usable = camera_note(raw, fused, now, scene_at, Context(DEFAULT, cam_ok)) == ""
        yolo_hold = person is not None and person.distance == "near" and not cam_usable and not self.fuser.is_suppressed(person_position)
        res = self.gate.check(want, mode, L, C, R, raw.fresh(now, DEFAULT.sensor_stale_s), now, yolo_hold)
        if mode == Mode.AUTO and res.veto and "blocked" in res.veto:
            print(f"[gate] vetoed AUTO {want.value}: {res.veto} (the brain should not have chosen this)", flush=True)
        self.motors.apply(res.action); self.watchdog.fed()
        wheels = self.motors.current(); pose = self.pose.update(wheels, now)
        true = self.world.pose() if self.world else None
        self.map.update(pose, (L, C, R), true)
        with sh.lock:
            sh.decision = {"action": dec.action.value, "rule": dec.rule, "reason": dec.reason, "notes": dec.notes, "stuck": dec.stuck,
                           "trace": [{"rule": s.rule, "name": s.name, "matched": s.matched, "applicable": s.applicable, "evidence": s.evidence,
                                      "fired": i == dec.fired} for i, s in enumerate(dec.steps)]}
            sh.final_action = res.action.value; sh.veto = res.veto; sh.filtered = [L, C, R]; sh.pose = pose; sh.true_pose = true
            sh.last_motor_apply = now; sh.watchdog_trips = self.watchdog.trips
            if self.world: sh.sim_contacts = self.world.contacts
        wall = time.time()
        if wall - self._last_log >= cfg["control"].get("log_every_s", 0.5):
            self._last_log = wall
            rec = {"time": wall, "mode": mode.value, "raw": [raw.left, raw.center, raw.right], "valid": list(raw.valid), "filtered": [L, C, R],
                   "scene_age": (now - scene_at) if scene_at else None, "person": person.model_dump() if person else None,
                   "brain": {"action": dec.action.value, "rule": dec.rule}, "final": res.action.value, "veto": res.veto,
                   "pose": pose.model_dump(), "online": online}
            with open(self.log_file, "a", encoding="utf-8") as f: f.write(json.dumps(rec) + "\n")
        hz = cfg["sync"].get("telemetry_hz", 1)
        if hz and wall - self._last_tel >= 1.0 / hz and self.outbox.sinks:
            self._last_tel = wall
            self.outbox.add_rows("telemetry", [{"time": utc_now(), "mode": mode.value, "action": res.action.value, "rule": dec.rule,
                                                "left_cm": L, "center_cm": C, "right_cm": R, "internet": online,
                                                "x_cm": pose.x_cm, "y_cm": pose.y_cm}])
        return res

    def control_loop(self):
        period = 1.0 / self.cfg["control"].get("hz", 10)
        while not self._stop.is_set():
            t0 = time.monotonic()
            try: self.control_tick(t0)
            except Exception as e:
                print("[control] tick failed, stopping motors:", repr(e), flush=True)
                try: self.motors.stop()
                except Exception: pass
            self._stop.wait(max(0.0, period - (time.monotonic() - t0)))

    # ---------------- recording (C15) ----------------
    def record_loop(self):
        """Saves camera frames (record.fps, default 2) and every sensor reading to data/recordings/<time>/ for replay:
        frames as NNNNNN.jpg (the folder camera plays them in order) and sensors.jsonl lines {t, raw, valid}."""
        rc = self.cfg.get("record", {}); fps = float(rc.get("fps", 2))
        out = Path(rc.get("dir") or Path(self.cfg["survivors"].get("data_dir", "data")) / "recordings" / time.strftime("%Y%m%d-%H%M%S"))
        out.mkdir(parents=True, exist_ok=True); self.record_dir = out
        print(f"[record] saving frames ({fps:g}/s) and sensor readings to {out}", flush=True)
        n = 0; last_seq = -1; last_frame = 0.0; last_sens = None
        with open(out / "sensors.jsonl", "a", encoding="utf-8") as f:
            while not self._stop.is_set():
                now = time.monotonic()
                with self.shared.lock: s = self.shared.raw_sensors; jpeg = self.shared.jpeg; seq = self.shared.frame_seq
                if s.updated_at and s.updated_at != last_sens:
                    last_sens = s.updated_at
                    f.write(json.dumps({"t": round(s.updated_at, 3), "raw": [s.left, s.center, s.right], "valid": list(s.valid)}) + "\n"); f.flush()
                if jpeg is not None and seq != last_seq and now - last_frame >= 1.0 / fps:
                    last_seq = seq; last_frame = now; n += 1
                    (out / f"{n:06d}.jpg").write_bytes(jpeg)
                self._stop.wait(0.05)

    # ---------------- continue search (KI-38) ----------------
    def _handled_positions(self, now: float) -> list[tuple[float, float, float]]:
        """(x, y, radius) of survivors a responder marked handled, still inside their hold time."""
        out = []
        for sid, until in list(self.handled.items()):
            if now > until: self.handled.pop(sid, None); continue
            s = self.registry.get(sid)
            if s: out.append((s.pose.x_cm, s.pose.y_cm, self.cfg["survivors"].get("merge_cm", 85) + 80.0))
        return out

    def _detection_position(self, det: PersonDetection) -> tuple[float, float]:
        return Registry.estimate(det, self.pose.pose(), self.cfg["survivors"])

    def _scene_person_position(self, scene, now: float) -> tuple[float, float] | None:
        if scene.people.distance not in ("near", "mid", "far"): return None
        where = scene.people.where if scene.people.where in ("left", "center", "right") else "center"
        return self._detection_position(PersonDetection(source="gemini", where=where, distance=scene.people.distance, confidence=1.0, at=now))

    # ---------------- survivors ----------------
    def survivor_loop(self):
        while not self._stop.is_set():
            time.sleep(0.1)
            with self.shared.lock:
                dets, det_at = list(self.shared.detections), self.shared.det_at
                scene, scene_at = self.shared.scene, self.shared.scene_at
                frame = None if self.shared.frame is None else self.shared.frame.copy()
                yolo = self.shared.det_status
            new_dets = []
            if dets and det_at != self._det_seen: self._det_seen = det_at; new_dets = dets
            # no working person detector: fall back to Gemini's people report (one sighting per new report)
            yolo_live = yolo in ("running", "sim") or yolo.startswith("remote")
            if not yolo_live and scene is not None and scene_at != self._scene_seen:
                self._scene_seen = scene_at
                if scene.people.visible:
                    new_dets = [PersonDetection(source="gemini", where=scene.people.where, distance=scene.people.distance, confidence=scene.confidence, at=scene_at)]
            used: set = set()                                 # two people in one frame are two survivors
            for d in new_dets:
                s, new = self.registry.sighting(d, self.pose.pose(), self.pose.odometer, frame, exclude=used)
                if s is None: continue                        # far and unknown: wait until the robot is closer
                used.add(s.id)
                if new:
                    print(f"[survivors] NEW {s.id} at ({s.pose.x_cm:.0f}, {s.pose.y_cm:.0f}) cm via {d.source}", flush=True)
                    if self.talk: self.talk.submit("new_survivor", s.id)

    # ---------------- commands from the dashboard ----------------
    def command(self, msg: dict) -> dict | None:
        t = msg.get("type"); sh = self.shared; now = time.monotonic()
        with sh.lock: sh.link_at = now                      # any message counts as a heartbeat
        if t == "heartbeat": return None
        if t == "ping": return {"ok": True, "t": msg.get("t")}     # the dashboard measures round-trip time
        if t == "estop": self.modes.estop(); self.motors.stop(); return {"ok": True}
        if t == "mode":
            m = Mode(msg["mode"]); self.modes.request(m, "responder")
            if m == Mode.STOPPED: self.motors.stop()
            return {"ok": True}
        if t == "drive":
            if self.modes.mode != Mode.MANUAL: return {"ok": False, "error": "take control first (MANUAL mode)"}
            with sh.lock: sh.drive_cmd = DriveCommand(action=Action(msg["action"]), seq=int(msg.get("seq", 0)), received_at=now)
            return None
        if t == "chat":
            sid = msg["survivor_id"]; text = str(msg.get("text", "")).strip()[:500]
            if not text or self.registry.get(sid) is None: return {"ok": False, "error": "unknown survivor or empty text"}
            if self.talk: self.talk.submit("survivor_says" if msg.get("role") == "survivor" else "responder_says", sid, text)
            return {"ok": True}
        if t == "retriage":
            if self.talk: self.talk.submit("retriage", msg["survivor_id"])
            return {"ok": True}
        if t == "handled":
            sid = msg.get("survivor_id", "")
            if self.registry.get(sid) is None: return {"ok": False, "error": "unknown survivor"}
            secs = float(self.cfg["survivors"].get("handled_s", 60))
            self.handled[sid] = now + secs
            self.registry.update(sid, lambda s: setattr(s, "handled_at", utc_now()))
            self.bus.publish("handled", {"survivor_id": sid, "for_s": secs})
            return {"ok": True}
        if t == "sim":
            if not self.cfg["server"].get("test_controls", False):
                return {"ok": False, "error": "test controls are off on this robot (server.test_controls: false)"}
            if "offline" in msg:
                with sh.lock: sh.force_offline = bool(msg["offline"])
                self.bus.publish("net", {"online": sh.online()})
            return {"ok": True}
        if t == "sensor":
            if not self.cfg["server"].get("test_controls", False) or self.cfg["hw"]["distance"] != "sliders":
                return {"ok": False, "error": "sensor sliders only work with test controls on and hw.distance: sliders"}
            i = int(msg["i"])
            with sh.lock:
                if "value" in msg: sh.slider_values[i] = float(msg["value"])
                if "valid" in msg: sh.slider_valid[i] = bool(msg["valid"])
            return None
        return {"ok": False, "error": f"unknown command {t}"}

    # ---------------- state for the dashboard ----------------
    def state(self) -> dict:
        sh = self.shared; now = time.monotonic()
        with sh.lock:
            raw = sh.raw_sensors; sc = sh.scene
            st = {
                "mode": sh.mode.value, "mode_reason": sh.mode_reason, "decision": {k: v for k, v in sh.decision.items() if k != "trace"},
                "trace": sh.decision.get("trace", []), "final_action": sh.final_action, "veto": sh.veto,
                "sensors": {"raw": [raw.left, raw.center, raw.right], "valid": list(raw.valid), "filtered": sh.filtered,
                            "age": round(now - raw.updated_at, 2) if raw.updated_at else None},
                "scene": sc.model_dump() if sc else None, "scene_age": round(now - sh.scene_at, 1) if sh.scene_at else None,
                "vlm": {"failures": sh.vlm_failures, "latency": sh.vlm_latency, "error": sh.vlm_error, "calls": sh.vlm_calls},
                "detections": [d.model_dump() for d in sh.detections] if sh.det_at and now - sh.det_at < 1.5 else [],
                "yolo": {"status": sh.det_status, "fps": sh.det_fps},
                "pose": sh.pose.model_dump(), "true_pose": sh.true_pose.model_dump() if sh.true_pose else None, "sim_contacts": sh.sim_contacts,
                "internet": sh.internet, "force_offline": sh.force_offline, "online": sh.internet and not sh.force_offline,
                "services": dict(sh.services), "sync": {k: dict(v) for k, v in sh.sync_status.items()},
                "camera": sh.cam_health,
                "deadman": {"motor_age": round(now - sh.last_motor_apply, 2) if sh.last_motor_apply else None, "trips": sh.watchdog_trips,
                            "link_age": round(now - sh.link_at, 2) if sh.link_at else None,
                            "link_timeout": self.cfg["safety"]["link_timeout_manual_s"] if sh.mode == Mode.MANUAL else self.cfg["safety"]["link_timeout_auto_s"]},
                "sliders": {"values": list(sh.slider_values), "valid": list(sh.slider_valid)},
            }
        st["survivors"] = self.survivor_rows()
        return st

    def survivor_rows(self, max_age_s: float = 0.5) -> list[dict]:
        """Cached survivor summaries (KI-08): rebuilt at most every 0.5 s, or at once after a survivor/chat/triage event."""
        now = time.monotonic()
        seq = self._bus_seq_of(("survivor", "chat", "triage"))
        if self._surv_cache is None or seq != self._surv_seq or now - self._surv_at >= max_age_s:
            self._surv_cache = self.registry.summaries(); self._surv_at = now; self._surv_seq = seq
        return self._surv_cache

    def _bus_seq_of(self, topics) -> int:
        for ev in reversed(self.bus.recent):
            if ev["topic"] in topics: return ev["seq"]
        return 0

    def hello(self) -> dict:
        return {"profile": self.cfg["profile"], "test_controls": self.cfg["server"].get("test_controls", False),
                "distance": self.cfg["hw"]["distance"], "world": self.world.layout() if self.world else None,
                "policy": {"stop_cm": DEFAULT.stop_cm, "slow_cm": DEFAULT.slow_cm, "side_near": DEFAULT.side_near}}
