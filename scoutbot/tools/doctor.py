"""Scoutbot doctor: checks this computer and explains, in plain words, anything that is missing.

    python -m scoutbot.tools.doctor                 # everything
    python -m scoutbot.tools.doctor --quiet         # only problems and optional things that are off
    python -m scoutbot.tools.doctor --no-camera     # skip the camera check (it can take a few seconds)

[ OK ] works   [ -- ] optional and not there (Scoutbot still runs)   [FAIL] must be fixed
Exit code 1 only for real blockers (Python too old, core packages missing)."""
from __future__ import annotations
import argparse, importlib.util, os, platform, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN_PY = (3, 10)

# (import name, pip name)
CORE = [("cv2", "opencv-python"), ("pydantic", "pydantic"), ("dotenv", "python-dotenv"), ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"), ("yaml", "pyyaml"), ("httpx", "httpx"), ("websockets", "websockets"), ("numpy", "numpy")]
# (import name, pip name, what it unlocks)
OPTIONAL = [("google.genai", "google-genai", "Gemini (scene descriptions, replies and triage online)"),
            ("ultralytics", "ultralytics", "YOLO person detection (without it Gemini spots people)"),
            ("pymongo", "pymongo", "MongoDB sync"),
            ("psycopg", "psycopg[binary]", "Tiger Data (Postgres) sync"),
            ("pytest", "pytest", "running the tests")]
# (env key, what turns off without it)
KEYS = [("GEMINI_API_KEY", "Gemini: without it the robot drives on its sensors only, and replies come from Ollama or canned text"),
        ("ELEVENLABS_API_KEY", "ElevenLabs voice: without it the computer's built-in voice speaks"),
        ("MONGODB_URI", "MongoDB: without it survivors are saved on this computer only"),
        ("TIGER_DATABASE_URL", "Tiger Data: without it sightings are saved on this computer only")]

class Report:
    def __init__(self, quiet: bool):
        self.quiet = quiet; self.problems = 0; self.blockers = 0
    def ok(self, msg):
        if not self.quiet: print(f"[ OK ] {msg}", flush=True)
    def opt(self, msg): print(f"[ -- ] {msg}", flush=True)
    def fail(self, msg, blocker=False):
        print(f"[FAIL] {msg}", flush=True); self.problems += 1
        if blocker: self.blockers += 1
    def info(self, msg):
        if not self.quiet: print(f"       {msg}", flush=True)

def has(mod: str) -> bool:
    try: return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError): return False

def check_python(r: Report) -> bool:
    v = sys.version_info; osname = f"{platform.system()} {platform.release()} ({platform.machine()})"
    if v < MIN_PY:
        r.fail(f"Python {v.major}.{v.minor} is too old: install Python 3.10+ from https://www.python.org/downloads/", blocker=True)
        return False
    r.ok(f"Python {v.major}.{v.minor}.{v.micro} on {osname}")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not in_venv: r.info("(not running inside .venv; the start launchers use .venv automatically)")
    return True

def check_packages(r: Report) -> bool:
    missing = [pip for mod, pip in CORE if not has(mod)]
    if missing:
        r.fail(f"core packages missing: {', '.join(missing)}. Run setup again: python3 scripts/setup.py "
               f"(or double-click start.command / start.bat)", blocker=True)
        return False
    r.ok("core packages installed")
    for mod, pip, what in OPTIONAL:
        if has(mod): r.ok(f"{pip}: {what}")
        else: r.opt(f"{pip} not installed: {what} is off")
    return True

def check_env(r: Report, cfg: dict):
    env = ROOT / ".env"
    if env.exists(): r.ok(".env found")
    else: r.opt(".env missing: copy .env.example to .env and paste the keys you have (all optional)")
    for key, what in KEYS:
        if os.getenv(key, "").strip(): r.ok(f"{key} is set")
        else: r.opt(f"{key} not set. {what}")
    tok = os.getenv("SCOUTBOT_TOKEN", "").strip()
    if tok: r.info("SCOUTBOT_TOKEN is set: open the dashboard with /?token=... (the start message shows the link)")
    sinks = cfg.get("sync", {}).get("sinks", [])
    try:
        from scoutbot.sync import resolve_sinks          # B.P1: turns "auto" into the sinks whose URL is set
        sinks = resolve_sinks(cfg)
    except Exception: pass
    if isinstance(sinks, str): sinks = [sinks]
    if sinks: r.ok(f"cloud sync on for: {', '.join(sinks)}")
    else: r.opt("cloud sync off for this profile (everything is still saved in data/ on this computer)")

def check_internet(r: Report, cfg: dict) -> bool:
    try:
        from scoutbot.net import NetWorker
        from scoutbot.state import Shared
        online = NetWorker(cfg, Shared()).check()
    except Exception as e:
        r.opt(f"could not test the internet ({type(e).__name__})"); return False
    if online: r.ok("internet reachable")
    else: r.opt("no internet: Scoutbot runs offline (Ollama replies, local voice, sync waits)")
    return online

