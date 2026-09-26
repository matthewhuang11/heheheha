#!/bin/bash
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" -m scoutbot.tools.ollama_check
read -n 1 -s -r -p "Done. Press any key to close..."
