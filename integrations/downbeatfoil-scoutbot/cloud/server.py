"""scoutbot cloud: the robot's home on the internet (runs on the vultr box).

The pi sits behind a phone hotspot, so it can't be reached from outside. Instead it dials out
to /robot here and keeps one websocket open. Over it the pi pushes its state a few times a
second and camera jpegs as binary messages; we relay dashboard requests back down the same
socket. The dashboard is the same single file the pi serves, so it works unchanged: /api/state
and /stream come from what the pi pushed, every other /api/* call is tunnelled to the pi.

Everything the robot sends is also ingested into sqlite (telemetry at 1 hz, events, survivors,
a camera snapshot every few seconds) so there's a record after the robot is gone.

Run:  uvicorn server:app --host 127.0.0.1 --port 8080   (caddy in front for https)
Env:  ROBOT_TOKEN (the pi's key), SITE_TOKEN (dashboard password: open /?token=...), DATA_DIR
"""
import asyncio
import base64
import hmac
import itertools
import json
import os
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
DASHBOARD = HERE / "dashboard"
DATA = Path(os.getenv("DATA_DIR", HERE / "data"))
FRAMES = DATA / "frames"
ROBOT_TOKEN = os.getenv("ROBOT_TOKEN", "")
SITE_TOKEN = os.getenv("SITE_TOKEN", "")
SNAP_EVERY_S = float(os.getenv("SNAP_EVERY_S", 5))
STALE_S = 5  # no state for this long = the robot is gone

FRAMES.mkdir(parents=True, exist_ok=True)
db = sqlite3.connect(DATA / "scout.db", check_same_thread=False, isolation_level=None)
db.execute("pragma journal_mode=wal")
db.executescript("""
create table if not exists telemetry (
  t real, mode text, auto_state text, x real, y real, heading real,
  sonar_left real, sonar_right real, temp_c real, humidity real, heard_sound int,
  camera_ok int, fps real, people int, cpu_c real, low_power int, raw text);
create index if not exists telemetry_t on telemetry(t);
create table if not exists events (t real, msg text, unique(t, msg));
create table if not exists survivors (id text primary key, updated real, doc text);
create table if not exists frames (t real, path text);
""")


class Robot:
    """The one live connection to the pi, plus the latest things it told us."""

    def __init__(self):
        self.ws = None
        self.state = None
        self.state_t = 0.0
        self.frame = None
        self.frame_id = 0
        self.connected_t = 0.0
        self.pending = {}  # tunnelled request id -> future
        self.ids = itertools.count(1)
        self.last_row_t = 0.0
        self.last_snap_t = 0.0

    def live(self):
        return self.ws is not None and time.time() - self.state_t < STALE_S


robot = Robot()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


# ---- auth: the dashboard can drive motors, so it's never open to the whole internet ----

def _ok(given, expected):
    return bool(expected) and bool(given) and hmac.compare_digest(given, expected)


@app.middleware("http")
async def site_auth(request: Request, call_next):
    if not SITE_TOKEN or request.url.path in ("/healthz",):
        return await call_next(request)
    q = request.query_params.get("token")
    if _ok(q, SITE_TOKEN):
        # swap the link token for a cookie so it doesn't sit in the address bar
        resp = await call_next(request) if request.url.path != "/" else FileResponse(
            DASHBOARD / "index.html", headers={"Cache-Control": "no-store"})
        resp.set_cookie("sb", SITE_TOKEN, httponly=True, samesite="strict", max_age=7 * 86400)
        return resp
    if _ok(request.cookies.get("sb"), SITE_TOKEN):
        return await call_next(request)
    if request.url.path == "/":
        return HTMLResponse("<p style='font:16px sans-serif'>scoutbot: open the link with ?token=...</p>", 401)
    return PlainTextResponse("unauthorized", 401)


# ---- ingest ----

def ingest_state(s):
    now = time.time()
    if now - robot.last_row_t >= 1.0:  # 1 hz is plenty for a record and keeps the db small
        robot.last_row_t = now
        d, e, p, pi = s["sonars"]["dist"], s["env"], s["motors"]["pose"], s.get("pi") or {}
        db.execute("insert into telemetry values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            now, s["mode"], s["auto"]["state"], p["x"], p["y"], p["heading"],
            d.get("left"), d.get("right"), e.get("temp_c"), e.get("humidity"), int(bool(e.get("heard_sound"))),
            int(bool(s["camera_ok"])), s["detector"]["fps"], len(s["detector"]["detections"]),
            pi.get("cpu_c"), int(bool(pi.get("low_power"))), json.dumps(s)))
    for ev in s.get("events", []):
        db.execute("insert or ignore into events values (?,?)", (ev["t"], ev["msg"]))
    for v in s.get("victims", []):
        doc = json.dumps(v, sort_keys=True)
        db.execute("insert into survivors values (?,?,?) on conflict(id) do update set updated=excluded.updated, doc=excluded.doc "
                   "where survivors.doc != excluded.doc", (v["id"], now, doc))


