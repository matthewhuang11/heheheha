"""Loads config/profiles/base.yaml, then the chosen profile, then --set overrides. Also loads .env (secrets).
Settings are a plain nested dict; use get(cfg, "a.b.c", default) for dotted access."""
from __future__ import annotations
import copy, os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "config" / "profiles"

def merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out

def set_path(cfg: dict, dotted: str, value) -> None:
    keys = dotted.split("."); d = cfg
    for k in keys[:-1]: d = d.setdefault(k, {})
    d[keys[-1]] = value

def get(cfg: dict, dotted: str, default=None):
    d = cfg
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d: return default
        d = d[k]
    return d

def load(profile: str = "mac", overrides: list[str] | None = None, load_env: bool = True) -> dict:
    if load_env:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env", override=True)
        except ImportError: pass
    cfg = yaml.safe_load((PROFILES / "base.yaml").read_text()) or {}
    if profile != "base":
        p = PROFILES / f"{profile}.yaml"
        if not p.exists(): raise SystemExit(f"unknown profile '{profile}' (looked for {p})")
        cfg = merge(cfg, yaml.safe_load(p.read_text()) or {})
    if os.getenv("CAMERA_INDEX", "").strip() and profile != "pi":
        cfg["hw"]["camera_index"] = int(os.environ["CAMERA_INDEX"])
    for item in overrides or []:
        if "=" not in item: raise SystemExit(f"--set needs key=value, got '{item}'")
        k, v = item.split("=", 1)
        set_path(cfg, k.strip(), yaml.safe_load(v))
    cfg["profile"] = profile
    return cfg
