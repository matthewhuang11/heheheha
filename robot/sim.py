"""Random mock data for testing the brain without a robot: fake ultrasonic readings and fake camera reports."""
from __future__ import annotations
import random
from robot.types import SceneReport, Sensors

OBJECTS = ["chair", "box", "wall", "door", "debris", "table", "cable", "bucket", "person", "pipe"]

def random_sensors(rng: random.Random, now: float = 0.0) -> Sensors:
    kind = rng.choices(["open", "ahead", "side", "mixed", "tight"], [35, 25, 15, 15, 10])[0]
    o = lambda: rng.uniform(80, 280)
    L, C, R = o(), o(), o()
    if kind == "ahead": C = rng.uniform(5, 75)
    elif kind == "side":
        if rng.random() < .5: L = rng.uniform(4, 30)
        else: R = rng.uniform(4, 30)
    elif kind == "mixed": L, C, R = rng.uniform(10, 120), rng.uniform(15, 120), rng.uniform(10, 120)
    elif kind == "tight": L, C, R = rng.uniform(8, 45), rng.uniform(8, 35), rng.uniform(8, 45)
    valid = tuple(rng.random() > 0.07 for _ in range(3))    # ~7% chance a sensor gets no echo
    return Sensors(left=round(L), center=round(C), right=round(R), updated_at=now, valid=valid)

def random_scene(rng: random.Random) -> SceneReport:
    side = lambda: rng.choice(["left", "center", "right"])
    hazards = [{"type": rng.choice(["fire", "smoke", "water", "wire", "glass", "drop_off", "unstable_debris", "other"]),
                "where": side(), "distance": rng.choice(["near", "mid", "far"])}
               for _ in range(rng.choices([0, 1, 2], [60, 30, 10])[0])]
    vis = rng.random() < 0.15
    people = ({"visible": True, "where": side(), "distance": rng.choice(["near", "mid", "far"])} if vis
              else {"visible": False, "where": "none", "distance": "none"})
    return SceneReport(
        path_ahead=rng.choices(["clear", "partially_blocked", "blocked", "unknown"], [40, 20, 20, 20])[0],
        best_direction=rng.choice(["left", "center", "right", "none"]),
        terrain=rng.choices(["flat", "rubble", "uneven", "stairs_or_drop", "water", "unknown"], [50, 15, 15, 5, 5, 10])[0],
        hazards=hazards, people=people, objects=rng.sample(OBJECTS, rng.randint(0, 3)),
        confidence=round(rng.uniform(.5, 1), 2), notes="simulated scene")
