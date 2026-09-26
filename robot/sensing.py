"""Per-sensor filtering for HC-SR04-style ultrasonics: median of last 5, reject impossible values,
'no echo' only when >=3 of the last 5 pings missed (one dropped ping is normal), closing speed / time-to-collision."""
from collections import deque
from statistics import median
MIN_CM, MAX_CM = 2.0, 400.0

class SensorFilter:
    def __init__(self, n=5):
        self.buf = deque(maxlen=n); self.hist = deque(maxlen=12); self.n = n
    def push(self, raw, t):
        ok = raw is not None and MIN_CM <= raw <= MAX_CM
        self.buf.append(raw if ok else None)
        v = self.value()
        if v is not None: self.hist.append((t, v))
        return v
    def value(self):
        vals = [x for x in self.buf if x is not None]
        if not vals or (len(self.buf) - len(vals)) * 5 >= 3 * len(self.buf): return None   # >=60% missing
        return float(median(vals))
    def missing_rate(self):
        return 0.0 if not self.buf else sum(x is None for x in self.buf) / len(self.buf)
    def closing_speed(self, now, window=0.5):
        """cm/s, positive = getting closer. None if not enough history."""
        if len(self.hist) < 2: return None
        t1, v1 = self.hist[-1]
        old = [(t, v) for t, v in self.hist if t1 - t >= window]
        if not old: return None
        t0, v0 = old[-1]
        return (v0 - v1) / (t1 - t0)
    def ttc(self, now):
        s = self.closing_speed(now); v = self.value()
        if s is None or v is None or s < 3.0: return None      # <3 cm/s is noise
        return v / s

# --- for the real hardware driver (not used by the simulator) ---
PING_GAP_S = 0.06          # fire the three sensors one at a time, at least 60 ms apart, so they do not hear each other
def speed_of_sound_cm_s(temp_c: float = 20.0) -> float:
    """Sound is ~0.6 m/s faster per degree C; at 35 C an uncorrected sensor reads ~3.5% off."""
    return (331.3 + 0.606 * temp_c) * 100
def echo_to_cm(echo_seconds: float, temp_c: float = 20.0) -> float:
    return echo_seconds * speed_of_sound_cm_s(temp_c) / 2
