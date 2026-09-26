#!/bin/bash
# Double-click me: opens the live webcam + Gemini + mock-sensor demo. Press q in the video window to quit.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python3 demo.py 2>&1 | grep -v "automatic function calling"
echo; read -n 1 -s -r -p "Demo closed. Press any key to close this window..."
