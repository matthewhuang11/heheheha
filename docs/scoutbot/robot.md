# Scoutbot robot notes

## What works

- A1 / KI-01: `motor_check` feeds each action every 0.1 seconds for one second, prints the ramped wheel output halfway through, then stops before the next action.
- The bench tool skips its physical-wheels confirmation when the configured motor driver is `fake`, so it is safe to exercise on the sim profile.
- A2 / KI-33: OpenCV camera selection tries the configured camera first, skips black or unavailable video feeds, and falls back across indexes 0 through 3. Windows uses OpenCV's DirectShow backend.
- A3/A5: YOLO webcam benchmark supports 320/640 pixels, optional box-height logging, NCNN export, and exported-folder loading. `requirements-yolo.txt` makes the large detector optional.
- KI-04: `sensor_check` now reports an all-missing sensor as a wiring/voltage-divider warning instead of crashing.
- KI-06: `scripts/pi_setup.sh` installs the Bookworm/OpenCV dependencies, enables I2C when available, adds GPIO/I2C group membership, creates the virtual environment and optional `.env`, and continues with remote YOLO guidance if the optional detector install fails.
- Safety proof includes a regression check that only the control loop and the explicit wheels-off-ground bench tool call `Motors.apply()`.

## How to run

```bash
.venv/bin/python -m scoutbot.tools.motor_check --profile sim
.venv/bin/python -m scoutbot.tools.camcheck --profile mac
.venv/bin/python -m scoutbot.tools.sensor_check --profile pi
bash scripts/pi_setup.sh
```

For real hardware, keep the wheels off the ground and confirm the prompt before running:

```bash
.venv/bin/python -m scoutbot.tools.motor_check --profile pi
```

## Measurements

- Sim motor bench, 2026-09-26: FORWARD reached left/right `+0.60/+0.60`; FORWARD_SLOW `+0.35/+0.35`; turns `-/+0.45`; BACK_UP `-0.35/-0.35` at the halfway check.
- Laptop camera check, 2026-09-26: selected index 1 at 1280x720, 37.3 FPS, frames not black. The configured `.env` index remains honored.
- YOLO laptop benchmark, 2026-09-26: 6.88 FPS at 320 px and 7.75 FPS at 640 px on Apple M1 CPU. NCNN 320 export completed in 12.4 seconds; exported NCNN ran at 16.46 FPS on the laptop. The folder is `yolov8n_ncnn_model` (12.1 MB, ignored and must be copied or exported on the Pi).

## Pi bring-up log

- Waiting for Pi hardware, actual GPIO pins, sensor type, camera model, and motor battery voltage.
- Do not connect an HC-SR04 echo output directly to a Pi GPIO pin. It needs a 5 V to 3.3 V voltage divider.

## Known limits

- The physical motor direction and speed calibration still require wheels-off-ground and floor tests on the actual robot.
- No Pi hardware measurements have been taken yet.
- Pi setup was syntax-checked locally, but not run on Raspberry Pi OS hardware.
- Remote YOLO, live dashboard link-loss, physical camera auto-detection, and Windows DirectShow have not been revalidated in this local-only pass.
