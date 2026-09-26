"""Check configured survivor stores without printing credentials or leaving test data."""
from __future__ import annotations
import argparse, os, time
from scoutbot.sync.ingest import IngestSink
from scoutbot.sync.mongo import MongoSink

def main(argv=None):
    p = argparse.ArgumentParser(description="Check configured Scoutbot cloud sync without persisting test data.")
    p.add_argument("--sink", choices=("ingest", "mongo", "both"), default="both"); a = p.parse_args(argv)
    choices = (("ingest", IngestSink, ("INGEST_URL", "INGEST_TOKEN")), ("mongo", MongoSink, ("MONGODB_URI",)))
    for name, cls, variable in choices:
        if a.sink not in (name, "both"): continue
        values = [os.getenv(v, "").strip().strip('"').strip("'") for v in variable]
        if not all(values):
            print(f"SKIP {name}: not configured"); continue
        try:
            started = time.monotonic()
            sink = cls(*values)
            if name == "ingest": sink.health()
            print(f"PASS {name}: connected in {time.monotonic() - started:.2f}s")
        except Exception as exc: print(f"FAIL {name}: {type(exc).__name__}")
if __name__ == "__main__": main()
