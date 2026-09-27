"""Speak through a passive buzzer: espeak -> band-pass -> 1-bit (zero-crossing) -> gpio toggles.

usage: sudo chrt -f 80 python3 buzz_say.py "how are you" [pin]
"""
import subprocess
import sys
import time
import wave

import lgpio
import numpy as np

text = sys.argv[1] if len(sys.argv) > 1 else "how are you"
PIN = int(sys.argv[2]) if len(sys.argv) > 2 else 8

subprocess.run(["espeak-ng", "-s", "130", "-p", "40", "-w", "/tmp/buzz.wav", text], check=True)
with wave.open("/tmp/buzz.wav") as w:
    rate = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)

# band-pass 300-3400 hz: the part of speech that carries the words
spec = np.fft.rfft(x)
f = np.fft.rfftfreq(len(x), 1 / rate)
spec[(f < 300) | (f > 3400)] = 0
x = np.fft.irfft(spec, len(x))

# gate the quiet parts so silence stays silent instead of buzzing on noise
env = np.convolve(np.abs(x), np.ones(int(rate * 0.01)) / int(rate * 0.01), mode="same")
on = env > env.max() * 0.06
bits = ((x > 0) & on).astype(np.int8)

# times (ns from start) where the pin must change
edges = np.flatnonzero(np.diff(bits)) + 1
times = (edges * 1e9 / rate).astype(np.int64)
levels = bits[edges]

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, PIN, 0)
write = lgpio.gpio_write
clock = time.perf_counter_ns
try:
    t0 = clock()
    for t, lv in zip(times.tolist(), levels.tolist()):
        while clock() - t0 < t:
            pass
        write(h, PIN, lv)
finally:
    write(h, PIN, 0)  # idle low: no current through the coil
    lgpio.gpio_free(h, PIN)
print(f"said {text!r}: {len(times)} toggles over {len(x) / rate:.1f}s")