def ingest_frame(jpg):
    now = time.time()
    if now - robot.last_snap_t < SNAP_EVERY_S:
        return
    robot.last_snap_t = now
    day = FRAMES / time.strftime("%Y%m%d", time.gmtime(now))
    day.mkdir(exist_ok=True)
    path = day / (time.strftime("%H%M%S", time.gmtime(now)) + ".jpg")
    path.write_bytes(jpg)
    db.execute("insert into frames values (?,?)", (now, str(path.relative_to(DATA))))


# ---- the pi's end ----

@app.websocket("/robot")
async def robot_socket(ws: WebSocket):
    if not _ok(ws.query_params.get("token") or ws.headers.get("x-robot-token"), ROBOT_TOKEN):
        await ws.close(code=4401)
        return
    await ws.accept()
    if robot.ws is not None:  # a reconnect replaces a half-dead old socket
        try:
            await robot.ws.close()
        except Exception:
            pass
    robot.ws, robot.connected_t = ws, time.time()
    print("[cloud] robot connected", flush=True)
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                robot.frame, robot.frame_id = msg["bytes"], robot.frame_id + 1
                ingest_frame(msg["bytes"])
                continue
            m = json.loads(msg["text"])
            if m["type"] == "state":
                robot.state, robot.state_t = m["data"], time.time()
                ingest_state(m["data"])
            elif m["type"] == "resp":
                fut = robot.pending.pop(m["id"], None)
                if fut and not fut.done():
                    fut.set_result(m)
    except WebSocketDisconnect:
        pass
    finally:
        if robot.ws is ws:
            robot.ws = None
        for fut in robot.pending.values():
            if not fut.done():
                fut.set_exception(ConnectionError("robot disconnected"))
        robot.pending.clear()
        print("[cloud] robot disconnected", flush=True)


async def tunnel(method, path, body=b"", timeout=6.0):
    """Run one http request on the pi's own api and return its answer."""
    if not robot.live():
        return PlainTextResponse("robot offline", 503)
    rid = next(robot.ids)
    fut = asyncio.get_running_loop().create_future()
    robot.pending[rid] = fut
    await robot.ws.send_text(json.dumps({"type": "req", "id": rid, "method": method, "path": path,
                                         "body": body.decode("utf-8", "replace")}))
    try:
        r = await asyncio.wait_for(fut, timeout)
    except (asyncio.TimeoutError, ConnectionError):
        robot.pending.pop(rid, None)
        return JSONResponse({"detail": "the robot didn't answer"}, 504)
    return Response(base64.b64decode(r["body"]), r["status"], media_type=r.get("ctype"))


# ---- the dashboard's end ----

@app.get("/healthz")
def healthz():
    return {"ok": True, "robot": robot.live()}


@app.get("/")
def index():
    return FileResponse(DASHBOARD / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/state")
def state():
    if not robot.live():
        return PlainTextResponse("robot offline", 503)  # not json on purpose: the dashboard shows "offline"
    return JSONResponse(dict(robot.state, cloud={"linked_s": round(time.time() - robot.connected_t)}),
                        headers={"Cache-Control": "no-store"})


@app.get("/stream")
async def stream():
    async def gen():
        last = 0
        while True:
            if robot.frame_id != last and robot.frame is not None:
                last = robot.frame_id
                yield b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + robot.frame + b"\r\n"
            await asyncio.sleep(0.03)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=f")


@app.get("/api/history")
def history(minutes: float = 10):
    """The ingested record, newest last. Handy for checking the pipeline end to end."""
    since = time.time() - minutes * 60
    cols = ["t", "mode", "auto_state", "x", "y", "heading", "sonar_left", "sonar_right", "temp_c", "humidity",
            "heard_sound", "camera_ok", "fps", "people", "cpu_c", "low_power"]
    rows = db.execute(f"select {','.join(cols)} from telemetry where t > ? order by t", (since,)).fetchall()
    counts = {k: db.execute(f"select count(*) from {k}").fetchone()[0] for k in ("telemetry", "events", "survivors", "frames")}
    return {"counts": counts, "telemetry": [dict(zip(cols, r)) for r in rows]}


@app.api_route("/api/{rest:path}", methods=["GET", "POST"])
async def relay(rest: str, request: Request):
    path = "/api/" + rest + (("?" + request.url.query) if request.url.query else "")
    return await tunnel(request.method, path, await request.body())


app.mount("/static", StaticFiles(directory=DASHBOARD), name="static")
