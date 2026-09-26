"""Live test dashboard for the robot brain.  Run: python3 web_demo.py   then open http://localhost:8000
Shows the live camera, the exact frame sent to Gemini, Gemini's answer, mock ultrasonic sliders, and every decision."""
import argparse, json, os, random, threading, time
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import cv2
from dotenv import load_dotenv
load_dotenv(override=True)
from robot.types import Sensors
from robot.controller import Controller
from robot.camera_health import CameraHealth
from robot.metrics import Metrics
from robot.brain import evaluate, first_match
from robot.sim import random_sensors, random_scene
from robot.vlm import describe, shrink
from demo import canned

LOCK = threading.Lock()
CTRL = Controller(); HEALTH = CameraHealth(); MET = Metrics()

class St:
    def __init__(s):
        s.sensors = Sensors(); s.scene = None; s.scene_at = None; s.failures = 0; s.last_error = ""
        s.latency = None; s.calls = 0; s.offline_sim = False; s.fake_i = 0
        s.frame = None; s.jpeg = None; s.sent_jpeg = None; s.sent_at = 0; s.dark = False
        s.action = "STOP"; s.rule = 1; s.reason = "starting"; s.hist = []; s.vhist = []
        s.force = threading.Event(); s.trace = []; s.freeze = False
        s.notes = []; s.filtered = [None, None, None]; s.scene_used = None; s.rand_sensors = False; s.rand_scenes = False; s.rand_every = 1.0; s.rng = random.Random()
st = St()
ARGS = None

def state():
    now = time.monotonic()
    with LOCK:
        return {
            "sensors": {"vals": [st.sensors.left, st.sensors.center, st.sensors.right], "valid": list(st.sensors.valid)},
            "action": st.action, "rule": st.rule, "reason": st.reason,
            "camera": {"dark": st.dark, "health": HEALTH.last, "index": ARGS.camera if not ARGS.image else "image"},
            "vlm": {"online": st.failures < 3 and not st.offline_sim, "offline_sim": st.offline_sim, "failures": st.failures,
                    "error": st.last_error, "age": (now - st.scene_at) if st.scene_at else None, "latency": st.latency,
                    "calls": st.calls, "fake": ARGS.fake_vlm, "model": "fake" if ARGS.fake_vlm else os.getenv("GEMINI_MODEL", ""),
                    "report": st.scene.model_dump() if st.scene else None, "sent_at": st.sent_at, "fake_i": st.fake_i},
            "trace": st.trace, "freeze": st.freeze, "rand": {"sensors": st.rand_sensors, "scenes": st.rand_scenes, "every": st.rand_every},
            "hist": st.hist, "vhist": st.vhist, "metrics": MET.summary(), "notes": st.notes, "filtered": st.filtered, "scene_used": st.scene_used,
        }

def decision_loop():
    last = None; last_log = 0; Path("logs").mkdir(exist_ok=True)
    while True:
        now = time.monotonic()
        with LOCK:
            st.sensors.updated_at = now
            if st.freeze and st.scene is not None: st.scene_at = now   # frozen scene counts as current: no more AI calls
            st.sensors.vlm_online = st.failures < 3 and not st.offline_sim
            cam_ok = HEALTH.last["healthy"] or bool(ARGS.image) or bool(ARGS.fake_vlm and st.rand_scenes)
            bypass = st.freeze or (ARGS.fake_vlm and st.rand_scenes)
            raw_vals = [st.sensors.left if st.sensors.valid[0] else None, st.sensors.center if st.sensors.valid[1] else None, st.sensors.right if st.sensors.valid[2] else None]
            dec = CTRL.step(st.sensors.model_copy(), st.scene, st.scene_at, cam_ok, now, bypass_scene_filter=bypass)
            steps = dec.steps; fs = steps[dec.fired]; a, r, why = dec.action, dec.rule, dec.reason
            st.action, st.rule, st.reason = a.value, r, why; st.notes = dec.notes
            st.filtered = list(dec.filtered.values()); st.scene_used = dec.scene.model_dump() if dec.scene else None
            cam_fresh = st.scene_at is not None and now - st.scene_at <= 6 and st.sensors.vlm_online
            MET.tick(now, time.time(), raw_vals, dec, cam_fresh, cam_ok, CTRL.events["stuck"])
            fi = steps.index(fs)
            st.trace = [{"rule": x.rule, "name": x.name, "matched": x.matched, "applicable": x.applicable, "evidence": x.evidence,
                         "reached": i <= fi, "fired": i == fi, "action": x.action.value, "reason": x.reason} for i, x in enumerate(steps)]
            if (a.value, r, why) != last:
                st.hist.insert(0, {"t": time.strftime("%H:%M:%S"), "action": a.value, "rule": r, "reason": why, "sensors": [st.sensors.left, st.sensors.center, st.sensors.right]})
                del st.hist[40:]; last = (a.value, r, why)
            rec = {"time": time.time(), "sensors": st.sensors.model_dump(), "scene": st.scene.model_dump() if st.scene else None,
                   "scene_age": (now - st.scene_at) if st.scene_at else None, "action": a.value, "rule": r}
        if time.time() - last_log >= 0.5:
            with open("logs/web_run.jsonl", "a") as f: f.write(json.dumps(rec) + "\n")
            last_log = time.time()
        time.sleep(0.1)

