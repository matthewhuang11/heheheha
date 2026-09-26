"""Internet checker: a tiny HTTPS request every few seconds sets shared.internet. 'Simulate offline' on the dashboard
(shared.force_offline) overrides it for testing. Offline means NO INTERNET; the robot <-> laptop Wi-Fi link is separate."""
from __future__ import annotations
import threading, time
import httpx

class NetWorker:
    def __init__(self, cfg: dict, shared, bus=None):
        self.cfg = cfg["net"]; self.shared = shared; self.bus = bus; self._stop = threading.Event()
        with shared.lock: shared.force_offline = bool(self.cfg.get("force_offline", False))
    def check(self) -> bool:
        try: httpx.head(self.cfg.get("check_url", "https://generativelanguage.googleapis.com/"), timeout=2.5); return True
        except Exception: return False
    def run(self):
        last = None
        while not self._stop.is_set():
            ok = self.check()
            with self.shared.lock: self.shared.internet = ok
            online = self.shared.online()
            if online != last:
                print(f"[net] internet {'ONLINE' if online else 'OFFLINE'}", flush=True)
                if self.bus: self.bus.publish("net", {"online": online})
                last = online
            self._stop.wait(self.cfg.get("check_interval_s", 3))
    def start(self):
        threading.Thread(target=self.run, daemon=True, name="net").start(); return self
    def stop(self): self._stop.set()
