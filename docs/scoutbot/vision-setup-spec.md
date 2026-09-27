# Scoutbot Vision Setup Spec

Status: draft v0.1, 2026-09-27
Scope: making sure the robot's "eyes" are set up correctly, from the camera to what the responder sees on the dashboard.
Repo: `heheheha`, branch `agent/robot`. Paths are relative to the repo root.

Assumption: "the visual thing" means the vision pipeline (camera, video stream, person detection, scene description, and the picture the dashboard draws). The web-app screens are covered in `data-and-webapp-spec.md`. Tell me if you meant something else.

## 1. What "set up properly" means

A vision setup is good when all of these are true, and we can prove each one with a number:

1. The camera opens by itself and gives a clear, correctly lit picture at a steady frame rate.
2. The video reaches the dashboard with low delay.
3. A person in view is found quickly, and not by mistake.
4. "Left / center / right" and "near / mid / far" match reality, because the survivor map and the safety rules depend on them.
5. The boxes drawn on the video line up with the people in it.
6. If the camera or a model fails, the robot notices and falls back to distance sensors only.

## 2. The pipeline as it exists today

```
Camera (OpenCV)            scoutbot/hw/camera_opencv.py      open_best_camera(): tries the configured index, then 0-3
   |
Runtime.camera_loop        scoutbot/runtime.py               resize to 640 wide, JPEG quality 80, camera health check
   |                                                         (runs on the main thread)
   +--> /video.mjpg        scoutbot/server/app.py            MJPEG stream, about 15 fps, for the dashboard
   |
   +--> CameraHealth       robot/camera_health.py            too dark / washed out / no contrast / frozen feed
   |
   +--> YOLO (people)      scoutbot/perception/yolo.py       robot | remote laptop worker | sim | off
   |        confirm: 2 of the last 3 frames; near/mid/far from box height
   |
   +--> Gemini (scene)     robot/vlm.py                      every ~2 s, only when online and camera healthy
            |
            v
   Fuser                   scoutbot/perception/fusion.py     YOLO can add a person Gemini missed, never remove one
            |
            v
   Brain rules + safety gate                                 the AI never drives; rules do
            |
            v
   Survivor registry       scoutbot/survivors/registry.py    position guess from bearing + distance bucket
```

Key facts from the code that this spec depends on:

- The frame is shrunk to 640 px wide before anything else sees it. YOLO then runs at `imgsz` 320 by default.
- An unhealthy camera is treated like a missing camera: sensors only, speed capped at slow. So a bad picture costs speed, not safety.
- "Where" is just thirds of the image width: left under 1/3, right over 2/3. "Near / mid / far" comes from box height as a fraction of image height (`near_frac` 0.5, `mid_frac` 0.2).
- The survivor position guess assumes a side bearing of 25 degrees for left/right and fixed distances: near 70 cm, mid 200 cm, far 400 cm (`survivors.bearing_deg`, `survivors.dist_cm`). These are guesses until measured on the real camera.
- The camera is a GoPro (confirmed by Matthew, 2026-09-27; exact model still to record). A GoPro configured in **USB webcam/UVC mode** appears as an ordinary video device and uses `hw.camera: opencv`. A GoPro using its network stream still needs its model-specific URL/source configuration. The new `hw.camera: picamera2` source is for a ribbon-cable Pi Camera Module, not a GoPro.

## 3. Setup steps and checks

Do these in order on the real Pi and camera. Each has a pass condition.

### 3.1 Camera opens and is the right one

Commands (on the Pi, in the project folder):

```
.venv/bin/python -m scoutbot.tools.camcheck --profile pi
```

Pass when it prints an index, a resolution, FPS, `black=no`, and saves 20 sample frames to `data/camcheck/`. Open two of the saved frames and look at them: right camera, right way up, not mirrored.

Things to check:

- Which type of camera it is. A USB webcam appears as `/dev/video0` and works with the current code. A ribbon-cable Pi Camera Module on current Raspberry Pi OS usually does not open through plain OpenCV `VideoCapture(0)`; it needs `picamera2` (or a compatibility layer). If `camcheck` finds nothing and a ribbon camera is installed, that is why. Fix: add a `hw.camera: picamera2` source (section 6, item V1).
- Set `CAMERA_INDEX` in `.env` once you know the right one so the search does not run each start. (Note: `settings.load` ignores `CAMERA_INDEX` for the `pi` profile; use `hw.camera_index` in `config/profiles/pi.yaml` instead.)
- Permissions on the Pi: the user must be in the `video` group (`groups` shows it).

### 3.2 Picture quality

Pass conditions, measured from the saved frames and `CameraHealth` values:

