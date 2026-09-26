"""Collect test frames from the webcam.  Run: python3 capture_dataset.py   (window opens)
SPACE = save a frame into dataset/   q = quit.  Aim for 40-100 frames: clear floor, blocked, person near/far, obstacles,
dim light, blur (move the camera), a mirror or glass, anything that might fool the system."""
import os, time, cv2
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)
out = Path("dataset"); out.mkdir(exist_ok=True)
cap = cv2.VideoCapture(int(os.getenv("CAMERA_INDEX", "0")))
for _ in range(30): cap.read(); time.sleep(0.03)
n = len(list(out.glob("*.jpg")))
while True:
    ok, f = cap.read()
    if not ok: continue
    view = f.copy(); cv2.putText(view, f"SPACE=save  q=quit  saved: {n}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 0), 2)
    cv2.imshow("capture", view); k = cv2.waitKey(30) & 255
    if k == ord(" "): n += 1; cv2.imwrite(str(out / f"frame_{int(time.time())}_{n:03d}.jpg"), f); print("saved", n, flush=True)
    if k == ord("q"): break
