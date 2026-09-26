# Scoutbot hardware hand-off (for the hardware team)

One page: how to wire the robot so the software works on first power-up, and what to send back.
**Every GPIO number below is a PLACEHOLDER from `config/profiles/base.yaml` / `pi.yaml`: confirm or change it, then tell us.**
GPIO numbers are **BCM** (the "GPIO17" names), not physical pin numbers. Physical pin numbers are given for convenience.

## 1. Parts (as the software expects them)

| Part | Expected | Notes |
| --- | --- | --- |
| Computer | Raspberry Pi 4 (2 GB+), Raspberry Pi OS 64-bit (Bookworm), SSH on | heatsink or fan: YOLO runs the CPU hot |
| Motor driver | L298N dual H-bridge, **ENA/ENB jumpers removed** (we drive them with PWM) | left motor pair on channel A, right pair on channel B |
| Motors | 4x TT gear motors (2 per side, in parallel) | |
| Distance sensors | 3x HC-SR04 (left / center / right), **or** 3x VL53L0X ToF on I2C | we support both (`hw.distance: hcsr04 | tof`) |
| Floor ("cliff") sensor | optional 4th HC-SR04 or VL53L0X pointing **down**, ~5 cm ahead of the front wheels, ~3-6 cm above the floor | `hw.cliff: hcsr04 | tof`; the robot backs up when it reads > 15 cm |
| Camera | USB webcam, or Pi Camera v2/v3 | USB webcam is the simplest (OpenCV index 0) |
| Power | separate motor battery (6-12 V for the L298N) + Pi supply 5 V / 3 A (USB-C power bank or buck converter) | **common ground** between Pi, L298N and sensors |
| Kill switch | a physical switch in series with the **motor battery +** | always within reach during tests |

## 2. Wiring table (placeholders, BCM)

### L298N -> Pi
| L298N pin | Pi GPIO (BCM) | Physical pin | Config key |
| --- | --- | --- | --- |
| ENA (left PWM) | GPIO12 | 32 | `hw.pins.left.en` |
| IN1 (left forward) | GPIO5 | 29 | `hw.pins.left.fwd` |
| IN2 (left backward) | GPIO6 | 31 | `hw.pins.left.back` |
| ENB (right PWM) | GPIO18 | 12 | `hw.pins.right.en` |
| IN3 (right forward) | GPIO13 | 33 | `hw.pins.right.fwd` |
| IN4 (right backward) | GPIO19 | 35 | `hw.pins.right.back` |
| GND | any GND | 6 / 9 / 14 ... | common ground with the motor battery |
| 12V / VS | motor battery + (through the kill switch) | | never the Pi's 5 V |

If a wheel spins the wrong way, **don't rewire**: swap `fwd` and `back` for that side in `pi.yaml`.

### HC-SR04 distance sensors
| Sensor | Trig -> GPIO | Echo -> divider -> GPIO | Config |
| --- | --- | --- | --- |
| left | GPIO23 (pin 16) | GPIO17 (pin 11) | `hw.pins.trig[0]`, `hw.pins.echo[0]` |
| center | GPIO24 (pin 18) | GPIO27 (pin 13) | `[1]` |
| right | GPIO25 (pin 22) | GPIO22 (pin 15) | `[2]` |
| cliff (optional) | GPIO26 (pin 37) | GPIO21 (pin 40) | `hw.cliff_pins.trig/echo`, `hw.cliff: hcsr04` |

- VCC to **5 V** (pin 2 or 4), GND to GND.
- **Echo is a 5 V signal and will damage the Pi. Every echo needs a voltage divider:** Echo -> **1 kΩ** -> GPIO, and GPIO -> **2 kΩ** -> GND
  (gives 3.3 V). 1.8 kΩ or 2.2 kΩ also work for the bottom resistor.

### VL53L0X ToF (alternative)
| Sensor | XSHUT -> GPIO | I2C address (set by software at boot) |
| --- | --- | --- |
| left | GPIO4 (pin 7) | 0x30 |
| center | GPIO16 (pin 36) | 0x31 |
| right | GPIO20 (pin 38) | 0x32 |
| cliff (optional) | GPIO7 (pin 26) | 0x33 |
- All share SDA = GPIO2 (pin 3), SCL = GPIO3 (pin 5), 3.3 V (pin 1), GND. Keep GPIO2/3 free of anything else.
- VL53L0X range is ~1.2-2 m; beyond that the software reports "far" (200 cm). VL53L1X needs a small code change: tell us.

## 3. Sensor angles (from our simulator study, KI-39)
- **Mount the side sensors at 45° left and 45° right** of straight ahead, center sensor straight ahead, all at the same height
  (~10-15 cm above the floor), at the front edge of the chassis.
- In 60 simulated 5-minute runs, ±45° hit walls/boxes **9** times vs **50** times with ±30° (the robot's sides clip corners the
  sensors can't see). If you mount differently, send us the angles: it's one config line (`hw.sensor_angles`).

## 4. Safety wiring (please do all three)
1. **Kill switch** in series with the motor battery +. It cuts the motors, not the Pi.
2. **Pull-down resistors (10 kΩ) from ENA and ENB to GND.** If the Scoutbot program crashes or the Pi reboots, the GPIO pins float;
   without pull-downs the L298N can keep driving. With them, the motors stop. (Our software also stops the motors within 0.5 s
   if its control loop stalls, but a killed process can't do that: the pull-downs are the hardware backstop.)
3. **Common ground**, and the motor battery never connected to the Pi's 5 V.

## 5. Send us back (please)
- [ ] Actual GPIO numbers for every row above (or "same as placeholder").
- [ ] Distance sensor model (HC-SR04 / VL53L0X / VL53L1X / other) and the mount angles.
- [ ] Whether there is a cliff sensor, and which kind.
- [ ] Camera model (USB webcam model, or Pi Camera v2/v3).
- [ ] Motor battery voltage and type; how the Pi is powered.
- [ ] Photos of the wiring (top and side), and the resistor values used on each echo line.
- [ ] Wheel base (cm between left and right wheels) and wheel diameter.

## 6. First power-up, in this order (we run these; takes ~30 min)
Wheels **off the ground** until step 6.
```bash
git clone git@github.com:matthewhuang11/heheheha.git scoutbot && cd scoutbot
bash scripts/pi_setup.sh                                   # packages, I2C, venv; safe to run again
.venv/bin/python -m scoutbot.tools.camcheck --profile pi    # saves frames to data/camcheck
.venv/bin/python -m scoutbot.tools.yolo_bench --profile pi --imgsz 320   # < 3 FPS -> YOLO runs on the laptop instead
.venv/bin/python -m scoutbot.tools.sensor_check --profile pi             # tape measure at 20 / 50 / 100 cm
.venv/bin/python -m scoutbot.tools.motor_check --profile pi              # WHEELS OFF THE GROUND; types "yes" first
# 6. floor calibration: time 1 m forward / slow / back-up and one full turn -> motion.* in pi.yaml
.venv/bin/python -m scoutbot --profile pi                   # dashboard from the laptop: http://<pi-ip>:8000
# 7. dead-man checks: laptop Wi-Fi off while driving -> stops < 0.5 s; kill -9 the program -> stops (needs the pull-downs)
# 8. first slow autonomous run toward a wall
```
