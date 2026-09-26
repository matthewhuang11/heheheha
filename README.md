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

## Scoutbot quick start

Install: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
Run Mac webcam: `python -m scoutbot --profile mac`; simulator: `python -m scoutbot --profile sim --set sim.world=demo`; offline: `python -m scoutbot --profile mac --set net.force_offline=true`. Open `http://localhost:8000`.
Tools: `python -m scoutbot.tools.camcheck`, `python -m scoutbot.tools.yolo_bench`, and `python -m scoutbot.tools.ollama_check`. On a Pi run `bash scripts/pi_setup.sh`, then use `--profile pi` and the sensor/motor checks. The motor check requires wheels off the ground and typed confirmation.
