#!/bin/bash
# Scoutbot for Mac: double-click me. The first time, I set everything up (a few minutes); after that I start at once.
cd "$(dirname "$0")" || exit 1

pause() { echo; read -n 1 -s -r -p "Press any key to close this window..."; echo; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "Scoutbot needs Python 3.10 or newer, and this Mac doesn't have it yet."
  echo "Download it from https://www.python.org/downloads/ , install it, then double-click start.command again."
  pause; exit 1
fi

# First run, or the package list changed since the last setup: (re)install. Otherwise this returns at once.
if ! python3 scripts/setup.py --if-needed; then
  echo; echo "Setup did not finish. Scroll up to see why, fix it, then double-click start.command again."
  pause; exit 1
fi

.venv/bin/python -m scoutbot.start "$@"
pause
