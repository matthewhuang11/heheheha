#!/bin/bash
# Double-click me: starts the live dashboard and opens it in your browser. Ctrl-C (or close this window) to stop.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
( sleep 4; open http://localhost:8000 ) &
python3 web_demo.py 2>&1 | grep -v "automatic function calling"
read -n 1 -s -r -p "Stopped. Press any key to close..."
