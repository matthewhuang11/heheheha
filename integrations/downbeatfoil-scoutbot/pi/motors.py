"""Differential drive with a dead-man timeout and rough dead-reckoning pose.

Runs in simulation mode (no pins touched) when gpio isn't available, so the whole
stack can be developed on a laptop.
"""
import math
import threading
import time

import config

try:
    from gpiozero import Motor
    _GPIO_OK = True
except Exception:
    _GPIO_OK = False


class Drive:
    def __init__(self):
        self.sim = True
        self.left = self.right = None
        if _GPIO_OK:
            try:
                lf, lb, le = config.LEFT_PINS
                rf, rb, re = config.RIGHT_PINS
                self.left = Motor(forward=lf, backward=lb, enable=le, pwm=True)
                self.right = Motor(forward=rf, backward=rb, enable=re, pwm=True)
                self.sim = False
            except Exception as e:
                print(f"[motors] gpio unavailable, simulating: {e}")

        self.cmd = (0.0, 0.0)  # (left, right) in -1..1
        self.last_cmd_t = 0.0
        # breadcrumbs: [[left, right, seconds], ...] merged runs of identical commands,
        # replayed backwards to retrace the path home
        self.recording = False
        self.path = []
        # pose in meters / degrees, relative to where the robot started
        self.x = self.y = self.heading = 0.0
        self._lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    def set(self, throttle, turn):
        """throttle, turn in -1..1 (turn > 0 = right)."""
        l = max(-1.0, min(1.0, throttle + turn))
        r = max(-1.0, min(1.0, throttle - turn))
        with self._lock:
            self.cmd = (l, r)
            self.last_cmd_t = time.time()

    def set_lr(self, l, r):
        """Raw wheel command, used for path replay."""
        with self._lock:
            self.cmd = (l, r)
            self.last_cmd_t = time.time()

    def start_recording(self):
        with self._lock:
            self.path = []
            self.recording = True

    def stop_recording(self):
        with self._lock:
            self.recording = False
            return list(self.path)

    def stop(self):
        with self._lock:
            self.cmd = (0.0, 0.0)

    def reset_pose(self):
        with self._lock:
            self.x = self.y = self.heading = 0.0

    def _apply(self, motor, v, invert):
        if motor is None:
            return
        if invert:
            v = -v
        if abs(v) < 0.02:
            motor.stop()
            return
        # rescale so any nonzero command is strong enough to actually turn the wheel
        duty = config.MIN_DUTY + (1 - config.MIN_DUTY) * min(abs(v), 1.0)
        motor.forward(duty) if v > 0 else motor.backward(duty)

    def _run(self):
        prev = time.time()
        while True:
            now = time.time()
            dt, prev = now - prev, now
            with self._lock:
                if now - self.last_cmd_t > config.DRIVE_TIMEOUT_S:
                    self.cmd = (0.0, 0.0)  # dead-man: link dropped or dashboard closed
                l, r = self.cmd
                if self.recording:
                    if self.path and self.path[-1][0] == l and self.path[-1][1] == r:
                        self.path[-1][2] += dt
                    else:
                        self.path.append([l, r, dt])
                # dead reckoning from commanded speed; replace with encoders when wired
                v = (l + r) / 2 * config.MAX_SPEED_MPS
                w = (l - r) / 2 * config.MAX_TURN_DPS
                self.heading = (self.heading + w * dt) % 360
                self.x += v * dt * math.sin(math.radians(self.heading))
                self.y += v * dt * math.cos(math.radians(self.heading))
            self._apply(self.left, l, config.LEFT_INVERT)
            self._apply(self.right, r, config.RIGHT_INVERT)
            time.sleep(0.02)

    def pose(self):
        with self._lock:
            return {"x": round(self.x, 2), "y": round(self.y, 2), "heading": round(self.heading, 1)}
