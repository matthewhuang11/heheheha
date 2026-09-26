"""Downward "cliff" sensor (KI-40): one distance sensor pointing at the floor just ahead of the front wheels.
read() returns cm to the floor, 999 when there is no floor (no echo / out of range = a drop), or None if not fitted.
The brain's rule 2 backs up when the reading is above robot.config cliff_max (15 cm).

hw.cliff: none | hcsr04 | tof     (pins in hw.cliff_pins; see docs/scoutbot/hardware-handoff.md)
Pi libraries are imported inside the classes so laptops and tests never need them."""
from __future__ import annotations
import time

NO_FLOOR = 999.0

class NoCliff:
    def read(self) -> float | None: return None
    def close(self): pass

class HCSR04Cliff:
    """A 4th HC-SR04 pointing down. Echo through a 5 V -> 3.3 V divider, like the others."""
    def __init__(self, trig: int, echo: int, temp_c: float = 20.0):
        import lgpio
        from robot.sensing import echo_to_cm
        self.lg = lgpio; self.echo_to_cm = echo_to_cm; self.h = lgpio.gpiochip_open(0)
        self.trig, self.echo, self.temp_c = trig, echo, temp_c
        lgpio.gpio_claim_output(self.h, trig, 0); lgpio.gpio_claim_input(self.h, echo); time.sleep(0.05)
    def read(self) -> float | None:
        lg, h = self.lg, self.h
        lg.gpio_write(h, self.trig, 1); time.sleep(10e-6); lg.gpio_write(h, self.trig, 0)
        deadline = time.perf_counter() + 0.02
        while lg.gpio_read(h, self.echo) == 0:
            if time.perf_counter() > deadline: return NO_FLOOR       # no echo at all: treat as no floor (safe side)
        rise = time.perf_counter(); deadline = rise + 0.02
        while lg.gpio_read(h, self.echo) == 1:
            if time.perf_counter() > deadline: return NO_FLOOR
        return round(self.echo_to_cm(time.perf_counter() - rise, self.temp_c), 1)
    def close(self):
        try: self.lg.gpiochip_close(self.h)
        except Exception: pass

class ToFCliff:
    """A VL53L0X pointing down on the I2C bus (its own XSHUT pin, address 0x33). Out of range = no floor."""
    def __init__(self, xshut: int, address: int = 0x33):
        import board, busio, digitalio, adafruit_vl53l0x
        i2c = busio.I2C(board.SCL, board.SDA)
        p = digitalio.DigitalInOut(getattr(board, f"D{xshut}")); p.switch_to_output(value=False); time.sleep(0.01)
        p.value = True; time.sleep(0.05)
        self.s = adafruit_vl53l0x.VL53L0X(i2c); self.s.set_address(address); self.pin = p
    def read(self) -> float | None:
        try: mm = self.s.range
        except Exception: return NO_FLOOR
        return NO_FLOOR if mm <= 0 or mm >= 8000 else round(mm / 10.0, 1)
    def close(self): pass

def build_cliff(cfg: dict):
    hw = cfg["hw"]; kind = str(hw.get("cliff", "none") or "none").lower()
    if kind in ("none", "false", "off"): return NoCliff()
    pins = hw.get("cliff_pins", {})
    if kind == "hcsr04": return HCSR04Cliff(int(pins["trig"]), int(pins["echo"]))
    if kind == "tof": return ToFCliff(int(pins["xshut"]))
    raise SystemExit(f"unknown hw.cliff '{kind}' (none | hcsr04 | tof)")
