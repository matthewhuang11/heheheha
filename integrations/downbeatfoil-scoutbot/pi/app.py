"""ScoutBot server: video stream, driving, autonomy, survivor log, and HQ sync.

Run:  uvicorn app:app --host 0.0.0.0 --port 8000
Open: http://<pi-ip>:8000
"""
import subprocess
import threading
import time

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import brain
import config
import voice
from autonomy import Autonomy
from camera import Camera
from detector import Detector, draw
from motors import Drive
from sensors import Sonars
from senses import Senses
from victims import SNAPS, VictimLog

DASHBOARD = config.ROOT.parent / "dashboard" / "index.html"
events = []  # short rolling feed shown on the dashboard


def event(msg):
    events.append({"t": time.time(), "msg": msg})
    del events[:-40]
    print(f"[event] {msg}")


camera = Camera()
detector = Detector(camera)
drive = Drive()
sonars = Sonars()
senses = Senses()
log = VictimLog()
auto = Autonomy(drive, sonars, detector, camera, log, event, senses)


def _victim_loop():
    """Feed detections into the survivor log."""
    last = None
    while True:
        dets = detector.detections
        if dets is not last:
            last = dets
            frame, _ = camera.latest()
            vid = log.update(dets, drive.pose(), frame)
            if vid:
                log.patch(vid, env=senses.snapshot())
                senses.buzzer.beep(2)
                event(f"survivor {vid} found and saved on the robot")
        time.sleep(0.05)


def scene(vid):
    """The whole frame when we have it: gemini needs the surroundings to judge hazards."""
    full = SNAPS / f"{vid}_full.jpg"
    return full if full.exists() else SNAPS / f"{vid}.jpg"


def _ready_for_hq(v):
    # wait until the robot has finished talking to them, or they were only seen in passing
    if v["status"] != "pending" or auto.contact_vid == v["id"] and auto.state == "contact":
        return False
    return v["contacted"] or time.time() - v["found_at"] > 20


def _sync_loop():
    """Store-and-forward: the moment we're back in range, hand everything to HQ."""
    while True:
        time.sleep(3)
        if brain.blackout():
            continue
        for v in log.all():
            if not _ready_for_hq(v):
                continue
            audio = voice.AUDIO_DIR / v["audio"] if v["audio"] else None
            out = brain.process_victim(v, scene(v["id"]), audio)
            log.patch(v["id"], status="processed", **out)
            event(f"survivor {v['id']} triaged ({out['report_source']})")


threading.Thread(target=_victim_loop, daemon=True).start()
threading.Thread(target=_sync_loop, daemon=True).start()
app = FastAPI()
app.mount("/static", StaticFiles(directory=DASHBOARD.parent), name="static")


@app.get("/")
def index():
    # never cache: a redeploy should show up on the next refresh, not the next day
    return FileResponse(DASHBOARD, headers={"Cache-Control": "no-store"})


