#!/bin/bash
# Double-click me: scores Gemini against your verified labels (3 repeats per frame).
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python3 eval_vlm.py --score --repeats 3 2>&1 | tee eval_score_output.txt
read -n 1 -s -r -p "Done. Press any key to close..."
