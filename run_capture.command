#!/bin/bash
# Double-click me: opens the webcam so you can press SPACE to save test frames into dataset/ (q to quit).
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python3 capture_dataset.py
read -n 1 -s -r -p "Done. Press any key to close..."