def vlm_loop():
    while True:
        t_start = time.time()
        with LOCK:
            frame = None if st.frame is None else st.frame.copy(); dark = st.dark
        if frame is not None and not dark and not st.freeze and not (ARGS.fake_vlm and st.rand_scenes):
            ok, enc = cv2.imencode(".jpg", shrink(frame))
            with LOCK:
                st.sent_jpeg = enc.tobytes(); st.sent_at = time.time(); fake_i = st.fake_i
            try:
                rep = canned(fake_i) if ARGS.fake_vlm else describe(frame)
                lat = time.time() - t_start
                with LOCK:
                    st.scene = rep; st.scene_at = time.monotonic(); st.failures = 0; st.last_error = ""; st.latency = lat; st.calls += 1; MET.vlm(True, lat)
                    st.vhist.insert(0, {"t": time.strftime("%H:%M:%S"), "latency": round(lat, 2), "path_ahead": rep.path_ahead, "terrain": rep.terrain,
                                        "objects": rep.objects, "notes": rep.notes})
                    del st.vhist[20:]
            except Exception as e:
                with LOCK:
                    st.failures += 1; MET.vlm(False); st.last_error = f"{type(e).__name__}: {e}"[:400]
                print("VLM ERROR:", st.last_error, flush=True)
        st.force.wait(timeout=max(0.3, ARGS.interval - (time.time() - t_start))); st.force.clear()

def rand_loop():
    while True:
        time.sleep(0.1)
        if not (st.rand_sensors or st.rand_scenes): continue
        with LOCK:
            if st.rand_sensors:
                r = random_sensors(st.rng); st.sensors.left, st.sensors.center, st.sensors.right, st.sensors.valid = r.left, r.center, r.right, r.valid
            if st.rand_scenes and ARGS.fake_vlm:
                sc = random_scene(st.rng); st.scene = sc; st.scene_at = time.monotonic(); st.failures = 0; st.calls += 1; st.latency = 0.0
                st.vhist.insert(0, {"t": time.strftime("%H:%M:%S"), "latency": 0.0, "path_ahead": sc.path_ahead, "terrain": sc.terrain, "objects": sc.objects, "notes": sc.notes}); del st.vhist[20:]
            every = st.rand_every
        time.sleep(every)

def batch(n, seed):
    rng = random.Random(seed); rows = []
    for _ in range(n):
        s = random_sensors(rng, 10.0); sc = None if rng.random() < 0.1 else random_scene(rng)
        f = first_match(evaluate(s, sc, 10.0, None if sc is None else 10.0))
        scene = None if sc is None else {"path": sc.path_ahead, "terrain": sc.terrain, "best": sc.best_direction,
                 "hazards": [f"{h.type} {h.where}/{h.distance}" for h in sc.hazards],
                 "person": f"{sc.people.where}/{sc.people.distance}" if sc.people.visible else None}
        rows.append({"sensors": list(s.values()), "scene": scene, "action": f.action.value, "rule": f.rule, "reason": f.reason})
    return rows

