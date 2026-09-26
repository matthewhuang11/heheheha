"""Check configured survivor stores without printing credentials or leaving test data."""
from __future__ import annotations
import argparse, os, time
from scoutbot.sync.mongo import MongoSink
from scoutbot.sync.tiger import TigerSink

def main(argv=None):
    p = argparse.ArgumentParser(description="Connect to configured MongoDB/Tiger and report safe connectivity.")
    p.add_argument("--sink", choices=("mongo", "tiger", "both"), default="both"); a = p.parse_args(argv)
    choices = (("mongo", MongoSink, "MONGODB_URI"), ("tiger", TigerSink, "TIGER_DATABASE_URL"))
    for name, cls, variable in choices:
        if a.sink not in (name, "both"): continue
        if not os.getenv(variable, "").strip().strip('"').strip("'"):
            print(f"SKIP {name}: not configured"); continue
        try:
            started = time.monotonic(); cls(os.environ[variable]); print(f"PASS {name}: connected in {time.monotonic() - started:.2f}s")
        except Exception as exc: print(f"FAIL {name}: {type(exc).__name__}")
if __name__ == "__main__": main()
