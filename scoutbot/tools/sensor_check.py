import argparse
import statistics

from scoutbot.settings import load
from scoutbot.hw.base import build


def parser():
    parser = argparse.ArgumentParser(
        description="Read 50 distance samples and print calibration statistics."
    )
    parser.add_argument("--profile", default="pi")
    return parser


def format_stats(name, values, total):
    """Describe valid samples without treating a missing echo as a distance."""
    missing = (1 - len(values) / total) * 100 if total else 100.0
    if not values:
        return (
            f"{name}: no echo at all: check wiring and the voltage divider "
            f"(no-echo={missing:.1f}%)"
        )
    return (
        f"{name}: min={min(values):.1f} median={statistics.median(values):.1f} "
        f"max={max(values):.1f} no-echo={missing:.1f}%"
    )


def main(argv=None):
    cfg = load(parser().parse_args(argv).profile)
    camera, sensors, motors = build(cfg, None)
    rows = []
    try:
        for _ in range(50):
            rows.append(sensors.read())
    finally:
        sensors.close()
        camera.close()
        motors.stop()
        motors.close()
    for index, name in enumerate(("left", "center", "right")):
        values = [
            (row.left, row.center, row.right)[index]
            for row in rows
            if row.valid[index] and (row.left, row.center, row.right)[index] is not None
        ]
        print(format_stats(name, values, len(rows)))


if __name__ == "__main__":
    main()
