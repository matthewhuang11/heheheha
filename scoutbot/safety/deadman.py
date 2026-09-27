"""Dead-man stop (spec 6.3). Two independent timers; either one stops the motors.
 - Motor watchdog (runs on the robot): if Motors.apply() has not been called for motor_watchdog_s, force stop and keep
   re-sending stop every 0.2 s. Catches a crashed or frozen control loop.
 - Link watchdog: the dashboard sends a heartbeat every 100 ms. If it goes quiet, MANUAL -> STOPPED, and AUTO -> STOPPED
   too unless safety.auto_on_link_loss is 'continue'.
Manual drive commands expire after manual_cmd_valid_s: only real drive commands keep the wheels turning."""
from __future__ import annotations
import threading, time
from robot.types import Action
from scoutbot.types import DriveCommand, Mode

def manual_action(cmd: DriveCommand | None, now: float, valid_s: float) -> Action:
    if cmd is None or now - cmd.received_at > valid_s: return Action.STOP
    return cmd.action

def manual_axes(cmd: DriveCommand | None, now: float, valid_s: float) -> tuple[float, float]:
    """Return a fresh analog command, or neutral when it is absent or stale."""
    if cmd is None or cmd.v is None or cmd.w is None or now - cmd.received_at > valid_s:
        return 0.0, 0.0
    return cmd.v, cmd.w

def link_check(mode: Mode, link_at: float | None, now: float, safety_cfg: dict) -> str | None:
    """Returns a reason string if the link is lost for this mode, else None."""
    if mode == Mode.STOPPED or not safety_cfg.get("link_required", True): return None
    timeout = safety_cfg["link_timeout_manual_s"] if mode == Mode.MANUAL else safety_cfg["link_timeout_auto_s"]
    if mode == Mode.AUTO and safety_cfg.get("auto_on_link_loss", "stop") == "continue": return None
    if link_at is None or now - link_at > timeout:
        return f"robot link lost ({'no heartbeat yet' if link_at is None else f'{now - link_at:.1f}s'}) - motors stopped"
    return None

class MotorWatchdog:
    def __init__(self, motors, timeout_s: float = 0.5, resend_s: float = 0.2, clock=time.monotonic):
        self.motors = motors; self.timeout = timeout_s; self.resend = resend_s; self.clock = clock
        self.last_apply = None; self.tripped = False; self.trips = 0; self._last_stop = 0.0
        self._stop_evt = threading.Event(); self.lock = threading.Lock()
    def fed(self, when: float | None = None):
        with self.lock: self.last_apply = self.clock() if when is None else when; self.tripped = False
    def check(self) -> bool:
        """Returns True if tripped (and stops the motors). Call often (the thread does it at 20 Hz)."""
        now = self.clock()
        with self.lock: last = self.last_apply
        if last is not None and now - last <= self.timeout: return False
        if not self.tripped and last is not None: self.trips += 1
        self.tripped = last is not None
        if now - self._last_stop >= self.resend:
            try: self.motors.stop()
            except Exception as e: print("[watchdog] stop failed:", e, flush=True)
            self._last_stop = now
        return self.tripped
    def run(self):
        while not self._stop_evt.is_set(): self.check(); time.sleep(0.05)
    def start(self):
        threading.Thread(target=self.run, daemon=True, name="motor-watchdog").start(); return self
    def stop(self): self._stop_evt.set()
