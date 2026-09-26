#!/bin/bash
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python -m scoutbot.tools.ollama_check
read -n 1 -s -r -p "Done. Press any key to close..."
