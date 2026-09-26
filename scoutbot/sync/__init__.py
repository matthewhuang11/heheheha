"""Local-first survivor storage and background sync to MongoDB and Tiger Data (spec section 12)."""
from __future__ import annotations
import os

def _set(name: str) -> bool:
    return bool(os.getenv(name, "").strip().strip('"').strip("'"))

def resolve_sinks(cfg: dict) -> list[str]:
    """Resolve explicit sync sinks, or enable only cloud stores configured in the environment."""
    sinks = cfg.get("sync", {}).get("sinks", [])
    if sinks == "auto":
        return [name for name, variable in (("mongo", "MONGODB_URI"), ("tiger", "TIGER_DATABASE_URL")) if _set(variable)]
    return list(sinks or [])
