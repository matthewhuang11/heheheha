"""Local-first survivor storage and background sync targets."""
from __future__ import annotations
import os

def _set(name: str) -> bool:
    return bool(os.getenv(name, "").strip().strip('"').strip("'"))

def resolve_sinks(cfg: dict) -> list[str]:
    """Resolve explicit sinks, or the selected safe default cloud target."""
    sync = cfg.get("sync", {})
    sinks = sync.get("sinks", [])
    if sinks == "auto":
        target = sync.get("target", "ingest")
        if target == "none":
            return []
        if target == "ingest":
            return ["ingest"] if _set("INGEST_URL") and _set("INGEST_TOKEN") else []
        if target == "mongo":
            return ["mongo"] if _set("MONGODB_URI") else []
        if target == "auto":  # migration convenience: prefer the server-side credential boundary.
            if _set("INGEST_URL") and _set("INGEST_TOKEN"):
                return ["ingest"]
            return ["mongo"] if _set("MONGODB_URI") else []
        raise ValueError(f"unknown sync.target {target!r}")
    return list(sinks or [])
