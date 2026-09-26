"""STOPPED / AUTO / MANUAL (spec 6.1). The robot always boots STOPPED; leaving STOPPED needs an explicit button press.
E-stop goes to STOPPED from any mode, instantly."""
from __future__ import annotations
import threading
from scoutbot.types import Mode

class ModeController:
    def __init__(self, shared, bus=None):
        self.shared = shared; self.bus = bus; self.lock = threading.Lock()
        with shared.lock: shared.mode = Mode.STOPPED; shared.mode_reason = "boot: press Start"
    @property
    def mode(self) -> Mode:
        with self.shared.lock: return self.shared.mode
    def request(self, mode: Mode | str, reason: str = "responder") -> Mode:
        mode = Mode(mode)
        with self.shared.lock:
            old = self.shared.mode; self.shared.mode = mode; self.shared.mode_reason = reason
            if mode != Mode.MANUAL: self.shared.drive_cmd = None
        if old != mode:
            print(f"[mode] {old.value} -> {mode.value} ({reason})", flush=True)
            if self.bus: self.bus.publish("mode", {"mode": mode.value, "reason": reason})
        return mode
    def estop(self, reason: str = "E-stop pressed") -> None:
        self.request(Mode.STOPPED, reason)
