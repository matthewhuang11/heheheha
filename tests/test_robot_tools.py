from robot.types import Action
from scoutbot.hw.motors_fake import FakeMotors
from scoutbot.settings import load
from scoutbot.tools.motor_check import run_step


def test_motor_check_repeatedly_applies_and_stops_fake_motors():
    motors = FakeMotors(load("sim", load_env=False), quiet=True)
    now = [0.0]
    halfway_wheels = []

    def clock():
        return now[0]

    def sleep(seconds):
        now[0] += seconds

    run_step(
        motors,
        Action.FORWARD,
        duration_s=0.10,
        interval_s=0.02,
        clock=clock,
        sleep=sleep,
        halfway=halfway_wheels.append,
    )

    assert halfway_wheels
    assert halfway_wheels[0][0] > 0
    assert halfway_wheels[0][1] > 0
    assert motors.current() == (0.0, 0.0)
