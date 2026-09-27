# Downbeatfoil Scoutbot integration

This directory preserves an exact source import of [Downbeatfoil/scoutbot](https://github.com/Downbeatfoil/scoutbot) at the revision recorded in `UPSTREAM_COMMIT`.

## How it is used here

The upstream project is the hardware-proven inspiration and reference implementation. Its dashboard, Pi application, cloud relay, and data model informed the main application in this repository, which runs from the top-level `scoutbot/` package.

The active console is intentionally **not** a thin wrapper around the upstream `pi/app.py` because it improves the safety boundary before permitting a responder to drive:

| Capability | Upstream source | Active console in this repository |
| --- | --- | --- |
| Operations view | Dashboard polling Pi state | Live WebSocket console with video, sensor ranges, pose uncertainty, map, survivor triage, rule trace, event feed, and service/sync health |
| Manual takeover | Any drive call immediately overrides autonomy | Explicit **Take control** mode, dead-man heartbeat, link watchdog, motor watchdog, safety gate, and STOP action |
| Data retention | Cloud SQLite ingestion | Local survivor records plus outbox-based sync, usable while offline |
| Local testing | Pi-oriented simulation tools | `sim` profile with synthetic camera, world, motors, survivors, test-only distance controls, and no hardware needed |

The imported tree is a reference snapshot, not a second service to start alongside the active console. Keeping it isolated prevents its direct `POST /api/drive` behavior from bypassing the active console's mode and safety checks.

## Run the local operations console

From the repository root:

```bash
./start.sh sim
# choose 1, or:
python -m scoutbot --profile sim --set sim.world=demo
```

Open <http://localhost:8000>, then:

1. Select **Start auto** to run a simulated search.
2. Use the live camera, map, sensor bars, survivor list, triage, and event feed to assess the situation.
3. Select **Take control** only when a responder must intervene. Drive with the on-screen pad or WASD/arrow keys.
4. Release the key or pad to stop. **STOP** always stops immediately.

For a non-interactive validation run:

```bash
python -m scoutbot --profile sim --set sim.world=demo --headless 20
python -m pytest -q tests
```

Do not run the `pi/` or `cloud/` deployment scripts in this imported directory on a real robot without separately reviewing its wiring, credentials, deployment settings, and operational safety constraints.
