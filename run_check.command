#!/bin/bash
# Double-click me. Grabs one webcam frame, asks Gemini, saves the result to gemini_check_output.txt
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
{
  echo "== $(date) =="
  "$PY" demo.py --once 2>&1 | grep -v "automatic function calling"
  echo "== done =="
} 2>&1 | tee gemini_check_output.txt
echo; echo "Finished. Tell Claude."
read -n 1 -s -r -p "Press any key to close..."
