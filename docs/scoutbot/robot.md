# Scoutbot robot notes

## What works

- A1 / KI-01: `motor_check` feeds each action every 0.1 seconds for one second, prints the ramped wheel output halfway through, then stops before the next action.
- The bench tool skips its physical-wheels confirmation when the configured motor driver is `fake`, so it is safe to exercise on the sim profile.

## How to run

```bash
.venv/bin/python -m scoutbot.tools.motor_check --profile sim
```

For real hardware, keep the wheels off the ground and confirm the prompt before running:

```bash
.venv/bin/python -m scoutbot.tools.motor_check --profile pi
```

## Measurements

- Sim motor bench, 2026-09-26: FORWARD reached left/right `+0.60/+0.60`; FORWARD_SLOW `+0.35/+0.35`; turns `-/+0.45`; BACK_UP `-0.35/-0.35` at the halfway check.

## Pi bring-up log

- Waiting for Pi hardware, actual GPIO pins, sensor type, camera model, and motor battery voltage.
- Do not connect an HC-SR04 echo output directly to a Pi GPIO pin. It needs a 5 V to 3.3 V voltage divider.

## Known limits

- The physical motor direction and speed calibration still require wheels-off-ground and floor tests on the actual robot.
- No Pi hardware measurements have been taken yet.
