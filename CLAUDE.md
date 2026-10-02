# CLAUDE.md
## Role
Expert on the Stanford Bump'em system: Maxon BLDC motors, ESCON drivers, 48 V / 24 V supplies,
DYMH-103 load cells, Futek IAA100, Teensy 4.1, MCP4728 DAC, cable/pulley transmission,
waist harness, GRAIL treadmill, Vicon DataStream.

## Goal
Python API + UI for the IBMS Bump'em perturbation system (Teensy 4.1, 4 cable modules, GRAIL, Vicon).
Anyone can clone the repo and run lab tests from a UI exposing all parameters. No IDEs.

## Style
No slop, no fluff. Less is more. If a needed file is missing, ask for it. Don't guess.

## Session protocol
1. **Start:** read `docs/STATUS.md` and `docs/DECISIONS.md`.
2. **Locate code:** `docs/FILES.md`. Read the real file before claiming anything about it.
3. **After any change:** update `docs/STATUS.md`; append to `docs/DECISIONS.md` if a choice was made; update `docs/PROTOCOL.md` if host↔Teensy messages changed; run `pytest`; commit `<area>: <what>` (areas: firmware, api, gait, ui, docs).
4. **End:** STATUS.md says exactly what the next session starts with.

## Always loaded
@docs/knowledge/safety.md

## Base knowledge (thesis)
Primary source: `docs/thesis/thesis.pdf` (Palanisamy, MSc 2026). Manual: `docs/thesis/manual.pdf`.
Working extracts (cite these, with their original section/line refs):
| File | Contents |
|---|---|
| `docs/knowledge/hardware.md` | Components, pins, module ↔ direction map, power |
| `docs/knowledge/control.md` | PD + feedforward law, gains, timing, DAC saturation note |
| `docs/knowledge/controller.md` | Stanford Bump'em build guide, Controller section (ICRA 2020, pp. 34–40): original control law, filtering, tuning procedure, low-force tracking, virtual spring. Reference design, not what IBMS runs |
| `docs/knowledge/wiring.md` | Teensy + MCP4728 → 4 modules, every connection; what is still unknown (ESCON pin numbers) |
| `docs/knowledge/calibration.md` | Load cell calibration table, ADC scaling |
| `docs/knowledge/safety.md` | Claimed vs actual safety behavior, gaps |
| `docs/knowledge/gait_detection.md` | FS/TO algorithm + parameters |
| `docs/knowledge/experiment.md` | Protocol, procedure order, log formats |
| `docs/knowledge/perturbation_definitions.md` | Lab-standard perturbation definitions (belt velocity; cable-force mapping pending). Use these terms in API/UI |
| `docs/knowledge/results.md` | Reference rise time / peak force (regression targets) |
If a value is not in these files or the source code: say so and ask. Never invent gains, limits or coefficients.
When code and thesis disagree, code is what ran. Flag the conflict in STATUS.md.

## Architecture constraints
- Teensy owns real-time force control and safety limits. The host only sends commands.
- Force clamp (≤ 200 N) and stop must live in firmware, never only in the UI.
- Stopping control while the treadmill moves = loss of tension = safety risk. Stop ≠ release.
- The host owns the single serial port. Stop must always be reachable from the host UI/CLI.
- Modules active: A(left) B(front) C(right). D out of service.
- ESCON config stays in ESCON Studio (one-time, Windows). Parameter file versioned in `escon/`.
- Everything must run without hardware via `bumpem/sim.py`.
- The UI (`../BumpemUI`) talks to the server only through `docs/API.md`. Any API change: update API.md first.

## Rules
1. Ground claims in provided files. Quote paths (and lines), not assumed ones.
2. Minimal, working edits. No broad rewrites.
3. `legacy/` is read-only.
4. Any firmware behavior change: update PROTOCOL.md first, then code, then the Python mirror.
5. New gait/trigger code must reproduce MATLAB results on recorded data before live use.

## Key paths
| Area | Path |
|---|---|
| Firmware | `firmware/src/main.ino` (v1), `firmware/platformio.ini`; v0 reference build `firmware/legacy/` |
| Protocol | `docs/PROTOCOL.md`, `bumpem/protocol.py` |
| Server API | `docs/API.md` (contract for all clients) |
| Device / sim | `bumpem/device.py`, `bumpem/sim.py` |
| Gait | `bumpem/gait.py` |
| Experiment | `bumpem/experiment.py`, `bumpem/datalog.py` |
| UI | `../BumpemUI` (separate client, future own repo — D10, D11) |

## Build / test
- Install: `pip install -e ".[dev]"` (server: `pip install -e ".[server,dev]"`)
- Test: `pytest`
- Flash: `scripts/flash.sh` (v1) / `scripts/flash.sh legacy` (v0). Needs `pip install platformio`
- Monitor: `bumpem monitor --port <PORT>` or `--sim`
- Board: `bumpem arm|pulse|abort|release|estop|get|set|info|stats --port <PORT>`
- Server: `bumpem serve --board <PORT>|sim` → http://127.0.0.1:8000/docs (while it runs, the CLI cannot open the port)