| Check | Pass | Why |
| --- | --- | --- |
| Brightness (mean, 0-255) | 40 to 220 | `CameraHealth` flags under 25 as too dark, over 235 as washed out |
| Contrast (std dev) | above 12 | Lens cap or covered lens shows as no contrast |
| Sharpness (Laplacian variance) | above 30 in normal light | Advisory only. Blur usually means focus or motion |
| Frozen feed | never for 2 s | Detects a hung camera |
| Frame rate | at least 10 fps at the size used | Below that, detection lags and the dashboard stutters |
| Exposure | fixed or auto, but no strobing | Flicker under indoor lights can trip "washed out" or "dark" |

Test in the demo room lighting, and once in dim light and once with a window behind the person. Write the results down. If auto-exposure is unstable, lock exposure and gain in the camera settings.

### 3.3 Mounting and field of view

The distance and left/right logic only works if the camera is aimed sensibly.

- Mount at a fixed height (write it down; suggested 15 to 30 cm for a small robot), tilted level or slightly down. Tighten it so it cannot shift while driving.
- Measure the horizontal field of view (FOV) of the camera. Stand a marker at the far left and far right edges of the frame at 2 m and measure the width to get the angle.
- Check that the three distance sensors point roughly where the image thirds are. Left sensor is at +30 degrees, right at -30 degrees in the map code. If the FOV is much wider or narrower than about 60 degrees, the thirds and the sensors will not match.
- Keep motors and wheels out of the frame. Check nothing on the robot blocks the lens edge.

Record: camera model, height, tilt, measured FOV, resolution. Put it in `docs/scoutbot/robot.md`.

### 3.4 Video to the dashboard

```
.venv/bin/python -m scoutbot --profile pi
```

Then open `http://<pi-ip>:8000` from a laptop on the same network and check:

| Check | Pass |
| --- | --- |
| Video appears within 3 s of page load | yes |
| Frame rate on the dashboard | at least 10 fps |
| Delay (glass-to-glass): wave a hand, or show a running stopwatch to the camera and compare with the same stopwatch on screen | under 500 ms on the local network, under 1 s on a hotspot |
| Two viewers at once (laptop and phone) | both work; robot control loop does not slow |
| Wi-Fi drops for 10 s then returns | video reconnects without restarting the robot |
| CPU use on the Pi while streaming plus YOLO | under 85% average; temperature under 75 C (Pi throttles at 80 C) |

If it lags: lower JPEG quality (80 to 60), lower stream width (640 to 480), or lower the stream rate. MJPEG is the simplest option; the research notes suggest moving to WebRTC only if the delay hurts driving. It matters more now that manual driving depends on the video.

Note: the remote YOLO worker (when used) also reads `/video.mjpg`, so it counts as a second viewer.

### 3.5 Person detection (YOLO)

Decide where it runs, by measurement:

```
.venv/bin/python -m scoutbot.tools.yolo_bench --profile pi --imgsz 320
```

- Pass: at least 3 fps on the Pi with the NCNN model (`yolov8n_ncnn_model`). The exported folder is not in git; export it on the Mac (`yolo export model=yolov8n.pt format=ncnn imgsz=320`) and copy it to the Pi.
- Fail (under 3 fps): set `perception.yolo.where: remote` and run `python -m scoutbot.perception.worker_remote --robot http://<pi-ip>:8000` on the laptop. Then the Pi needs the video stream working well (3.4) more than ever.

Detection quality checks (use a person, a chair, a coat on a chair, a poster of a person):

| Check | Pass |
| --- | --- |
| A person standing at 1 m, 2 m, 3 m appears with a box within 1 s | yes at 1 and 2 m; 3 m best-effort |
| Person lying down or half hidden behind a chair at 1.5 m | note the result (a known weak spot) |
| False alarms over 5 minutes with no person in view | 0 confirmed detections |
| Flicker: a stationary person stays detected | at least 90% of frames once confirmed |
| Poster / photo of a person | note the result; decide if acceptable |

If false alarms appear, raise `min_conf` (0.45 to 0.55). If real people are missed, lower it or raise `imgsz` to 480/640 if the frame rate allows.

### 3.6 Calibrate near / mid / far and left / right

This ties vision to the map, and it is the part most likely to be wrong out of the box.

1. Stand at 0.7, 1.0, 1.5, 2.5 and 4.0 m from the camera, facing it. At each distance, log the YOLO box height as a fraction of image height (the A4 task in the parallel plan asked for a `--log-boxes` flag on `yolo_bench`; add it if missing).
2. Set `perception.yolo.near_frac` and `mid_frac` so near means under about 1 m and mid about 1 to 2.5 m. Update `test_fusion.py` if the boundaries move.
3. Stand at the far left, center and far right at 2 m. Confirm the thirds put you in left, center and right.
4. Compare the survivor pin on the dashboard map with where the person really is (tape measure). Adjust `survivors.dist_cm` and `survivors.bearing_deg` until it is within about 50 cm at mid range. Write the measured values down.

