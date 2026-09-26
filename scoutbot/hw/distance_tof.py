"""Real ToF distance sensors over I2C (VL53L0X / VL53L1X), in case the hardware team uses them instead of HC-SR04s
(the diagram says "ToF · I2C"). All three share one bus, so each gets its own address at boot using its XSHUT pin.
Needs on the Pi: enable I2C (raspi-config), pip install adafruit-circuitpython-vl53l0x adafruit-blinka.
VL53L0X only reaches ~1.2-2 m: beyond that we report 'far' (200 cm) rather than 'no echo'."""
from __future__ import annotations
import time
from robot.types import Sensors

FAR_CM = 200.0

class ToFArray:
    def __init__(self, xshut: list[int], addresses=(0x30, 0x31, 0x32)):
        import board, busio, digitalio, adafruit_vl53l0x
        i2c = busio.I2C(board.SCL, board.SDA)
        pins = []
        for n in xshut:
            p = digitalio.DigitalInOut(getattr(board, f"D{n}")); p.switch_to_output(value=False); pins.append(p)
        self.sensors = []
        for p, addr in zip(pins, addresses):     # wake one at a time and move it to its own address
            p.value = True; time.sleep(0.05)
            s = adafruit_vl53l0x.VL53L0X(i2c); s.set_address(addr); self.sensors.append(s)
    def read(self) -> Sensors:
        vals, ok = [], []
        for s in self.sensors:
            try:
                mm = s.range
                if mm <= 0: vals.append(0.0); ok.append(False)
                elif mm >= 8000: vals.append(FAR_CM); ok.append(True)     # out of range = nothing close
                else: vals.append(mm / 10.0); ok.append(True)
            except Exception: vals.append(0.0); ok.append(False)
        return Sensors(left=vals[0], center=vals[1], right=vals[2], valid=tuple(ok), updated_at=time.monotonic())
    def close(self): pass
