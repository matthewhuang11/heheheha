#!/bin/bash
# Double-click me: dashboard in FULL MOCK mode (fake camera reports + random ultrasonic data, no Gemini needed).
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
( sleep 4; open http://localhost:8000 ) &
python3 web_demo.py --fake-vlm --random-sensors --random-scenes 2>&1 | grep -v "automatic function calling"
read -n 1 -s -r -p "Stopped. Press any key to close..."
