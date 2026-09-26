"""Tiger Data sink (Tiger Cloud: Postgres + TimescaleDB). Put TIGER_DATABASE_URL (a postgres:// URL) in .env.
  survivors  latest record per survivor (JSONB + a few columns), only newer versions overwrite
  sightings  hypertable: where each survivor was seen over time
  telemetry  hypertable: robot action / rule / distances / internet, sampled at 1 Hz
If TimescaleDB is not available the tables still work as plain Postgres tables."""
from __future__ import annotations
import json

SETUP = [
    """CREATE TABLE IF NOT EXISTS survivors (id text PRIMARY KEY, version int NOT NULL, updated_at timestamptz DEFAULT now(),
         first_seen timestamptz, last_seen timestamptz, triage text, x_cm real, y_cm real, uncertainty_cm real, sightings int, doc jsonb)""",
    """CREATE TABLE IF NOT EXISTS sightings (time timestamptz NOT NULL, survivor_id text, x_cm real, y_cm real,
         uncertainty_cm real, source text, confidence real)""",
    """CREATE TABLE IF NOT EXISTS telemetry (time timestamptz NOT NULL, mode text, action text, rule int,
         left_cm real, center_cm real, right_cm real, internet boolean, x_cm real, y_cm real)""",
]
HYPER = ["SELECT create_hypertable('sightings', 'time', if_not_exists => TRUE)",
         "SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE)"]

class TigerSink:
    def __init__(self, url: str):
        if not url: raise ValueError("TIGER_DATABASE_URL is not set in .env")
        import psycopg
        self.conn = psycopg.connect(url, autocommit=True, connect_timeout=5)
        with self.conn.cursor() as cur:
            for q in SETUP: cur.execute(q)
        for q in HYPER:
            try:
                with self.conn.cursor() as cur: cur.execute(q)
            except Exception: pass                      # plain Postgres: fine
    def upsert_survivor(self, d: dict) -> None:
        tri = (d.get("triage") or {}).get("category")
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO survivors (id, version, first_seen, last_seen, triage, x_cm, y_cm, uncertainty_cm, sightings, doc)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                           ON CONFLICT (id) DO UPDATE SET version=EXCLUDED.version, updated_at=now(), last_seen=EXCLUDED.last_seen,
                             triage=EXCLUDED.triage, x_cm=EXCLUDED.x_cm, y_cm=EXCLUDED.y_cm, uncertainty_cm=EXCLUDED.uncertainty_cm,
                             sightings=EXCLUDED.sightings, doc=EXCLUDED.doc
                           WHERE survivors.version < EXCLUDED.version""",
                        (d["id"], d["version"], d["first_seen"], d["last_seen"], tri, d["pose"]["x_cm"], d["pose"]["y_cm"],
                         d["pose"]["uncertainty_cm"], d["sightings"], json.dumps(d)))
    def add_sightings(self, rows: list[dict]) -> None:
        with self.conn.cursor() as cur:
            cur.executemany("INSERT INTO sightings (time, survivor_id, x_cm, y_cm, uncertainty_cm, source, confidence) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                            [(r["time"], r["survivor_id"], r["x_cm"], r["y_cm"], r["uncertainty_cm"], r["source"], r["confidence"]) for r in rows])
    def add_telemetry(self, rows: list[dict]) -> None:
        with self.conn.cursor() as cur:
            cur.executemany("INSERT INTO telemetry (time, mode, action, rule, left_cm, center_cm, right_cm, internet, x_cm, y_cm) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            [(r["time"], r.get("mode"), r.get("action"), r.get("rule"), r.get("left_cm"), r.get("center_cm"), r.get("right_cm"),
                              r.get("internet"), r.get("x_cm"), r.get("y_cm")) for r in rows])
