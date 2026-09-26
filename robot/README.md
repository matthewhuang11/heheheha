# DRR V1 Runtime

This package implements the **laptop-verifiable** controlled V1 software baseline. It is simulation-first and displays `RESEARCH TEST ONLY – NOT FOR RESCUE OR PUBLIC USE`.

Run software tests with `python -m pytest -q` from this directory. The package provides deterministic fake sensors, camera frames, canned VLM responses, strict VLM validation, fail-closed decision and safety control, lifecycle latching, permit-enforced fake motors, JSONL logging, and `tools/replay.py`.

## Acceptance boundary

This software is not authorization to operate hardware. The V1 physical gates still require the documented bench and field evidence: hardwired E-stop energy-removal timing, real sensor calibration and crosstalk, actual motor-speed/acceleration/permit timing, camera/provider behavior, power-fault testing, ODD inspection, and the supervised 300-second field run. Do not connect a real motor driver through this package without implementing and verifying the required hardware layer and procedures.