def check_lan(r: Report, cfg: dict):
    from scoutbot.start import lan_ips
    ips = lan_ips(); port = cfg.get("server", {}).get("port", 8000)
    if ips:
        r.ok(f"this computer on the network: {', '.join(ips)}")
        r.info(f"tip: start with --share, then open http://{ips[0]}:{port} on a phone on the same Wi-Fi")
    else: r.opt("no network address found: phones can't open the dashboard (join a Wi-Fi or hotspot)")

def check_ollama(r: Report, cfg: dict):
    o = cfg.get("talk", {}).get("ollama", {}); url = str(o.get("url", "http://localhost:11434")).rstrip("/"); model = o.get("model", "qwen2.5:3b")
    if "LAPTOP_IP" in url:
        r.opt(f"Ollama url is a placeholder ({url}): set talk.ollama.url in config/profiles/pi.yaml to the laptop's address"); return
    try:
        import httpx
        tags = httpx.get(url + "/api/tags", timeout=2.0).json()
        names = [m.get("name", "") for m in tags.get("models", [])]
    except Exception:
        r.opt(f"Ollama not running at {url}: offline replies will be canned text. Install from https://ollama.com, "
              f"open it, then: ollama pull {model}"); return
    if any(n == model or n.startswith(model + ":") or n.split(":")[0] == model for n in names) or any(model in n for n in names):
        r.ok(f"Ollama running, model {model} ready")
    else: r.opt(f"Ollama is running but the model isn't downloaded yet: ollama pull {model}")

def check_voice(r: Report):
    try:
        from scoutbot.voice.speaker import LocalVoice
        v = LocalVoice(); cmd = getattr(v, "cmd", None)
    except Exception as e:
        r.opt(f"could not check the built-in voice ({type(e).__name__})"); return
    if cmd: r.ok(f"built-in voice: {cmd[0] if isinstance(cmd, (list, tuple)) else cmd}")
    elif platform.system() == "Linux": r.opt("no built-in voice: sudo apt install espeak-ng (replies are shown as text until then)")
    else: r.opt("no built-in voice found (replies are shown as text)")

def check_camera(r: Report, cfg: dict):
    idx = cfg.get("hw", {}).get("camera_index", 0)
    try:
        from scoutbot.hw import camera_opencv as camlib
    except Exception as e:
        r.opt(f"could not load the camera code ({type(e).__name__})"); return
    finder = getattr(camlib, "open_best_camera", None)
    cam = None; used = idx
    try:
        if finder is not None:                            # A's auto-detect, if merged
            res = finder(cfg) if _takes_cfg(finder) else finder(idx)
            cam = res[0] if isinstance(res, tuple) else res
            used = getattr(cam, "index", idx)
        else:
            cam = camlib.OpenCVCamera(idx, warmup_frames=5)
        frame = None
        if cam is not None and getattr(cam, "ok", False):
            t_end = time.monotonic() + 3
            while frame is None and time.monotonic() < t_end: frame = cam.read()
        if frame is not None:
            h, w = frame.shape[:2]; r.ok(f"camera {used} works ({w}x{h})")
            if finder is None and str(idx) != "0": r.info("(set CAMERA_INDEX in .env if this is the wrong camera)")
        else:
            hint = ("Mac: allow Camera for Terminal in System Settings > Privacy & Security > Camera"
                    if platform.system() == "Darwin" else "check it is plugged in and not used by another app")
            r.opt(f"no camera at index {used} ({hint}; or try CAMERA_INDEX=0/1/2 in .env). The simulator doesn't need one.")
    finally:
        try:
            if cam is not None: cam.close()
        except Exception: pass

def _takes_cfg(fn) -> bool:
    import inspect
    try: params = list(inspect.signature(fn).parameters)
    except (TypeError, ValueError): return False
    return bool(params) and params[0] in ("cfg", "config")

def parser():
    p = argparse.ArgumentParser(prog="python -m scoutbot.tools.doctor", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--quiet", action="store_true", help="hide the OK lines")
    p.add_argument("--no-camera", action="store_true", help="skip the camera check")
    p.add_argument("--profile", default="laptop", help="which profile's settings to check (default laptop)")
    return p

def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(errors="replace")
        except Exception: pass
    a = parser().parse_args(argv); r = Report(a.quiet)
    print("Scoutbot doctor", flush=True)
    if not check_python(r) or not check_packages(r):
        print(f"\n{r.problems} problem(s) to fix.", flush=True); return 1
    from scoutbot import settings
    try: cfg = settings.load(a.profile)
    except SystemExit as e:
        r.fail(f"config: {e}"); cfg = settings.load("laptop")
    check_env(r, cfg)
    check_internet(r, cfg)
    check_lan(r, cfg)
    check_ollama(r, cfg)
    check_voice(r)
    if not a.no_camera: check_camera(r, cfg)
    print("\n" + ("Ready." if r.problems == 0 else f"{r.problems} problem(s) to fix."), flush=True)
    print("Start with: python -m scoutbot.start (or double-click start.command / start.bat, or ./start.sh)", flush=True)
    return 1 if r.blockers else 0

if __name__ == "__main__":
    sys.exit(main())