@app.get("/stream")
def stream(fps: float = 0):
    """mjpeg of the camera with detection boxes. ?fps= caps the rate (the cloud link uses it: less jpeg work)."""
    def gen():
        last, sent = 0, 0.0
        while True:
            frame, fid = camera.latest()
            if frame is None or fid == last or (fps and time.time() - sent < 1 / fps):
                time.sleep(0.02)
                continue
            last, sent = fid, time.time()
            ok, jpg = cv2.imencode(".jpg", draw(frame, detector.detections), [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                yield b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=f")


_pi = {"t": 0.0, "val": {}}


def pi_health():
    """cpu temp and power state, cached a few seconds (vcgencmd is a subprocess)."""
    if time.time() - _pi["t"] > 5:
        val = {"cpu_c": None, "low_power": None}
        try:
            val["cpu_c"] = round(int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000, 1)
            out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2).stdout
            val["low_power"] = bool(int(out.split("=")[1], 16) & 0x1)  # bit 0: under-voltage right now
        except Exception:
            pass  # laptop sim: no pi sensors
        _pi.update(t=time.time(), val=val)
    return _pi["val"]


@app.get("/api/state")
def state():
    return {
        "mode": brain.mode(),
        "camera_ok": camera.ok,
        "detector": {"fps": detector.fps, "error": detector.error, "detections": detector.detections},
        "motors": {"sim": drive.sim, "pose": drive.pose()},
        "sonars": {"sim": sonars.sim, "dist": sonars.dist},
        "env": senses.snapshot(),
        "pi": pi_health(),
        "auto": auto.status(),
        "victims": log.all(),
        "events": events[-12:],
    }


# ---- driving ----

class DriveCmd(BaseModel):
    throttle: float
    turn: float


@app.post("/api/drive")
def drive_cmd(c: DriveCmd):
    auto.manual()  # a human touching the controls always wins
    drive.set(c.throttle, c.turn)
    return {"ok": True}


@app.post("/api/stop")
def stop():
    auto.manual()
    drive.stop()
    return {"ok": True}


@app.post("/api/reset")
def reset():
    auto.manual()
    drive.reset_pose()
    log.clear()
    event("map and survivors cleared")
    return {"ok": True}


# ---- mission ----

@app.post("/api/mission/start")
def mission_start():
    """Go dark and search on our own: the demo's 'send it into the building' moment."""
    drive.reset_pose()
    brain.set_blackout(True)
    auto.start()
    event("blackout: no connection, robot is on its own")
    return {"ok": True}


@app.post("/api/mission/return")
def mission_return():
    auto.go_home()
    return {"ok": True}


@app.post("/api/mission/end")
def mission_end():
    """Back in range: reconnect and let the sync loop dump everything to HQ."""
    auto.manual()
    brain.set_blackout(False)
    event("back in range: syncing with HQ")
    return {"ok": True}


class Toggle(BaseModel):
    on: bool


@app.post("/api/blackout")
def blackout(t: Toggle):
    brain.set_blackout(t.on)
    event("blackout on" if t.on else "blackout off: syncing with HQ")
    return {"ok": True}


# ---- survivors ----

def _victim_or_404(vid):
    v = log.get(vid)
    if not v:
        raise HTTPException(404, "no such survivor")
    return v


@app.post("/api/victims/{vid}/contact")
def contact(vid: str):
    """Manually trigger the talk-and-record routine (when driving by hand)."""
    _victim_or_404(vid)
    drive.stop()
    threading.Thread(target=auto._contact, args=(vid,), daemon=True).start()
    return {"ok": True}


@app.post("/api/victims/{vid}/report")
def report(vid: str):
    v = _victim_or_404(vid)
    if brain.blackout():
        raise HTTPException(409, "robot is in blackout; reports are written once it's back in range")
    audio = voice.AUDIO_DIR / v["audio"] if v["audio"] else None
    out = brain.process_victim(v, scene(vid), audio)
    event(f"survivor {vid} re-triaged ({out['report_source']})")
    return log.patch(vid, status="processed", **out)


class Say(BaseModel):
    text: str


@app.post("/api/victims/{vid}/heard")
def heard(vid: str, s: Say):
    """Typed survivor reply (online chat). Returns the robot's answer."""
    v = _victim_or_404(vid)
    convo = v["conversation"] + [{"role": "victim", "text": s.text}]
    text, src = brain.reply_to_victim(dict(v, conversation=convo))
    event(f"robot to {vid} ({src}): {text}")
    return log.patch(vid, conversation=convo + [{"role": "robot", "text": text}])


@app.get("/api/victims/{vid}/snap")
def snap(vid: str):
    p = SNAPS / f"{vid}.jpg"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/victims/{vid}/audio")
def audio(vid: str):
    v = _victim_or_404(vid)
    if not v["audio"] or not (voice.AUDIO_DIR / v["audio"]).exists():
        raise HTTPException(404)
    return FileResponse(voice.AUDIO_DIR / v["audio"], media_type="audio/wav")
