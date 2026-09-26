#!/bin/bash
# Double-click me. ONE webcam frame -> Gemini once -> data object -> plain code + random ultrasonic readings -> actions.
# If Gemini/camera fails it falls back to a mock scene. Output is saved to sim_output.txt
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
{
  "$PY" simulate.py --live --n 15 2>&1 | grep -v "automatic function calling" || true
} | tee sim_output.txt
if grep -q "Gemini call failed\|Cannot open camera\|black image" sim_output.txt; then
  echo; echo ">>> Live step failed, running with a MOCK scene instead:"; echo
  "$PY" simulate.py --n 15 2>&1 | grep -v "automatic function calling" | tee -a sim_output.txt
fi
echo; read -n 1 -s -r -p "Done. Press any key to close..."