def handle_cmd(d):
    t = d.get("type")
    with LOCK:
        if t == "sensor":
            i = int(d["i"]); names = ["left", "center", "right"]
            if "value" in d: setattr(st.sensors, names[i], float(d["value"]))
            if "valid" in d:
                v = list(st.sensors.valid); v[i] = bool(d["valid"]); st.sensors.valid = tuple(v)
        elif t == "preset":
            st.sensors.left, st.sensors.center, st.sensors.right = [float(x) for x in d["values"]]
            st.sensors.valid = tuple(bool(x) for x in d.get("valid", [True, True, True]))
        elif t == "freeze": st.freeze = bool(d["on"]) and st.scene is not None
        elif t == "offline": st.offline_sim = bool(d["on"])
        elif t == "fake": st.fake_i = int(d["i"])
        elif t == "rand":
            st.rand_sensors = bool(d.get("sensors", st.rand_sensors)); st.rand_scenes = bool(d.get("scenes", st.rand_scenes)); st.rand_every = float(d.get("every", st.rand_every))
    if t in ("force", "fake"): st.force.set()

HTML = open(Path(__file__).with_name("dashboard.html"), encoding="utf-8").read()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, ctype, body):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/": self._send(200, "text/html; charset=utf-8", HTML.encode())
        elif p == "/state": self._send(200, "application/json", json.dumps(state()).encode())
        elif p == "/batch":
            q = parse_qs(urlparse(self.path).query); self._send(200, "application/json", json.dumps(batch(min(int(q.get("n", ["25"])[0]), 100), int(q.get("seed", ["0"])[0]))).encode())
        elif p == "/sent.jpg":
            with LOCK: b = st.sent_jpeg
            self._send(200, "image/jpeg", b) if b else self._send(404, "text/plain", b"none yet")
        elif p == "/video":
            self.send_response(200); self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame"); self.end_headers()
            try:
                while True:
                    with LOCK: b = st.jpeg
                    if b: self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(b) + b + b"\r\n")
                    time.sleep(0.06)
            except (BrokenPipeError, ConnectionResetError): pass
        else: self._send(404, "text/plain", b"not found")
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try: handle_cmd(json.loads(self.rfile.read(n) or b"{}")); self._send(200, "application/json", b"{}")
        except Exception as e: self._send(400, "text/plain", str(e).encode())

def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake-vlm", action="store_true"); ap.add_argument("--random-sensors", action="store_true"); ap.add_argument("--random-scenes", action="store_true"); ap.add_argument("--image")
    ap.add_argument("--camera", type=int, default=int(os.getenv("CAMERA_INDEX", "0")))
    ap.add_argument("--port", type=int, default=8000); ap.add_argument("--interval", type=float, default=2.0)
    ARGS = ap.parse_args()
    image = cv2.imread(ARGS.image) if ARGS.image else None
    cap = None if image is not None else cv2.VideoCapture(ARGS.camera)
    if cap is not None:
        for _ in range(30): cap.read(); time.sleep(0.03)   # macOS webcams start black
    st.rand_sensors, st.rand_scenes = ARGS.random_sensors, ARGS.random_scenes
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.port), H)
    for fn in (srv.serve_forever, decision_loop, vlm_loop, rand_loop): threading.Thread(target=fn, daemon=True).start()
    print(f"Dashboard: http://localhost:{ARGS.port}   (Ctrl-C to stop)", flush=True)
    try:
        while True:   # camera capture stays on the main thread (macOS likes that)
            if image is not None: f = image.copy(); time.sleep(0.05)
            else:
                ok, f = cap.read()
                if not ok: time.sleep(0.05); continue
            ok2, enc = cv2.imencode(".jpg", shrink(f), [cv2.IMWRITE_JPEG_QUALITY, 80])
            with LOCK: st.frame = f; st.jpeg = enc.tobytes(); HEALTH.update(f, time.monotonic()); st.dark = image is None and not HEALTH.last["healthy"]
    except KeyboardInterrupt: pass

if __name__ == "__main__": main()
