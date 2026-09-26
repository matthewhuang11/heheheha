# Robot Brain Laptop Harness

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python demo.py
python demo.py --fake-vlm
python demo.py --image path.jpg
python demo.py --once
pytest -q
```

On macOS, grant **Camera** permission to the terminal or IDE running `demo.py`.

Keys: `1`/`2`/`3` select left/center/right, `=` and `-` change it by 10 cm, `0` toggles no echo, `r` resets, `v` toggles VLM offline, space forces a VLM call, `4`–`9` select canned reports in `--fake-vlm`, and `q` quits. Decisions append to `logs/run.jsonl`.

## Decision policy and testing (v1.1)

Rules: `robot/brain.py` (pure). Filters and safety wrappers: `robot/sensing.py` (median-of-5, no-echo, time-to-collision), `robot/scene_filter.py` (fast to believe danger, slow to believe "clear"), `robot/camera_health.py` (dark / blocked / frozen camera = treated as no camera), `robot/controller.py` (hysteresis, turn hold, stuck recovery), `robot/config.py` (all thresholds, derived from robot speed), `robot/metrics.py` (what the dashboard tracks).

- Live dashboard: double-click `run_web.command` (real camera) or `run_web_sim.command` (fake camera + random sensors). The "Health & what we track" card shows the numbers that matter.
- Measure Gemini's accuracy on your own frames: `run_capture.command` (save frames), `run_eval_label.command` (Gemini pre-fills labels), fix `dataset/labels.json` by hand, then `run_eval_score.command`.
- Tests: `python -m pytest -q tests`.
