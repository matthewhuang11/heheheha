#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
sudo apt-get update
sudo apt-get install -y python3-venv espeak-ng mpg123 libatlas-base-dev
sudo raspi-config nonint do_i2c 0
cd "$ROOT"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-pi.txt
printf 'Pi IP: '; hostname -I
