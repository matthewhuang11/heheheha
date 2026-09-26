"""Outbox (spec 12.1). Every record is already on disk in data/survivors.jsonl; the outbox holds what still has to reach
each cloud database. Each sink has its own folder, so one sink being down never blocks the other:
  data/outbox/<sink>/survivors/<id>.json   newest version only (repeated edits collapse into one upload)
  data/outbox/<sink>/<kind>.jsonl          rows (sightings, telemetry), appended
The sync worker runs only when the internet is up, upserts by id + version (so resending is harmless), deletes a file only
after that sink confirms, and backs off 2 s, 4 s, 8 s ... up to backoff_max_s on failure."""
from __future__ import annotations
import json, os, threading, time, uuid
from pathlib import Path

class Outbox:
    def __init__(self, data_dir: str | Path, sinks: list[str]):
        self.root = Path(data_dir) / "outbox"; self.sinks = list(sinks or []); self.lock = threading.Lock()
        for s in self.sinks: (self.root / s / "survivors").mkdir(parents=True, exist_ok=True)
    def put_survivor(self, survivor) -> None:
        data = survivor.model_dump_json() if hasattr(survivor, "model_dump_json") else json.dumps(survivor)
        sid = survivor.id if hasattr(survivor, "id") else survivor["id"]
        with self.lock:
            for s in self.sinks:
                p = self.root / s / "survivors" / f"{sid}.json"; tmp = p.with_suffix(".tmp")
                tmp.write_text(data); os.replace(tmp, p)
    def add_rows(self, kind: str, rows: list[dict]) -> None:
        if not rows: return
        if kind not in ("sightings", "telemetry"):
            raise ValueError(f"unknown outbox row kind {kind!r}")
        with self.lock:
            for s in self.sinks:
                with open(self.root / s / f"{kind}.jsonl", "a") as f:
                    for r in rows:
                        row = dict(r)
                        # A durable client event ID makes a retry after a successful remote
                        # write harmless. It is assigned before the row reaches disk.
                        row.setdefault("event_id", uuid.uuid4().hex)
                        f.write(json.dumps(row) + "\n")
    def queued(self, sink: str) -> int:
        d = self.root / sink
        if not d.exists(): return 0
        n = len(list((d / "survivors").glob("*.json")))
        for p in d.glob("*.jsonl*"):
            try: n += sum(1 for _ in open(p))
            except OSError: pass
        return n

    # ---- draining (used by the sync worker) ----
    def drain(self, sink: str, client) -> int:
        """Send everything queued for one sink. Raises on the first failure (the file stays for the next try)."""
        d = self.root / sink; sent = 0
        for p in sorted((d / "survivors").glob("*.json")):
            text = p.read_text(); client.upsert_survivor(json.loads(text))
            with self.lock:                                   # only delete if it was not rewritten meanwhile
                if p.exists() and p.read_text() == text: p.unlink()
            sent += 1
        for kind in ("sightings", "telemetry"):
            live = d / f"{kind}.jsonl"
            with self.lock:
                if live.exists() and live.stat().st_size > 0: os.replace(live, d / f"{kind}.jsonl.{time.time_ns()}.sending")
            for p in sorted(d.glob(f"{kind}.jsonl.*.sending")):
                rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
                if rows: getattr(client, f"add_{kind}")(rows)
                p.unlink(); sent += len(rows)
        return sent

class SyncWorker:
    def __init__(self, cfg: dict, shared, outbox: Outbox, clients: dict | None = None):
        self.cfg = cfg["sync"]; self.shared = shared; self.outbox = outbox; self.clients = clients or {}
        self.backoff = {s: 0.0 for s in outbox.sinks}; self.next_try = {s: 0.0 for s in outbox.sinks}; self._stop = threading.Event()
        with shared.lock:
            for s in outbox.sinks: shared.sync_status[s] = {"state": "starting", "queued": 0, "last_ok": None, "error": ""}
    def _client(self, sink):
        if sink not in self.clients:
            if sink == "mongo":
                from scoutbot.sync.mongo import MongoSink; self.clients[sink] = MongoSink(os.getenv("MONGODB_URI", ""))
            elif sink == "ingest":
                from scoutbot.sync.ingest import IngestSink
                self.clients[sink] = IngestSink(os.getenv("INGEST_URL", ""), os.getenv("INGEST_TOKEN", ""))
            elif sink == "tiger":
                from scoutbot.sync.tiger import TigerSink; self.clients[sink] = TigerSink(os.getenv("TIGER_DATABASE_URL", ""))
            else: raise ValueError(f"unknown sink {sink}")
        return self.clients[sink]
    def _set(self, sink, **kw):
        with self.shared.lock: self.shared.sync_status.setdefault(sink, {}).update(kw)
    def tick(self, now: float | None = None):
        now = time.monotonic() if now is None else now; online = self.shared.online()
        for sink in self.outbox.sinks:
            q = self.outbox.queued(sink); self._set(sink, queued=q)
            if not online: self._set(sink, state="offline (queued)" if q else "offline"); continue
            if now < self.next_try[sink]: continue
            try:
                self.outbox.drain(sink, self._client(sink)); self.backoff[sink] = 0.0
                self._set(sink, state="ok", queued=self.outbox.queued(sink), error="", last_ok=time.strftime("%H:%M:%S"))
            except Exception as e:
                self.backoff[sink] = min(self.cfg.get("backoff_max_s", 60), max(2.0, self.backoff[sink] * 2))
                self.next_try[sink] = now + self.backoff[sink]
                self.clients.pop(sink, None)          # reconnect next time
                state = "not configured" if isinstance(e, ValueError) else "error"
                self._set(sink, state=state, error=f"{type(e).__name__}: {e}"[:200], retry_in_s=round(self.backoff[sink], 1))
    def run(self):
        while not self._stop.is_set():
            try: self.tick()
            except Exception as e: print("[sync]", e, flush=True)
            time.sleep(self.cfg.get("interval_s", 3))
    def start(self):
        threading.Thread(target=self.run, daemon=True, name="sync").start(); return self
    def stop(self): self._stop.set()
