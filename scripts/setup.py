#!/usr/bin/env python3
"""One-step Scoutbot setup for Mac, Windows, Linux and the Raspberry Pi. Standard library only.

    python3 scripts/setup.py            # laptop: core packages + YOLO (optional) + .env
    python3 scripts/setup.py --no-yolo  # skip YOLO (PyTorch is big; Gemini spots people instead)
    python3 scripts/setup.py --pi       # on the Raspberry Pi: requirements-pi.txt

Safe to run again at any time: it only adds what is missing.
You normally never run this yourself: start.command / start.sh / start.bat run it the first time."""
from __future__ import annotations
import argparse, hashlib, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
MIN = (3, 10)

def say(msg: str): print(f"\n==> {msg}", flush=True)
def warn(msg: str): print(f"[warning] {msg}", flush=True)

MARKER = VENV / "scoutbot-setup-ok"      # written only when setup finished; holds a hash of the requirements

def requirements_hash(pi: bool | None = None) -> str:
    """Changes when requirements.txt (or requirements-pi.txt) changes, so a git pull that adds a package re-runs setup."""
    if pi is None: pi = marker_mode() == "pi"
    h = hashlib.sha256()
    for name in ("requirements.txt", "requirements-pi.txt") if pi else ("requirements.txt",):
        p = ROOT / name
        if p.exists(): h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]

def marker_mode() -> str:
    try: return MARKER.read_text(encoding="utf-8").split()[1]
    except Exception: return "laptop"

def setup_is_current() -> bool:
    """True if setup finished before and the requirements haven't changed since."""
    try: return MARKER.read_text(encoding="utf-8").split()[0] == requirements_hash()
    except Exception: return False

def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def run(cmd: list, check: bool = True) -> bool:
    shown = " ".join(str(c) for c in cmd).replace(str(ROOT) + os.sep, "")
    print(f"    $ {shown}", flush=True)
    rc = subprocess.call([str(c) for c in cmd], cwd=str(ROOT))
    if rc != 0 and check:
        print("\n[FAIL] That step failed. Scroll up to see why, fix it, then run setup again "
              "(double-click start again, or: python3 scripts/setup.py).", flush=True)
        sys.exit(rc)
    return rc == 0

def check_python():
    if sys.version_info < MIN:
        print(f"[FAIL] Scoutbot needs Python {MIN[0]}.{MIN[1]} or newer; this is {sys.version.split()[0]}.\n"
              "       Download it from https://www.python.org/downloads/ (Windows: tick 'Add python.exe to PATH'),\n"
              "       then run setup again.", flush=True)
        sys.exit(1)

def make_venv():
    py = venv_python()
    if py.exists():
        say(f"Using the existing virtual environment in {VENV.name}/"); return py
    say(f"Creating a virtual environment in {VENV.name}/ (a private copy of Python for Scoutbot)")
    import venv
    try:
        venv.EnvBuilder(with_pip=True, clear=False, upgrade_deps=False).create(str(VENV))
    except Exception as e:
        print(f"[FAIL] could not create {VENV.name}/: {e}", flush=True)
        if sys.platform.startswith("linux"):
            print("       On Debian / Ubuntu / Raspberry Pi OS run:  sudo apt install python3-venv python3-pip", flush=True)
        shutil.rmtree(VENV, ignore_errors=True); sys.exit(1)
    if not py.exists():
        print(f"[FAIL] {VENV.name}/ was made but has no Python in it. Delete the {VENV.name} folder and run setup again.", flush=True)
        sys.exit(1)
    return py

def install(py: Path, pi: bool, yolo: bool):
    say("Updating pip")
    run([py, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    req = "requirements-pi.txt" if pi else "requirements.txt"
    say(f"Installing packages from {req} (a few minutes the first time)")
    run([py, "-m", "pip", "install", "-r", req])
    if not yolo:
        print("    (skipping YOLO: --no-yolo)"); return
    say("Installing YOLO person detection (optional, large download the first time)")
    yreq = ROOT / "requirements-yolo.txt"
    ok = run([py, "-m", "pip", "install", "-r", yreq.name] if yreq.exists() else [py, "-m", "pip", "install", "ultralytics"], check=False)
    if not ok:
        warn("YOLO didn't install. That's OK: Gemini will spot people instead.\n"
             f"          Retry later with:  {venv_python().relative_to(ROOT)} -m pip install "
             + ("-r requirements-yolo.txt" if yreq.exists() else "ultralytics"))

def make_env():
    env, example = ROOT / ".env", ROOT / ".env.example"
    if env.exists():
        say(".env already exists (your keys are kept)"); return
    if example.exists():
        lines = []
        for line in example.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and not line.lstrip().startswith("#") and looks_like_placeholder(v):
                line = f"{k}="                        # never copy a fake value (e.g. a token nobody knows)
            lines.append(line)
        env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        env.write_text("# Scoutbot keys (all optional). See README.md.\n", encoding="utf-8")
    say("Created .env: open it and paste the keys you have (all optional; the simulator needs none)")

PLACEHOLDER_HINTS = ("your_", "replace_with", "user:password@", "<", "changeme", "xxx")

def looks_like_placeholder(value: str) -> bool:
    v = value.strip().strip('"').strip("'").lower()
    return bool(v) and any(h in v for h in PLACEHOLDER_HINTS)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pi", action="store_true", help="install the Raspberry Pi packages (requirements-pi.txt)")
    ap.add_argument("--no-yolo", action="store_true", help="skip YOLO / PyTorch")
    ap.add_argument("--if-needed", action="store_true",
                    help="do nothing if setup already finished and the requirements haven't changed (used by the start launchers)")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(errors="replace")
        except Exception: pass
    if not a.pi and is_raspberry_pi(): a.pi = True
    if a.if_needed:
        if venv_python().exists() and setup_is_current(): return
        if venv_python().exists(): print("Scoutbot: the package list changed (or setup didn't finish last time): updating.", flush=True)
        else: print("Scoutbot: first run, setting things up. This takes a few minutes, once.", flush=True)
        if marker_mode() == "pi": a.pi = True

    print(f"Scoutbot setup  (Python {sys.version.split()[0]}, {sys.platform}, folder {ROOT})", flush=True)
    check_python()
    py = make_venv()
    install(py, a.pi, not a.no_yolo)
    make_env()
    MARKER.write_text(f"{requirements_hash(a.pi)} {'pi' if a.pi else 'laptop'}\n", encoding="utf-8")
    say("Checking the setup")
    run([py, "-m", "scoutbot.tools.doctor", "--quiet", "--no-camera"], check=False)
    starter = "double-click start.bat" if os.name == "nt" else ("double-click start.command, or run ./start.sh" if sys.platform == "darwin" else "run ./start.sh")
    print(f"\nSetup finished. To start Scoutbot: {starter}\n"
          f"  (or: {venv_python().relative_to(ROOT)} -m scoutbot.start)", flush=True)

def is_raspberry_pi() -> bool:
    try: return "raspberry pi" in Path("/proc/device-tree/model").read_text(encoding="utf-8", errors="ignore").lower()
    except Exception: return False

if __name__ == "__main__":
    main()