### 3.7 Gemini scene description

Only when online and the camera is healthy. Checks:

- `python check_gemini.py` from a machine with internet returns a valid report.
- Latency per call under 4 s (dashboard shows it). The station notes measured about 1.5 s on the laptop.
- With Wi-Fi off, the dashboard shows Gemini offline and the robot keeps driving on sensors and YOLO.
- Timeout stays at 10 s or more for talk calls (the API rejects shorter deadlines).
- Frames are sent at 640 px wide; confirm no faces or sensitive scenes are being stored beyond what the data spec allows.

### 3.8 The dashboard picture

- Boxes line up with people: walk across the frame and watch the box follow. The code saves the exact frame each set of boxes came from (`det_frame`), so any drift is a client-side drawing problem (scaling or an old frame), not a detection problem.
- The video keeps its aspect ratio at phone width (390 px) and desktop width.
- Camera status chip shows the reason when unhealthy ("too dark", "frozen feed").
- Sim vs real: the sim draws its own view (labelled "SIMULATED VIEW"). Make sure a real robot cannot be mistaken for the sim.

## 4. Failure behaviour to prove

Each of these should be tested on purpose, with the wheels off the ground first:

| Fault | Expected result |
| --- | --- |
| Cover the lens | Health goes unhealthy within 2 s ("no contrast"); robot caps to slow and relies on sensors |
| Unplug the camera (USB) | "no frames from camera" reason appears; robot does not crash; recovers on replug or restart |
| Kill YOLO / model load error | Status shows "unavailable"; Gemini fallback is used; robot keeps running |
| Turn Wi-Fi off | Gemini offline, YOLO (on robot) still works; dashboard link loss stops motors per the link watchdog |
| Camera returns black after warm-up | `open_best_camera` moves to the next index at start; mid-run black frames trip health |

## 5. Acceptance checklist (sign off before the demo)

- [ ] Camera model, height, tilt, FOV, resolution recorded in `robot.md`
- [ ] `camcheck`: not black, at least 10 fps
- [ ] Picture quality table passed in demo lighting
- [ ] Dashboard video: at least 10 fps, delay under 500 ms (LAN)
- [ ] YOLO at least 3 fps (on Pi) or remote worker running
- [ ] 0 false detections in 5 minutes of empty scene
- [ ] near / mid / far and left / center / right calibrated and written down
- [ ] Survivor pin within about 50 cm of the truth at mid range
- [ ] Gemini latency and offline fallback verified
- [ ] All five failure tests in section 4 pass
- [ ] Sample frames and measurements saved (not committed if they show people)

## 6. Implemented setup support

| # | Change | Status |
| --- | --- | --- |
| V1 | `hw.camera: picamera2` for a ribbon Pi Camera Module, BGR conversion, lazy import | Implemented. Set `hw.camera: picamera2` only when the physical camera is a Pi Camera Module and `picamera2` is installed. GoPro USB webcam mode remains `opencv`. |
| V2 | `python -m scoutbot.tools.vision_check --profile pi` | Implemented. Measures health, brightness, contrast, sharpness, capture FPS, saves two samples, and runs the configured on-device YOLO benchmark. Glass-to-glass delay remains a required manual stopwatch check. |
| V3 | `yolo_bench --log-boxes` and distance calibration | Already implemented. `scoutbot.tools.distance_tune` captures the distance-test set; `yolo_bench --log-boxes` prints normalized box heights. |
| V4 | Camera metrics in `Runtime.state()` | Implemented as `vision.camera_type`, `camera_index`, `capture_fps`, `last_frame_age`, and `stream_fps_target`; the dashboard displays source and capture FPS. |
| V5 | Pi `CAMERA_INDEX` override | Implemented. `CAMERA_INDEX` now applies to `pi` as well as laptop profiles. |
| V6 | Record / folder replay | Already implemented through `--record` and `hw.camera: folder`. Capture a 60 s real-room clip after the hardware setup passes, then retain an approved non-sensitive clip as a local regression fixture. |

## 7. Open questions

1. What camera is on the robot: GoPro (which model, and does it appear as a webcam?), USB webcam, or Pi Camera Module? This decides V1.
2. Is the Pi 4 fast enough for YOLO on-board, or will the laptop run it? (Answered by the 3.5 benchmark.)
3. What is the demo room like (floor, lighting, distances)? Sets the thresholds.
4. Is a wide-angle lens in use? It changes the "thirds" assumption and the position guesses.
5. Do we want the sim view visible next to the real view in the web app, or only the real one?
6. Who may see snapshots and video, and for how long are they kept? (See the data spec.)
