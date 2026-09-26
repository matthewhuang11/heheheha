"""FastAPI robot server (spec 7). The responder opens http://<robot-ip>:8000 on the laptop.
One WebSocket carries state (pushed ~10 Hz) and commands (heartbeat, mode, estop, drive, chat, retriage, sim, sensor).
Optional SCOUTBOT_TOKEN in .env: then every request needs ?token=<it>."""
from __future__ import annotations
import asyncio, os, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from scoutbot.types import PersonDetection

STATIC = Path(__file__).resolve().parent / "static"

def create_app(rt) -> FastAPI:
    app = FastAPI(title="scoutbot", docs_url="/docs")
    token = os.getenv("SCOUTBOT_TOKEN", "").strip()
    snap_dir = (Path(rt.cfg["survivors"].get("data_dir", "data")) / "snapshots").resolve()

    def auth(tok: str | None):
        if token and tok != token: raise HTTPException(401, "missing or wrong token")

    @app.get("/", response_class=HTMLResponse)
    def index(token: str | None = None):
        auth(token); return HTMLResponse((STATIC / "responder.html").read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})

    @app.get("/video.mjpg")
    def video(token: str | None = None):
        auth(token)
        def gen():
            last = None
            while True:
                with rt.shared.lock: b = rt.shared.jpeg
                if b is not None and b is not last:
                    last = b; yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(b)).encode() + b"\r\n\r\n" + b + b"\r\n"
                time.sleep(1 / 15)
        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/snapshot.jpg")
    def snapshot(token: str | None = None):
        auth(token)
        with rt.shared.lock: b = rt.shared.jpeg
        if b is None: raise HTTPException(404, "no frame yet")
        return Response(b, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/snapshots/{name}")
    def snap(name: str, token: str | None = None):
        auth(token); p = (snap_dir / name).resolve()
        if p.parent != snap_dir or not p.exists(): raise HTTPException(404)
        return FileResponse(p, media_type="image/jpeg")

    @app.get("/api/survivors")
    def survivors(token: str | None = None):
        auth(token); return [s.model_dump() for s in rt.registry.all()]

    @app.get("/api/survivors/{sid}")
    def survivor(sid: str, token: str | None = None):
        auth(token); s = rt.registry.get(sid)
        if s is None: raise HTTPException(404)
        return s.model_dump()

    @app.get("/api/map")
    def map_(token: str | None = None):
        auth(token); m = rt.map.snapshot()
        m["world"] = rt.world.layout() if rt.world else None
        return m

    @app.post("/api/detections")
    async def detections(req: Request, token: str | None = None):
        """The remote YOLO worker (laptop) posts confirmed detections here (perception.yolo.where = remote)."""
        auth(token); body = await req.json(); now = time.monotonic()
        dets = [PersonDetection(**{**d, "at": now}) for d in body.get("detections", [])]
        with rt.shared.lock:
            rt.shared.detections = dets; rt.shared.det_at = now; rt.shared.det_fps = body.get("fps")
            rt.shared.det_status = "remote (laptop worker)"
        return {"ok": True}

    @app.get("/api/health")
    def health(token: str | None = None):
        auth(token); st = rt.state()
        return {"profile": rt.cfg["profile"], "uptime_s": round(time.monotonic() - rt.shared.started, 1), "mode": st["mode"],
                "services": st["services"], "sync": st["sync"], "yolo": st["yolo"], "online": st["online"], "deadman": st["deadman"]}

    @app.get("/api/state")
    def state(token: str | None = None):
        auth(token); return JSONResponse(rt.state())

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        if token and sock.query_params.get("token") != token: await sock.close(code=4401); return
        await sock.accept(); q = rt.bus.subscribe(); hz = rt.cfg["server"].get("state_hz", 10)
        await sock.send_json({"type": "hello", **rt.hello()})

        async def sender():
            while True:
                await sock.send_json({"type": "state", **rt.state()})
                while not q.empty():
                    ev = q.get_nowait(); await sock.send_json({"type": "event", **ev})
                await asyncio.sleep(1 / hz)

        async def receiver():
            while True:
                msg = await sock.receive_json()
                try: reply = rt.command(msg)
                except Exception as e: reply = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                if reply is not None: await sock.send_json({"type": "reply", "for": msg.get("type"), **reply})

        tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except WebSocketDisconnect: pass
        finally:
            for t in tasks: t.cancel()
            rt.bus.unsubscribe(q)
    return app
