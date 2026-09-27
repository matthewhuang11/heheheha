"""Link the robot to the cloud dashboard (runs next to app.py as its own service).

The pi can't be reached from the internet (it's behind a phone hotspot), so this dials out to
the cloud server and holds one websocket open:
  up:   /api/state a few times a second, and camera jpegs (with the detection overlay) as binary
  down: dashboard requests, which we replay against our own api on localhost and answer

Everything goes through the robot's own api, so the dead-man stop, "a human touching the
controls always wins", and every other safety rule still apply to remote driving. If the link
drops mid-drive the drive commands stop arriving and the 0.5 s dead-man halts the motors.

Env (pi/.env): CLOUD_URL (e.g. ws://45.76.60.159/robot), CLOUD_TOKEN, CLOUD_FPS, CLOUD_STATE_HZ
"""
import asyncio
import base64
import json
import os
import time

import httpx
import websockets
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("CLOUD_URL", "")
TOKEN = os.getenv("CLOUD_TOKEN", "")
FPS = float(os.getenv("CLOUD_FPS", 5))
STATE_HZ = float(os.getenv("CLOUD_STATE_HZ", 4))
LOCAL = os.getenv("ROBOT_API", "http://127.0.0.1:8000")  # only overridden to test off the pi


async def push_state(ws, http):
    while True:
        try:
            r = await http.get("/api/state")
            if r.status_code == 200:
                await ws.send(json.dumps({"type": "state", "data": r.json()}))
        except httpx.HTTPError:
            pass  # app.py restarting; the cloud shows "offline" after a few seconds
        await asyncio.sleep(1 / STATE_HZ)


async def push_video(ws, http):
    """Re-send frames from our own mjpeg stream, capped to FPS to spare the hotspot."""
    while True:
        try:
            async with http.stream("GET", f"/stream?fps={FPS}", timeout=httpx.Timeout(10, read=15)) as r:
                buf, last = b"", 0.0
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    while True:
                        a = buf.find(b"\xff\xd8")
                        b = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
                        if b < 0:
                            buf = buf[a:] if a > 0 else buf
                            break
                        jpg, buf = buf[a:b + 2], buf[b + 2:]
                        if time.monotonic() - last >= 1 / FPS:
                            last = time.monotonic()
                            await ws.send(jpg)
        except httpx.HTTPError:
            await asyncio.sleep(2)  # camera or app.py not up yet


async def serve_requests(ws, http):
    async for msg in ws:
        if isinstance(msg, bytes):
            continue
        m = json.loads(msg)
        if m.get("type") != "req" or not m["path"].startswith("/api/"):
            continue  # only ever touch our own api
        asyncio.create_task(answer(ws, http, m))


async def answer(ws, http, m):
    try:
        body = m.get("body") or None
        r = await http.request(m["method"], m["path"], content=body,
                               headers={"Content-Type": "application/json"} if body else None)
        out = {"status": r.status_code, "ctype": r.headers.get("content-type"), "body": base64.b64encode(r.content).decode()}
    except httpx.HTTPError as e:
        out = {"status": 502, "ctype": "application/json", "body": base64.b64encode(json.dumps({"detail": str(e)}).encode()).decode()}
    await ws.send(json.dumps({"type": "resp", "id": m["id"], **out}))


async def main():
    if not URL or not TOKEN:
        print("[cloud] CLOUD_URL / CLOUD_TOKEN not set in pi/.env: not linking", flush=True)
        while True:
            await asyncio.sleep(3600)
    wait = 2
    async with httpx.AsyncClient(base_url=LOCAL, timeout=5) as http:
        while True:
            try:
                async with websockets.connect(URL, additional_headers={"x-robot-token": TOKEN},
                                              max_size=4 * 1024 * 1024, ping_interval=10, ping_timeout=10) as ws:
                    print(f"[cloud] linked to {URL.split('?')[0]}", flush=True)
                    wait = 2
                    tasks = [asyncio.create_task(f(ws, http)) for f in (push_state, push_video, serve_requests)]
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for t in pending:
                        t.cancel()
                    for t in done:
                        if t.exception():
                            raise t.exception()
                    raise ConnectionError("server closed the link")
            except Exception as e:
                print(f"[cloud] link down ({type(e).__name__}: {e}); retrying in {wait}s", flush=True)
            await asyncio.sleep(wait)
            wait = min(wait * 2, 30)


if __name__ == "__main__":
    asyncio.run(main())
