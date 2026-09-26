"""Bench-test every motor action with the wheels safely off the ground."""
from __future__ import annotations

import argparse
import time
from collections.abc import Callable

from robot.types import Action
from scoutbot.hw.base import build
from scoutbot.settings import load


STEP_S = 1.0
INTERVAL_S = 0.1
REST_S = 1.0


def parser():
    parser = argparse.ArgumentParser(
        description="WHEELS OFF GROUND: step each motor action."
    )
    parser.add_argument("--profile", default="pi")
    return parser


def run_step(
    motors,
    action: Action,
    *,
    duration_s: float = STEP_S,
    interval_s: float = INTERVAL_S,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    halfway: Callable[[tuple[float, float]], None] | None = None,
) -> None:
    """Feed one action repeatedly so ramped motors reach their requested speed."""
    started = clock()
    ends_at = started + duration_s
    halfway_at = started + duration_s / 2
    reported_halfway = False
    try:
        while True:
            now = clock()
            if now >= ends_at:
                break
            motors.apply(action)
            if not reported_halfway and now >= halfway_at:
                reported_halfway = True
                if halfway is not None:
                    halfway(motors.current())
            sleep(min(interval_s, max(0.0, ends_at - now)))
        motors.apply(action)
        if not reported_halfway and halfway is not None:
            halfway(motors.current())
    finally:
        motors.stop()


def main(argv=None):
    cfg = load(parser().parse_args(argv).profile)
    is_fake = cfg["hw"]["motors"] == "fake"
    if not is_fake:
        answer = input("WHEELS OFF THE GROUND. Type yes to continue: ").strip().lower()
        if answer != "yes":
            print("Cancelled.")
            return

    world = None
    if cfg["profile"] == "sim":
        from scoutbot.hw.simworld import World

        world = World(cfg)
    camera, sensors, motors = build(cfg, None, world)
    try:
        for action in Action:
            print(action.value)
            run_step(
                motors,
                action,
                halfway=lambda wheels, action=action: print(
                    f"  halfway {action.value}: LEFT {wheels[0]:+.2f} RIGHT {wheels[1]:+.2f}"
                ),
            )
            time.sleep(REST_S)
    finally:
        motors.stop()
        sensors.close()
        camera.close()
        motors.close()


if __name__ == "__main__":
    main()
