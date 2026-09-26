#!/bin/bash
cd "$(dirname "$0")"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" -m scoutbot --profile laptop --set net.force_offline=true
read -n 1 -s -r -p "Stopped. Press any key to close..."
