"""python -m scoutbot --profile laptop | sim | pi   [--set key=value ...] [--share]

  --profile laptop  any laptop: its webcam + dashboard sliders as distance sensors + fake motors ("mac" also works)
  --profile sim     simulated room: fake sensors react to fake driving, fake survivors
  --profile pi      the real robot
  --set a.b=c       override any config value, e.g. --set hw.distance=random --set sim.world=rubble
  --share           let phones / other laptops on the same Wi-Fi open the dashboard (listens on 0.0.0.0)
  --headless N      no server: run N seconds in AUTO (link check off) and print a summary (for quick tests)

Easiest start: python -m scoutbot.start   (a menu), or double-click start.command / start.bat.
"""
from __future__ import annotations
import argparse, os, signal, socket, sys, threading, time, webbrowser
from scoutbot import settings

def _console_safe():
    """Odd characters must never crash a Windows console."""
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(errors="replace")
        except Exception: pass

def port_free(host: str, port: int) -> bool:
    """False if something already answers on the port (any address), or we can't bind it."""
    for probe in {"127.0.0.1", host if host not in ("0.0.0.0", "") else "127.0.0.1"}:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM); c.settimeout(0.3)
        try:
            if c.connect_ex((probe, port)) == 0: return False
        except OSError: pass
        finally: c.close()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name != "nt": s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port)); return True
    except OSError: return False
    finally: s.close()

def dashboard_urls(host: str, port: int, token: str = "") -> list[tuple[str, str]]:
    """[(label, url)] to print: localhost always, plus LAN addresses when listening on all interfaces."""
    from scoutbot.start import lan_ips
    q = f"/?token={token}" if token else ""
    local = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0', '') else host}:{port}"
    out = [("dashboard", local + q)]
    if host in ("0.0.0.0", ""):
        ips = lan_ips()
        if ips:
            for ip in ips: out.append(("other devices on this Wi-Fi", f"http://{ip}:{port}{q}"))
        else: out.append(("other devices on this Wi-Fi", "no network address found (are you on Wi-Fi?)"))
    return out

def main(argv=None):
    _console_safe()
    ap = argparse.ArgumentParser(prog="python -m scoutbot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=settings.DEFAULT_PROFILE); ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--headless", type=float, default=0, metavar="SECONDS")
    ap.add_argument("--share", action="store_true", help="let other devices on this Wi-Fi open the dashboard")
    ap.add_argument("--record", action="store_true", help="save camera frames (2/s) and sensor readings to data/recordings/<time>/")
    a = ap.parse_args(argv)
    overrides = list(a.set)
    if a.share: overrides = ["server.host=0.0.0.0"] + overrides
    if a.record: overrides = ["record.enabled=true"] + overrides
    if a.headless: overrides += ["safety.link_required=false"]
    cfg = settings.load(a.profile, overrides)

    host, port = cfg["server"]["host"], int(cfg["server"]["port"])
    if not a.headless and not port_free(host, port):
        raise SystemExit(f"[scoutbot] port {port} is in use (is Scoutbot already running in another window?). "
                         f"Close it, or try: --set server.port={port + 1}")

    from scoutbot.runtime import Runtime
    rt = Runtime(cfg)

    def shutdown(*_):
        print("\n[scoutbot] stopping: motors off", flush=True); rt.stop(); sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)
    try: signal.signal(signal.SIGTERM, shutdown)
    except (ValueError, AttributeError): pass

    if a.headless:
        from scoutbot.types import Mode
        threading.Thread(target=rt.camera_loop, daemon=True).start()
        time.sleep(1.0); rt.modes.request(Mode.AUTO, "headless test")
        t_end = time.monotonic() + a.headless
        while time.monotonic() < t_end:
            time.sleep(2); st = rt.state()
            p = st["pose"]; print(f"  {st['final_action']:<13} rule {st['decision']['rule']}  pose ({p['x_cm']:.0f},{p['y_cm']:.0f}) "
                                  f"+/-{p['uncertainty_cm']:.0f}  survivors {len(st['survivors'])}  contacts {st['sim_contacts']}", flush=True)
        st = rt.state(); rt.stop()
        print(f"[headless] done: survivors={len(st['survivors'])} sim_contacts={st['sim_contacts']} watchdog_trips={st['deadman']['trips']}")
        for s in st["survivors"]: print(f"   {s['id']} at ({s['x']:.0f},{s['y']:.0f}) +/-{s['u']:.0f} triage={s['category']} msgs={s['messages']}")
        return st

    import uvicorn
    from scoutbot.server.app import create_app
    server = uvicorn.Server(uvicorn.Config(create_app(rt), host=host, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True, name="server").start()
    urls = dashboard_urls(host, port, os.getenv("SCOUTBOT_TOKEN", "").strip())
    for label, url in urls: print(f"[scoutbot] {label}: {url}", flush=True)
    if host not in ("0.0.0.0", ""): print("[scoutbot] (add --share to open it from a phone on the same Wi-Fi)", flush=True)
    print("[scoutbot] press Ctrl-C to stop", flush=True)
    if cfg["server"].get("open_browser"): threading.Timer(2.0, lambda: webbrowser.open(urls[0][1])).start()
    try: rt.camera_loop()          # camera capture stays on the main thread (macOS likes that)
    except KeyboardInterrupt: shutdown()

if __name__ == "__main__": main()
