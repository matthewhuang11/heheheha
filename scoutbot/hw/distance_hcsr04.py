"""Real HC-SR04 ultrasonic sensors on the Pi (spec 5.2). Fires the three sensors one at a time, 60 ms apart, so they do
not hear each other. Echo pins MUST go through a 5 V -> 3.3 V voltage divider. Returns raw readings: the existing
robot/sensing.py filter (median of 5, no-echo rules) runs inside the controller.
Needs on the Pi: pip install lgpio   (Pi OS Bookworm)."""
from __future__ import annotations
import time
from robot.sensing import PING_GAP_S, echo_to_cm
from robot.types import Sensors

ECHO_TIMEOUT_S = 0.03

class HCSR04Array:
    def __init__(self, trig: list[int], echo: list[int], temp_c: float = 20.0):
        import lgpio
        self.lg = lgpio; self.h = lgpio.gpiochip_open(0); self.trig = trig; self.echo = echo; self.temp_c = temp_c
        for t in trig: lgpio.gpio_claim_output(self.h, t, 0)
        for e in echo: lgpio.gpio_claim_input(self.h, e)
        time.sleep(0.05)
    def _ping(self, i: int) -> float | None:
        lg, h, t, e = self.lg, self.h, self.trig[i], self.echo[i]
        lg.gpio_write(h, t, 1); time.sleep(10e-6); lg.gpio_write(h, t, 0)
        start = time.perf_counter(); deadline = start + ECHO_TIMEOUT_S
        while lg.gpio_read(h, e) == 0:
            if time.perf_counter() > deadline: return None
        rise = time.perf_counter(); deadline = rise + ECHO_TIMEOUT_S
        while lg.gpio_read(h, e) == 1:
            if time.perf_counter() > deadline: return None
        return echo_to_cm(time.perf_counter() - rise, self.temp_c)
    def read(self) -> Sensors:
        vals = []
        for i in range(3):
            vals.append(self._ping(i)); time.sleep(PING_GAP_S)
        return Sensors(left=vals[0] or 0, center=vals[1] or 0, right=vals[2] or 0,
                       valid=tuple(v is not None for v in vals), updated_at=time.monotonic())
    def close(self):
        try: self.lg.gpiochip_close(self.h)
        except Exception: pass
