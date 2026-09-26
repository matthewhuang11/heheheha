"""The Scoutbot start menu: one place to start anything, on any computer.

    python -m scoutbot.start                 # shows the menu
    python -m scoutbot.start sim --share     # skips the menu (choices: sim, laptop, offline, robot, doctor, test)

start.command (Mac), start.sh (Linux / Pi) and start.bat (Windows) set everything up and then run this.
Standard library only at import time, so it can always print its menu."""
from __future__ import annotations
import socket, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# name: (menu text, command args after "python", asks about sharing)
CHOICES = {
    "sim":     ("Simulated room demo (no camera or robot needed)",
                ["-m", "scoutbot", "--profile", "sim", "--set", "sim.world=demo"], True),
    "laptop":  ("Use this computer's webcam (fake distance sliders, no motors)",
                ["-m", "scoutbot", "--profile", "laptop"], True),
    "offline": ("Webcam, but pretend there is no internet (tests Ollama + queued sync)",
                ["-m", "scoutbot", "--profile", "laptop", "--set", "net.force_offline=true"], True),
    "robot":   ("The real robot (run this ON the Raspberry Pi)",
                ["-m", "scoutbot", "--profile", "pi"], True),
    "doctor":  ("Check my setup",
                ["-m", "scoutbot.tools.doctor"], False),
    "test":    ("Run the tests",
                ["-m", "pytest", "-q", "tests"], False),
}
ORDER = list(CHOICES)

def lan_ips() -> list[str]:
    """This computer's address(es) on the local network (not 127.x). UDP 'connect' sends nothing; it only picks a route."""
    ips: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1)); ips.append(s.getsockname()[0])
        finally: s.close()
    except OSError: pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.append(info[4][0])
    except OSError: pass
    out = []
    for ip in ips:
        if ip and not ip.startswith("127.") and not ip.startswith("0.") and ip not in out: out.append(ip)
    return out

def build_command(choice: str, share: bool = False, extra: list[str] | None = None) -> list[str]:
    _, args, can_share = CHOICES[choice]
    cmd = [sys.executable, *args]
    if share and can_share: cmd.append("--share")
    return cmd + list(extra or [])

def _ask(prompt: str) -> str:
    try: return input(prompt).strip()
    except EOFError: return ""

def menu() -> str | None:
    print("\nScoutbot")
    for i, name in enumerate(ORDER, 1): print(f"  {i}) {CHOICES[name][0]}")
    ans = _ask("Pick a number [1]: ").lower() or "1"
    if ans.isdigit() and 1 <= int(ans) <= len(ORDER): return ORDER[int(ans) - 1]
    if ans in CHOICES: return ans
    return None

def usage():
    print("Choices: " + ", ".join(ORDER))
    for i, name in enumerate(ORDER, 1): print(f"  {i}) {name:<8} {CHOICES[name][0]}")
    print("Example: python -m scoutbot.start sim --share")

def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(errors="replace")
        except Exception: pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if any(a in ("-h", "--help") for a in argv): print(__doc__); usage(); return 0
    share = "--share" in argv; argv = [a for a in argv if a != "--share"]
    try:
        if argv and not argv[0].startswith("-"):
            choice = argv.pop(0).lower()
            if choice.isdigit() and 1 <= int(choice) <= len(ORDER): choice = ORDER[int(choice) - 1]
            if choice not in CHOICES:
                print(f"Unknown choice '{choice}'."); usage(); return 2
        else:
            choice = menu()
            if choice is None: print("That's not one of the choices."); usage(); return 2
            if CHOICES[choice][2] and not share:
                share = _ask("Let phones / other laptops on this Wi-Fi open the dashboard too? [y/N]: ").lower() in ("y", "yes")
        cmd = build_command(choice, share, argv)
        print("==> python " + " ".join(cmd[1:]), flush=True)
        return subprocess.call(cmd, cwd=str(ROOT))
    except KeyboardInterrupt:
        print("\nStopped."); return 0

if __name__ == "__main__":
    sys.exit(main())
