#!/bin/bash
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python -m scoutbot --profile mac
read -n 1 -s -r -p "Stopped. Press any key to close..."
