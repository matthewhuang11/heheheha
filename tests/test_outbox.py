import json
import pytest
from scoutbot.sync.outbox import Outbox, SyncWorker
from scoutbot.state import Shared

class Sink:
    def __init__(self, fail=False): self.fail = fail; self.survivors = {}; self.rows = {"sightings": [], "telemetry": []}
    def upsert_survivor(self, d):
        if self.fail: raise ConnectionError("db down")
        if d["version"] > self.survivors.get(d["id"], {}).get("version", -1): self.survivors[d["id"]] = d
    def add_sightings(self, rows): self.rows["sightings"] += rows
    def add_telemetry(self, rows): self.rows["telemetry"] += rows

def rec(v): return {"id": "S-0001", "version": v}

def test_newest_version_wins_and_files_collapse(tmp_path):
    ob = Outbox(tmp_path, ["mongo"])
    for v in (1, 2, 3): ob.put_survivor(rec(v))
    ob.add_rows("sightings", [{"a": 1}, {"a": 2}])
    s = Sink(); ob.drain("mongo", s)
    assert s.survivors["S-0001"]["version"] == 3 and len(s.rows["sightings"]) == 2 and ob.queued("mongo") == 0

def test_failed_sink_keeps_its_queue_other_sink_drains(tmp_path):
    ob = Outbox(tmp_path, ["mongo", "tiger"]); ob.put_survivor(rec(1)); ob.add_rows("telemetry", [{"x": 1}])
    sh = Shared(); sh.internet = True
    good, bad = Sink(), Sink(fail=True)
    w = SyncWorker({"sync": {"interval_s": 1, "backoff_max_s": 60}}, sh, ob, clients={"mongo": good, "tiger": bad})
    w.clients = {"mongo": good, "tiger": bad}; w._client = lambda k: {"mongo": good, "tiger": bad}[k]
    w.tick(now=0)
    assert ob.queued("mongo") == 0 and ob.queued("tiger") == 2
    assert sh.sync_status["tiger"]["state"] == "error" and sh.sync_status["mongo"]["state"] == "ok"
    assert w.backoff["tiger"] == 2.0
    w.tick(now=1); assert bad.survivors == {}                 # still backing off: not retried yet
    bad.fail = False; w.tick(now=2.5); assert ob.queued("tiger") == 0

def test_offline_queues_only(tmp_path):
    ob = Outbox(tmp_path, ["mongo"]); ob.put_survivor(rec(1))
    sh = Shared(); sh.internet = True; sh.force_offline = True; s = Sink()
    w = SyncWorker({"sync": {}}, sh, ob); w._client = lambda k: s
    w.tick(now=0); assert s.survivors == {} and sh.sync_status["mongo"]["state"].startswith("offline")
    sh.force_offline = False; w.tick(now=1); assert "S-0001" in s.survivors
