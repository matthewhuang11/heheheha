"""Pulse every free gpio as a trigger and see which pin answers with an echo."""
import time
import lgpio

h = lgpio.gpiochip_open(0)
# skip dht (4), motors (5,6,12,13,23,24), buzzer (8), sound (25)
cands = [2, 3, 7, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 26, 27]
for p in cands:
    lgpio.gpio_claim_input(h, p, lgpio.SET_PULL_DOWN)
time.sleep(0.05)
idle = {p: lgpio.gpio_read(h, p) for p in cands}
print("pins idling high (skipped as triggers):", [p for p, v in idle.items() if v])
found = False
for t in cands:
    if idle[t]:
        continue
    lgpio.gpio_free(h, t)
    lgpio.gpio_claim_output(h, t, 0)
    others = [p for p in cands if p != t and not idle[p]]
    hits = {}
    for _ in range(4):
        lgpio.gpio_write(h, t, 1); time.sleep(0.00002); lgpio.gpio_write(h, t, 0)
        t0 = time.time(); end = t0 + 0.04
        while time.time() < end:
            for p in others:
                if lgpio.gpio_read(h, p):
                    hits[p] = hits.get(p, 0) + 1
        time.sleep(0.06)
    lgpio.gpio_free(h, t)
    lgpio.gpio_claim_input(h, t, lgpio.SET_PULL_DOWN)
    if hits:
        found = True
        print(f"trig {t:>2} -> echo seen on {sorted(hits)}")
if not found:
    print("no pin produced an echo anywhere")
