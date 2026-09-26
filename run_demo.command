#!/bin/bash
# Double-click me: opens the live webcam + Gemini + mock-sensor demo. Press q in the video window to quit.
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" demo.py 2>&1 | grep -v "automatic function calling"
echo; read -n 1 -s -r -p "Demo closed. Press any key to close this window..."
