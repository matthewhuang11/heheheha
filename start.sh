#!/usr/bin/env bash
# Scoutbot for Linux, the Raspberry Pi, or a Mac terminal:   ./start.sh        (menu)
#                                                            ./start.sh sim --share
# The first time, it sets everything up (a few minutes); after that it starts at once.
set -e
cd "$(dirname "$0")"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Scoutbot needs Python 3.10 or newer. Install it (Debian/Ubuntu/Pi: sudo apt install python3 python3-venv python3-pip)"
  echo "or download it from https://www.python.org/downloads/ , then run ./start.sh again."
  exit 1
fi

if ! "$PY" scripts/setup.py --if-needed; then
  echo; echo "Setup did not finish. Scroll up to see why, fix it, then run ./start.sh again."
  exit 1
fi

exec .venv/bin/python -m scoutbot.start "$@"
