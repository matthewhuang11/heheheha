"""Talk worker: greets new survivors, answers what they say, relays responder messages, and keeps triage up to date.
Jobs come from the survivor registry and the dashboard. Never touches motors."""
from __future__ import annotations
import queue, threading, time
from pathlib import Path
from scoutbot.talk.models import GREETING, GeminiTalk, OllamaTalk
from scoutbot.talk.router import CircuitBreaker, TalkRouter
from scoutbot.types import ChatMessage

class TalkWorker:
    def __init__(self, cfg: dict, shared, bus, registry, voice=None, router: TalkRouter | None = None):
        self.cfg = cfg; self.t = cfg["talk"]; self.shared = shared; self.bus = bus; self.registry = registry; self.voice = voice
        self.q: queue.Queue = queue.Queue(); self._stop = threading.Event()
        self.snap_dir = Path(cfg["survivors"].get("data_dir", "data")) / "snapshots"
        if router is None:
            gemini = None
            try: gemini = GeminiTalk(self.t["gemini"].get("timeout_s", 8)); self._status("gemini", "ready")
            except Exception as e: self._status("gemini", f"disabled: {e}"[:120])
            o = self.t["ollama"]
            self.ollama = OllamaTalk(o["url"], o["model"], o.get("timeout_s", 20), o.get("keep_alive", "30m"))
            b = self.t.get("breaker", {})
            router = TalkRouter(shared.online, gemini, self.ollama, breaker=CircuitBreaker(b.get("fail_threshold", 3), b.get("open_s", 30)),
                                status_fn=self._status)
        else: self.ollama = router.ollama
        self.router = router

    def _status(self, k, v):
        with self.shared.lock: self.shared.services[k] = v

    # ---- jobs ----
    def submit(self, kind: str, sid: str, text: str = "", source: str = "typed"):
        self.q.put({"kind": kind, "sid": sid, "text": text, "source": source})

    def context(self) -> str:
        with self.shared.lock:
            sc = self.shared.scene; dets = list(self.shared.detections)
        parts = []
        if dets: parts.append("person visible: " + ", ".join(f"{d.where}/{d.distance} ({d.source})" for d in dets))
        if sc is not None:
            parts.append(f"terrain {sc.terrain}, path {sc.path_ahead}")
            if sc.hazards: parts.append("hazards: " + ", ".join(f"{h.type} {h.where}/{h.distance}" for h in sc.hazards))
            if sc.notes: parts.append(f"camera notes: {sc.notes}")
        return "; ".join(parts) or "no camera information"

    def _add(self, sid, role, text, source) -> ChatMessage:
        msg = ChatMessage(survivor_id=sid, role=role, text=text, source=source)
        self.registry.update(sid, lambda s: s.chat.append(msg))
        self.bus.publish("chat", msg.model_dump())
        return msg

    def _speak(self, text, priority=0, sid=""):
        if self.voice is not None: self.voice.say(text, priority, key=f"{sid}:{text}")

    def _snapshot(self, s) -> bytes | None:
        if not s or not s.best_snapshot: return None
        try: return (self.snap_dir / s.best_snapshot).read_bytes()
        except OSError: return None

    def _retriage(self, sid):
        s = self.registry.get(sid)
        if s is None: return
        tri = self.router.triage(s.chat, self.context(), self._snapshot(s))
        self.registry.update(sid, lambda x: setattr(x, "triage", tri))
        self.bus.publish("triage", {"survivor_id": sid, **tri.model_dump()})

    def handle(self, job: dict):
        sid, kind = job["sid"], job["kind"]
        if self.registry.get(sid) is None: return
        if kind == "new_survivor":
            self._add(sid, "robot", GREETING, "canned"); self._speak(GREETING, priority=1, sid=sid); self._retriage(sid)
        elif kind == "survivor_says":
            self._add(sid, "survivor", job["text"], job.get("source", "typed"))
            s = self.registry.get(sid); text, src = self.router.reply(s.chat, self.context())
            self._add(sid, "robot", text, src); self._speak(text, sid=sid); self._retriage(sid)
        elif kind == "responder_says":
            self._add(sid, "responder", job["text"], "responder"); self._speak(job["text"], priority=2, sid=sid)
        elif kind == "retriage":
            self._retriage(sid)

    def run(self):
        if self.ollama is not None: threading.Thread(target=self._ollama_watch, daemon=True, name="ollama-watch").start()
        while not self._stop.is_set():
            try: job = self.q.get(timeout=0.5)
            except queue.Empty: continue
            try: self.handle(job)
            except Exception as e: print("[talk] job failed:", job, e, flush=True)

    def _ollama_watch(self):
        warmed = False
        while not self._stop.is_set():
            ok = self.ollama.healthy()
            cur = self.shared.services.get("ollama", "")
            if not ok: self._status("ollama", f"unreachable at {self.ollama.url}")
            elif not cur.startswith("error") or not warmed: self._status("ollama", "ready")
            if ok and not warmed: self.ollama.warm_up(); warmed = True
            time.sleep(10)

    def start(self):
        threading.Thread(target=self.run, daemon=True, name="talk").start(); return self
    def stop(self): self._stop.set()
