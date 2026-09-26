#!/bin/bash
# Double-click me: Gemini pre-fills labels for dataset/ frames (step 1), then you fix dataset/labels.json, then run_eval_score.command
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" eval_vlm.py --label 2>&1 | tee eval_label_output.txt
read -n 1 -s -r -p "Done. Press any key to close..."
