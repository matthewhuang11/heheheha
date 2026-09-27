"""Sound sensor, DHT11 temperature/humidity, and the buzzer.

Everything degrades to "not present" instead of crashing when a part is missing.
"""
import threading
import time
from pathlib import Path

import config

try:
    import lgpio
    _OK = True
except Exception:
    _OK = False


class Sound:
    """Digital sound sensor: remembers when it last heard something loud."""

    def __init__(self):
        self.last_heard = 0.0
        self.count = 0
        self.present = _OK and config.SOUND_PIN >= 0
        if not self.present:
            return
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_alert(self.h, config.SOUND_PIN, lgpio.BOTH_EDGES)
        # no debounce: a clap makes the comparator chatter at audio frequency, so every
        # pulse is well under a millisecond and any debounce filters the whole clap out
        self._cb = lgpio.callback(self.h, config.SOUND_PIN, lgpio.BOTH_EDGES, self._edge)

    def _edge(self, chip, gpio, level, tick):
        active = level == (0 if config.SOUND_ACTIVE_LOW else 1)
        if active:
            self.last_heard = time.time()
            self.count += 1

    def heard_within(self, seconds):
        return self.present and time.time() - self.last_heard < seconds


class Dht11:
    """Reads the kernel's dht11 driver (dtoverlay=dht11,gpiopin=4 in /boot/firmware/config.txt).

    The sensor answers within microseconds of being woken, which python can't catch
    reliably; the kernel driver does the timing. Keeps the last good reading, since
    the dht11 misses often.
    """

    def __init__(self):
        self.temp_c = self.humidity = None
        self.read_at = 0.0
        self.dev = None
        self.present = self._find()
        threading.Thread(target=self._run, daemon=True).start()

    def _find(self):
        # the iio node can be missing for a moment at boot; keep looking instead of giving up
        f = next(Path("/sys/bus/iio/devices").glob("iio:device*/in_temp_input"), None)
        self.dev = f.parent if f else None
        self.present = f is not None
        return self.present

    def _read(self):
        t = int((self.dev / "in_temp_input").read_text()) / 1000
        h = int((self.dev / "in_humidityrelative_input").read_text()) / 1000
        return t, h

    def _run(self):
        while True:
            if self.dev is None and not self._find():
                time.sleep(5)
                continue
            try:
                t, h = self._read()
                # the dht11 sometimes passes its checksum with garbage (e.g. 151% humidity)
                sane = -10 <= t <= 60 and 5 <= h <= 95
                jump = self.temp_c is not None and abs(t - self.temp_c) > 8
                if sane and not jump:
                    self.temp_c, self.humidity = t, h
                    self.read_at = time.time()
            except OSError:
                pass  # checksum or timeout miss; normal for a dht11, try again
            time.sleep(3)  # the dht11 needs >1 s between reads


class Buzzer:
    """Active buzzer: hold the pin on to sound. Passive buzzer: needs a square wave at the pitch."""

    def __init__(self):
        self.present = _OK and config.BUZZER_PIN >= 0
        self.on_level = 0 if config.BUZZER_ACTIVE_LOW else 1
        self.off_level = 1 - self.on_level
        self._lock = threading.Lock()
        if self.present:
            self.h = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.h, config.BUZZER_PIN, self.off_level)  # claim it silent

    def _sound(self, hz):
        if config.BUZZER_PASSIVE:
            lgpio.tx_pwm(self.h, config.BUZZER_PIN, hz, 50)
            self._pwm_on = True
        else:
            lgpio.gpio_write(self.h, config.BUZZER_PIN, self.on_level)

    def _silence(self):
        if getattr(self, "_pwm_on", False):
            lgpio.tx_pwm(self.h, config.BUZZER_PIN, 0, 0)  # lgpio errors if pwm is stopped twice
            self._pwm_on = False
        lgpio.gpio_write(self.h, config.BUZZER_PIN, self.off_level)

    def play(self, notes, wait=False):
        """notes: [(hz, seconds), ...]; hz 0 is a rest. An active buzzer plays the rhythm only."""
        if not self.present:
            return

        def run():
            with self._lock:
                try:
                    for hz, secs in notes:
                        if hz:
                            self._sound(hz)
                            time.sleep(secs * 0.9)
                            self._silence()
                            time.sleep(secs * 0.1)
                        else:
                            time.sleep(secs)
                finally:
                    self._silence()  # never leave it sounding
        if wait:
            run()
        else:
            threading.Thread(target=run, daemon=True).start()

    def beep(self, times=1, on=0.12, off=0.1):
        self.play([(config.BUZZER_HZ, on), (0, off)] * times)


class Senses:
    def __init__(self):
        self.sound, self.dht, self.buzzer = Sound(), Dht11(), Buzzer()

    def snapshot(self):
        """Environment facts, stored on each survivor and shown on the dashboard."""
        t = self.dht.temp_c
        return {
            "temp_c": t,
            "humidity": self.dht.humidity,
            "hot": t is not None and t >= config.HOT_C,
            "heard_sound": self.sound.heard_within(10),
            "sound_present": self.sound.present,
            "dht_present": self.dht.present and self.dht.read_at > 0,
        }
