"""Simulate the whole robot workflow with no robot.

    picture --(Gemini, ONE call)--> standard data object --+
                                                           +--> plain code (NO AI) --> action
    random ultrasonic readings (mock) ---------------------+

Examples:
    python3 simulate.py                      mock scene, no API needed
    python3 simulate.py --scene fire         pick a mock scene: clear blocked fire person rubble stairs
    python3 simulate.py --live               grab ONE webcam frame, ask Gemini once, then simulate
    python3 simulate.py --image photo.jpg    same, using a photo
    python3 simulate.py --random-scenes      also randomize the camera data object on every row
"""
import argparse, os, random, sys, time
from pathlib import Path
import cv2
from dotenv import load_dotenv
load_dotenv(override=True)
from robot.brain import evaluate, first_match, RULE_NAMES
from robot.sim import random_sensors, random_scene
from demo import canned

MOCK = {"clear": 0, "blocked": 1, "fire": 2, "person": 3, "rubble": 4, "stairs": 5}
RULE_TEXT = {
    1: "sensor data stale, or no sensor has an echo            -> STOP",
    2: "center < 25 cm                                         -> BACK UP if both sides < 40 cm, else turn to the roomier side",
    3: "a side < 15 cm                                         -> turn away from that side",
    4: "camera: fire/smoke/drop near anywhere, or center near/mid, or stairs -> BACK UP",
    5: "camera: a person is near                               -> STOP",
    6: "camera: path is blocked                                -> turn toward best_direction (or the roomier side)",
    7: "center < 60, side < 30, no center echo, or camera not sure / path unknown or partial / rough ground / any hazard or person -> SLOW",
    8: "everything agrees it is clear                           -> FORWARD (SLOW if camera data is missing, stale or unusable)",
}
FIELD_USE = [
    ("path_ahead", "rules 6 and 7"), ("best_direction", "rule 6 (which way to turn)"), ("terrain", "rules 4 and 7"),
    ("hazards", "rule 4 (fire / smoke / drop_off), rule 7 (anything else)"), ("people", "rule 5 (near), rule 7 (mid / far)"),
    ("objects, confidence, notes", "for humans and logs ONLY. Never used to decide."),
]

def grab_frame(idx):
    cap = cv2.VideoCapture(idx); frame = None
    if not cap.isOpened(): sys.exit(f"Cannot open camera {idx}. Try CAMERA_INDEX in .env")
    for _ in range(40):
        ok, f = cap.read(); time.sleep(0.03)
        if ok: frame = f
    cap.release()
    if frame is None or float(frame.mean()) < 8: sys.exit(f"Camera {idx} gives a black image. Try a different CAMERA_INDEX in .env")
    return frame

def sensor_txt(v): return "no echo" if v is None else f"{v:.0f} cm"
def scene_line(sc):
    if sc is None: return "(no camera data)"
    t = f"path {sc.path_ahead}, {sc.terrain}"
    if sc.hazards: t += ", " + "; ".join(f"{h.type} {h.where}/{h.distance}" for h in sc.hazards)
    if sc.people.visible: t += f", person {sc.people.where}/{sc.people.distance}"
    return t

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true"); ap.add_argument("--image"); ap.add_argument("--scene", choices=MOCK)
    ap.add_argument("--random-scenes", action="store_true"); ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--seed", type=int, default=None); ap.add_argument("--trace", type=int, default=1, help="show the full rule trace for this row")
    ap.add_argument("--camera", type=int, default=int(os.getenv("CAMERA_INDEX", "0")))
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randrange(10_000); rng = random.Random(seed)
    line = "=" * 78

    print(f"{line}\nSTEP 1: the picture becomes a standard data object (the ONLY AI step)\n{line}")
    if a.live or a.image:
        from robot.vlm import describe
        frame = cv2.imread(a.image) if a.image else grab_frame(a.camera)
        if frame is None: sys.exit(f"Cannot read image {a.image}")
        Path("logs").mkdir(exist_ok=True); cv2.imwrite("logs/sim_frame.jpg", frame)
        print(f"Source: {'photo ' + a.image if a.image else 'webcam ' + str(a.camera)}  (frame saved to logs/sim_frame.jpg). Calling Gemini ONCE...")
        t = time.time()
        try: scene = describe(frame)
        except Exception as e: sys.exit(f"\nGemini call failed: {type(e).__name__}: {e}")
        print(f"Gemini answered in {time.time() - t:.1f}s. This is the last time any AI is used.\n")
    elif a.random_scenes:
        scene = None; print("Source: RANDOM mock camera data, a new one for every row (no AI).\n")
    else:
        scene = canned(MOCK[a.scene or "blocked"]) if a.scene else random_scene(rng)
        print(f"Source: MOCK scene{' ' + a.scene if a.scene else ' (random)'} (no AI, no API call).\n")
    if scene is not None:
        print(scene.model_dump_json(indent=2))
    print("\nHow the code uses each field:")
    for f, u in FIELD_USE: print(f"  {f:<28}{u}")

    print(f"\n{line}\nSTEP 2: plain code takes over (NO AI from here). First matching rule wins.\n{line}")
    for n in range(1, 9): print(f"  {n}. {RULE_TEXT[n]}")

    print(f"\n{line}\nSTEP 3: {a.n} random ultrasonic readings, each run through those rules   (seed {seed})\n{line}")
    print(f"{'#':>2}  {'LEFT':>8} {'CENTER':>8} {'RIGHT':>8}   {'ACTION':<13}{'RULE':<5} WHY" + ("   |  CAMERA DATA" if a.random_scenes else ""))
    counts, kept = {}, []
    for i in range(1, a.n + 1):
        s = random_sensors(rng, 10.0); sc = random_scene(rng) if a.random_scenes else scene
        steps = evaluate(s, sc, 10.0, 10.0); f = first_match(steps); L, C, R = s.values()
        counts[f.action.value] = counts.get(f.action.value, 0) + 1; kept.append((s, sc, steps, f))
        print(f"{i:>2}  {sensor_txt(L):>8} {sensor_txt(C):>8} {sensor_txt(R):>8}   {f.action.value:<13}{f.rule:<5} {f.reason}" + (f"   |  {scene_line(sc)}" if a.random_scenes else ""))
    print("\nSummary: " + ", ".join(f"{k} x{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))

    k = min(max(a.trace, 1), a.n); s, sc, steps, f = kept[k - 1]; L, C, R = s.values()
    print(f"\n{line}\nWALKTHROUGH of row {k}:  left {sensor_txt(L)}, center {sensor_txt(C)}, right {sensor_txt(R)};  camera: {scene_line(sc)}\n{line}")
    fi = steps.index(f)
    for i, x in enumerate(steps):
        tag = "FIRES" if i == fi else ("not reached" if i > fi else ("skipped" if not x.applicable else "no match"))
        print(f"  rule {x.rule} [{tag:<11}] {x.name}\n{'':>26}{x.evidence}")
    print(f"\n  => {f.action.value}  (rule {f.rule}: {f.reason})")
    print(f"\nRerun the same numbers with:  python3 simulate.py --seed {seed}" + (" --live" if a.live else ""))

if __name__ == "__main__": main()
