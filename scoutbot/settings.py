"""Loads config/profiles/base.yaml, then the chosen profile, then --set overrides. Also loads .env (secrets).
Settings are a plain nested dict; use get(cfg, "a.b.c", default) for dotted access.

Profile aliases: "mac" is the old name of "laptop" (it works on any laptop), so --profile mac still works."""
from __future__ import annotations
import copy, os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "config" / "profiles"
ALIASES = {"mac": "laptop"}
DEFAULT_PROFILE = "laptop"

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

def available_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILES.glob("*.yaml") if p.stem != "base")

def resolve_profile(profile: str) -> str:
    return ALIASES.get(profile, profile)

def _read_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def load(profile: str = DEFAULT_PROFILE, overrides: list[str] | None = None, load_env: bool = True) -> dict:
    if load_env:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env", override=True, encoding="utf-8")
        except ImportError: pass
    profile = resolve_profile(profile)
    cfg = _read_yaml(PROFILES / "base.yaml")
    if profile != "base":
        p = PROFILES / f"{profile}.yaml"
        if not p.exists():
            raise SystemExit(f"unknown profile '{profile}'. Choose one of: {', '.join(available_profiles())} "
                             f"(or 'mac', the old name of 'laptop')")
        cfg = merge(cfg, _read_yaml(p))
    cam = os.getenv("CAMERA_INDEX", "").strip()
    if cam and profile != "pi":
        try: cfg["hw"]["camera_index"] = int(cam)
        except ValueError: print(f"[settings] CAMERA_INDEX in .env is not a number ('{cam}'): ignored", flush=True)
    for item in overrides or []:
        if "=" not in item: raise SystemExit(f"--set needs key=value, got '{item}'")
        k, v = item.split("=", 1)
        set_path(cfg, k.strip(), yaml.safe_load(v))
    cfg["profile"] = profile
    return cfg
