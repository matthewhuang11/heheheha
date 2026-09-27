"""Load two DEMO survivors into pi/data for the laptop preview. Never run this on the robot.

Photos are staged Pexels stock (free license, no attribution required), run through the
robot's real person detector and portrait crop so the cards look like live captures:
  tools/demo-photos/survivor-1.jpg  https://www.pexels.com/photo/man-sitting-in-an-abandoned-building-18901339/
  tools/demo-photos/survivor-2.jpg  https://www.pexels.com/photo/bald-man-sitting-on-ground-and-leaning-against-concrete-wall-11627305/
The transcript and report are written demo text, not real data.

Run from scoutbot/pi:  ../tools/.venv/Scripts/python ../tools/seed_demo.py
"""
import json
import math
import struct
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import cv2

import config
import detector
import victims

PHOTOS = Path(__file__).parent / "demo-photos"


def person_box(img):
    d = detector.Detector.__new__(detector.Detector)
    d.net = cv2.dnn.readNetFromONNX(config.MODEL_PATH)
    dets = d._infer(img)
    if not dets:
        raise SystemExit("no person detected in a demo photo")
    return max(dets, key=lambda x: x["conf"])


def tone(path, seconds=2):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(1200 * math.sin(i / 9) * math.sin(i / 4000)))
                               for i in range(16000 * seconds)))


audio_dir = config.DATA_DIR / "audio"
audio_dir.mkdir(exist_ok=True)
for old in list(victims.SNAPS.glob("*.jpg")) + list(audio_dir.glob("*.wav")):
    old.unlink()

now = time.time()
base = dict(dist_m=1.2, sightings=4, conversation=[])
out = []
specs = [
    ("d41a07", "survivor-2.jpg", 2.6, 3.4, now - 420, dict(
        contacted=True, audio="d41a07.wav", status="processed", report_source="gemini",
        transcript="yeah, i can hear you. i think my ankle's broken, i can't put weight on it. "
                   "there was someone else on the stairs with me.",
        report="PRIORITY: DELAYED\nPOSITION: 2.6 m east, 3.4 m north of the entry point\n"
               "CONDITION: conscious and talking clearly, sitting up against a wall, suspected ankle "
               "injury, cannot bear weight\nHAZARDS: none visible near him\n"
               "NEXT STEP: stretcher team to his position, then search the stairwell for the second "
               "person he mentioned")),
    ("7be3c9", "survivor-1.jpg", -1.9, 6.1, now - 180, dict(
        contacted=True, audio="7be3c9.wav", status="pending", report_source=None,
        transcript=None, report=None)),
]
for vid, photo, x, y, found, extra in specs:
    img = cv2.imread(str(PHOTOS / photo))
    det = person_box(img)
    victims.save_snap(vid, img, det)
    tone(audio_dir / f"{vid}.wav")
    out.append(dict(base, id=vid, x=x, y=y, conf=det["conf"], found_at=found, last_seen=found + 30, **extra))

victims.STORE.write_text(json.dumps(out, indent=2))
print(f"seeded {len(out)} demo survivors into {config.DATA_DIR}")
