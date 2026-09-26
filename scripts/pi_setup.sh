#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi

essential_packages=(
  python3-venv python3-dev espeak-ng mpg123 libgl1 libglib2.0-0 i2c-tools git
)
optional_packages=(libatlas-base-dev libopenblas-dev)

echo "Installing Raspberry Pi OS Bookworm dependencies..."
$SUDO apt-get update
$SUDO apt-get install -y "${essential_packages[@]}"
$SUDO apt-get install -y "${optional_packages[@]}" || \
  echo "Optional math packages unavailable; continuing."

if command -v raspi-config >/dev/null 2>&1; then
  $SUDO raspi-config nonint do_i2c 0
else
  echo "raspi-config is unavailable; enable I2C before using ToF sensors."
fi

if [ "$(id -u)" -ne 0 ]; then
  $SUDO usermod -aG gpio,i2c "$USER"
  echo "Group membership updated; sign out and back in before GPIO/I2C use."
fi

cd "$ROOT"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-pi.txt
if ! pip install -r requirements-yolo.txt; then
  echo "YOLO install failed; set perception.yolo.where=remote and run the laptop worker."
fi

if [ ! -e .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example."
fi

printf 'Pi IP: '
hostname -I
cat <<'EOF'

Next steps:
  python -m scoutbot.tools.camcheck --profile pi
  python -m scoutbot.tools.yolo_bench --profile pi --imgsz 320
  python -m scoutbot.tools.sensor_check --profile pi
  python -m scoutbot.tools.motor_check --profile pi

For laptop Ollama, set talk.ollama.url in config/profiles/pi.yaml to:
  http://<LAPTOP_IP>:11434
EOF
