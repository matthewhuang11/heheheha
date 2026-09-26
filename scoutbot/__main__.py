"""python -m scoutbot --profile mac | sim | pi   [--set key=value ...]

  --profile mac   laptop webcam + dashboard sliders as distance sensors + fake motors
  --profile sim   simulated room: fake sensors react to fake driving, fake survivors
  --profile pi    the real robot
  --set a.b=c     override any config value, e.g. --set hw.distance=random --set sim.world=rubble
  --headless N    no server: run N seconds in AUTO (link check off) and print a summary (for quick tests)
"""
from __future__ import annotations
import argparse, signal, sys, threading, time, webbrowser
from scoutbot import settings

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m scoutbot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="mac"); ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--headless", type=float, default=0, metavar="SECONDS")
    a = ap.parse_args(argv)
    overrides = list(a.set)
    if a.headless: overrides += ["safety.link_required=false"]
    cfg = settings.load(a.profile, overrides)
    from scoutbot.runtime import Runtime
    rt = Runtime(cfg)

    def shutdown(*_):
        print("\n[scoutbot] stopping: motors off", flush=True); rt.stop(); sys.exit(0)
    signal.signal(signal.SIGINT, shutdown); signal.signal(signal.SIGTERM, shutdown)

    if a.headless:
        from scoutbot.types import Mode
        threading.Thread(target=rt.camera_loop, daemon=True).start()
        time.sleep(1.0); rt.modes.request(Mode.AUTO, "headless test")
        t_end = time.monotonic() + a.headless
        while time.monotonic() < t_end:
            time.sleep(2); st = rt.state()
            p = st["pose"]; print(f"  {st['final_action']:<13} rule {st['decision']['rule']}  pose ({p['x_cm']:.0f},{p['y_cm']:.0f}) "
                                  f"±{p['uncertainty_cm']:.0f}  survivors {len(st['survivors'])}  contacts {st['sim_contacts']}", flush=True)
        st = rt.state(); rt.stop()
        print(f"[headless] done: survivors={len(st['survivors'])} sim_contacts={st['sim_contacts']} watchdog_trips={st['deadman']['trips']}")
        for s in st["survivors"]: print(f"   {s['id']} at ({s['x']:.0f},{s['y']:.0f}) ±{s['u']:.0f} triage={s['category']} msgs={s['messages']}")
        return st

    import uvicorn
    from scoutbot.server.app import create_app
    host, port = cfg["server"]["host"], cfg["server"]["port"]
    server = uvicorn.Server(uvicorn.Config(create_app(rt), host=host, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True, name="server").start()
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}"
    print(f"[scoutbot] dashboard: {url}   (Ctrl-C to stop)", flush=True)
    if cfg["server"].get("open_browser"): threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    try: rt.camera_loop()          # camera capture stays on the main thread (macOS likes that)
    except KeyboardInterrupt: shutdown()

if __name__ == "__main__": main()
