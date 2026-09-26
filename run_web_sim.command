#!/bin/bash
# Double-click me: dashboard in FULL MOCK mode (fake camera reports + random ultrasonic data, no Gemini needed).
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
( sleep 4; open http://localhost:8000 ) &
"$PY" web_demo.py --fake-vlm --random-sensors --random-scenes 2>&1 | grep -v "automatic function calling"
read -n 1 -s -r -p "Stopped. Press any key to close..."
