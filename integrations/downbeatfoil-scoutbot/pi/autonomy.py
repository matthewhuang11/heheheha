"""Autonomous search behavior. Runs entirely on the robot, no network needed.

    explore -> (obstacle) -> avoid -> explore
    explore -> (person seen) -> approach -> contact -> turn_away -> explore
    any     -> (time up / "return" pressed) -> return (retrace path backwards) -> done

Driving is plain control code on sonar + yolo, not an llm: it has to react 10x a second.
"""
import random
import threading
import time

import config
import voice
from victims import locate

TICK = 0.1


class Autonomy:
    def __init__(self, drive, sonars, detector, camera, log, event, senses=None):
        self.drive, self.sonars, self.detector, self.camera, self.log = drive, sonars, detector, camera, log
        self.senses = senses
        self.scan_cooldown_until = 0.0
        self.event = event
        self.state = "manual"
        self.state_t = time.time()
        self.mission_t0 = None
        self.avoid_dir = 1
        self.target_lost_t = None
        self.contact_vid = None
        self._contact_done = False
        threading.Thread(target=self._run, daemon=True).start()

    # ---- controls ----

    def start(self):
        self.drive.start_recording()
        self.mission_t0 = time.time()
        self._go("explore")
        self.event("mission started: exploring on its own")

    def go_home(self):
        if self.state in ("manual", "return", "done"):
            return
        self._go("return")
        threading.Thread(target=self._retrace, daemon=True).start()

    def manual(self):
        """Any manual drive command takes over immediately."""
        if self.state != "manual":
            self.drive.stop_recording()
            self._go("manual")
            self.event("manual control")

    def status(self):
        left = None
        if self.mission_t0 and self.state not in ("manual", "done"):
            left = max(0, round(config.MISSION_S - (time.time() - self.mission_t0)))
        return {"state": self.state, "mission_left_s": left, "contact": self.contact_vid}

    # ---- internals ----

    def _go(self, state):
        self.state = state
        self.state_t = time.time()

    def _in_state(self):
        return time.time() - self.state_t

    def _new_target(self):
        """Best detection that isn't someone we've already talked to."""
        pose = self.drive.pose()
        for d in sorted(self.detector.detections, key=lambda d: -d["conf"]):
            v = self.log.nearest(*locate(d, pose))
            if not (v and v["contacted"]):
                return d
        return None

    def _front(self):
        """Closest obstacle ahead across the forward-looking sonars; None only if all are dead."""
        ds = [d for d in (self.sonars.get(n) for n in config.FRONT_SONARS) if d is not None]
        return min(ds) if ds else None

    def _open_side(self):
        """Which way to turn away from an obstacle: +1 right, -1 left."""
        l, r = self.sonars.get("left"), self.sonars.get("right")
        if l is not None and r is not None:
            return 1 if r > l else -1  # toward the more open side
        if r is not None:
            return 1 if r > config.CLEAR_DIST_M else -1  # one side sensor: use it if clear, else go the other way
        if l is not None:
            return -1 if l > config.CLEAR_DIST_M else 1
        return random.choice((-1, 1))

    def _heard_something(self):
        return (self.senses is not None and time.time() > self.scan_cooldown_until
                and self.senses.sound.heard_within(1.0))

    def _run(self):
        while True:
            try:
                self._tick()
            except Exception as e:
                self.drive.stop()
                self.event(f"autonomy error, stopped: {e}")
                self._go("manual")
            time.sleep(TICK)

    def _tick(self):
        s = self.state
        if s in ("manual", "done", "return"):
            return
        if self.mission_t0 and time.time() - self.mission_t0 > config.MISSION_S and s != "contact":
            self.event("mission time up: heading home")
            self.go_home()
            return

        front = self._front()
        if front is None and not self.sonars.sim and s != "contact":
            # every distance sensor unplugged or dead: never drive blind on real hardware
            self.drive.stop()
            if self._in_state() > 0.5 and s != "blind":
                self.event("distance sensors not answering: holding still")
                self._go("blind")
            return
        if s == "blind":
            self.event("distance sensors back: resuming")
            self._go("explore")
            return
        blocked = front is not None and front < config.AVOID_DIST_M

        if s == "explore":
            if self._new_target():
                self._go("approach")
                self.event("person spotted: approaching")
            elif blocked:
                self.avoid_dir = self._open_side()
                self._go("avoid")
            elif self._heard_something():
                # someone knocked or shouted but isn't in view: stop and turn to look for them
                self.scan_cooldown_until = time.time() + 15
                self._go("scan")
                self.event("heard a sound: stopping to look around")
            else:
                self.drive.set(config.CRUISE, 0)

        elif s == "scan":
            if self._new_target():
                self._go("approach")
                self.event("found where the sound came from: approaching")
            elif self._in_state() > 6.0:  # about one slow turn
                self._go("explore")
            else:
                self.drive.set(0, config.TURN_SPEED * 0.6)

        elif s == "avoid":
            clear = front is None or front > config.CLEAR_DIST_M
            if clear and self._in_state() > 0.4:
                self._go("explore")
            elif self._in_state() > 3.0:
                self.avoid_dir *= -1  # stuck turning one way, try the other
                self._go("avoid")
            else:
                self.drive.set(0, config.TURN_SPEED * self.avoid_dir)

        elif s == "approach":
            t = self._new_target()
            if not t:
                self.target_lost_t = self.target_lost_t or time.time()
                if time.time() - self.target_lost_t > 2.0:
                    self.target_lost_t = None
                    self._go("explore")
                else:
                    self.drive.stop()
                return
            self.target_lost_t = None
            turn = max(-0.6, min(0.6, t["bearing_deg"] / 30))
            close = t["dist_m"] <= config.STOP_NEAR_PERSON_M or (front is not None and front < 0.45)
            if close and abs(t["bearing_deg"]) < 12:
                self.drive.stop()
                frame, _ = self.camera.latest()
                self.contact_vid = self.log.find_or_add(t, self.drive.pose(), frame)
                self._contact_done = False
                self._go("contact")
                threading.Thread(target=self._contact, args=(self.contact_vid,), daemon=True).start()
            else:
                self.drive.set(0 if close else config.APPROACH_SPEED, turn)

        elif s == "contact":
            self.drive.stop()
            if self._contact_done:
                self._go("turn_away")

        elif s == "turn_away":
            # swing away so we don't lock straight back onto the same person
            if self._in_state() < 1.5:
                self.drive.set(0, config.TURN_SPEED)
            else:
                self._go("explore")

    def _contact(self, vid):
        self.event(f"talking to survivor {vid}")
        if self.senses:
            self.senses.buzzer.beep(3)  # a sound they can locate, even before the voice starts
            self.log.patch(vid, env=self.senses.snapshot())
            time.sleep(0.8)
        spoke = voice.say(config.GREETING)
        audio = voice.record(vid, config.LISTEN_S)
        voice.say(config.SIGNOFF)
        self.log.patch(vid, contacted=True, audio=audio.name if audio else None)
        self.scan_cooldown_until = time.time() + 5  # don't chase the echo of our own voice
        self.event(f"survivor {vid}: " + ("answer recorded" if audio else
                                          "no mic, location saved" if spoke else "no audio hardware, location saved"))
        self._contact_done = True

    def _retrace(self):
        path = self.drive.stop_recording()
        self.event(f"retracing {sum(p[2] for p in path):.0f}s of driving back to entry")
        for l, r, dt in reversed(path):
            if self.state != "return":
                return  # someone took manual control
            if l == 0 and r == 0:
                continue  # time spent parked (e.g. talking to someone) doesn't need replaying
            end = time.time() + dt
            while time.time() < end:
                self.drive.set_lr(-l, -r)
                time.sleep(min(0.1, max(0, end - time.time())))
        self.drive.stop()
        self._go("done")
        self.event("back at entry: ready to sync with HQ")
