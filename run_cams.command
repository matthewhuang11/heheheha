#!/bin/bash
# Double-click me: tries camera 0-3, saves cam0.jpg... and reports brightness
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" - 2>&1 <<'PY' | tee cams_output.txt
import cv2, time
for i in range(4):
    cap = cv2.VideoCapture(i)
    if not cap.isOpened(): print(f"camera {i}: cannot open"); continue
    frame = None
    for _ in range(40):
        ok, f = cap.read(); time.sleep(0.05)
        if ok: frame = f
    cap.release()
    if frame is None: print(f"camera {i}: opened but no frames"); continue
    cv2.imwrite(f"cam{i}.jpg", frame)
    print(f"camera {i}: {frame.shape[1]}x{frame.shape[0]} brightness {frame.mean():.1f}  (near 0 = black)")
PY
echo; read -n 1 -s -r -p "Done. Tell Claude. Press any key to close..."
