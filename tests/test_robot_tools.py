import ast
from pathlib import Path

from robot.types import Action
from scoutbot.hw.motors_fake import FakeMotors
from scoutbot.settings import load
from scoutbot.tools.motor_check import run_step
from scoutbot.tools.sensor_check import format_stats


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


def test_sensor_check_reports_missing_echo_without_crashing():
    message = format_stats("center", [], 50)

    assert "no echo at all" in message
    assert "voltage divider" in message


def test_only_control_loop_and_bench_tool_apply_motor_actions():
    root = Path(__file__).resolve().parents[1] / "scoutbot"
    callers = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "apply"
            for node in ast.walk(tree)
        ):
            callers.append(path.relative_to(root).as_posix())

    assert callers == ["runtime.py", "tools/motor_check.py"]
