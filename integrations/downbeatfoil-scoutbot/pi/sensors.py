"""HC-SR04 ultrasonic rangefinders, fired one at a time so they don't hear each other's echoes.

Echo edges are timestamped by the kernel through lgpio callbacks, which is far more
accurate than timing the pulse in python.
"""
import statistics
import threading
import time

import config

try:
    import lgpio
    _OK = True
except Exception:
    _OK = False

MAX_M = 4.0          # hc-sr04 range limit; "nothing in front" reads as this
SOUND_MPS = 343.0


class Sonars:
    def __init__(self):
        self.dist = {name: None for name, _, _ in config.SONARS}  # meters, None = sensor not answering
        self._hist = {name: [] for name in self.dist}
        self.sim = not _OK or not config.SONARS
        self._edges = {}
        if self.sim:
            return
        self.h = lgpio.gpiochip_open(0)
        self._cbs = []
        for name, trig, echo in config.SONARS:
            lgpio.gpio_claim_output(self.h, trig, 0)
            lgpio.gpio_claim_alert(self.h, echo, lgpio.BOTH_EDGES)
            self._cbs.append(lgpio.callback(self.h, echo, lgpio.BOTH_EDGES, self._edge))
        threading.Thread(target=self._run, daemon=True).start()

    def _edge(self, chip, gpio, level, tick):
        if level == 1:
            self._edges[gpio] = [tick, None]
        elif level == 0 and gpio in self._edges:
            self._edges[gpio][1] = tick

    def _ping(self, trig, echo):
        self._edges.pop(echo, None)
        lgpio.gpio_write(self.h, trig, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(self.h, trig, 0)
        time.sleep(0.05)  # longer than the sensor's 38 ms no-echo timeout
        e = self._edges.get(echo)
        if not e:
            return None           # never answered: unplugged or miswired
        if e[1] is None:
            return MAX_M          # started but no echo back in time: open space
        return min((e[1] - e[0]) / 1e9 * SOUND_MPS / 2, MAX_M)

    def _run(self):
        while True:
            for name, trig, echo in config.SONARS:
                d = self._ping(trig, echo)
                hist = self._hist[name]
                hist.append(d)
                del hist[:-3]
                good = [x for x in hist if x is not None]
                # median of the last 3 kills the odd spurious reading
                self.dist[name] = round(statistics.median(good), 2) if good else None
                time.sleep(0.01)

    def get(self, name):
        return self.dist.get(name)
