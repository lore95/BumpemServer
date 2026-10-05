# Decisions

Append-only. Format: `## D<n> — <date> — <title>` / Decision / Reason / Alternatives.

## D1 — 2026-09-23 — Keep legacy untouched
Decision: `legacy/` is read-only reference. Firmware work starts from a verbatim copy in `firmware/src/main.ino`.
Reason: thesis results were produced with this code; need a known-good baseline.

## D2 — 2026-09-23 — PlatformIO replaces Arduino IDE
Decision: build/flash via `pio` CLI (`firmware/platformio.ini`, `upload_protocol = teensy-cli`).
Reason: reproducible, scriptable, pinned library deps, no GUI.
Alternatives: arduino-cli (fine, less dependency pinning).

## D3 — 2026-09-23 — Python package is the API; UI is a client
Decision: all device/gait/experiment logic in `bumpem/`. UI and CLI only call it.
Reason: same code path for UI, headless scripts and tests.

## D4 — 2026-09-23 — UI stack (proposed, not final)
Decision: PySide6 + pyqtgraph.
Reason: real-time force plots at ~100 Hz × 4 channels; native desktop, offline lab PC.
Alternatives: NiceGUI (web, easier layout, weaker real-time plotting).

## D5 — 2026-09-23 — Pin firmware platform and libraries
Decision: `platformio.ini` pins teensy@6.0.0, Adafruit MCP4728@1.0.10, Adafruit BusIO@1.17.4 (versions from the first successful build).
Reason: D2 promised pinned deps; unpinned `lib_deps` would pull whatever is latest.
Note: the versions used for the thesis are unknown (Arduino IDE install on the lab PC). Check there if behavior differs.

## D6 — 2026-09-29 — Firmware v1: generic pulse API, host owns semantics
Decision: new `firmware/src/main.ino` implements protocol v1 (`docs/PROTOCOL.md`): per-channel trapezoid `PULSE` (amplitude relative to baseline, delay/rise/dur/fall), runtime `SET/GET` parameters, `ARM`/`RELEASE`/`ESTOP`/`ABORT`, typed lines, ack per command, firmware force clamp, over-force fault, optional watchdog, non-blocking fixed-rate loop. Angles, gait/PTO, sequences stay on the host.
Reason: one board API usable by any front end; porting to another board only needs the pin/DAC/ADC layer. Terms follow `docs/knowledge/perturbation_definitions.md` (duration = start→end incl. ramps; amplitude relative to baseline).
Defaults reproduce v0 control (gains, kff 7.5, 10 ms, no filter). Deliberate differences from v0: boots DISARMED (send `ARM`); channel D disabled by default; `stop` is recoverable (`ARM`); commands work mid-pulse; one `fastWrite` I²C transaction at 400 kHz instead of four at 100 kHz.
v0 remains buildable from `legacy/` via `firmware/legacy/platformio.ini` (`scripts/flash.sh legacy`) as the reference.
Alternatives: keep v0 letter commands and add parameters (no general API); angle-aware firmware (couples board to geometry).

## D7 — 2026-09-29 — Baseline window and balance recovery
Decision: baseline force/SD = first 3 s of the trial (fixed). Balance recovery is decided by the lab's existing algorithm (gait prediction + whole-body angular momentum), plugged into the host as an external detector; bumpem does not implement its own.
Reason: project lead's choice; the recovery algorithm already exists and is validated in the lab.
Consequence: recovery needs whole-body kinematics (Vicon marker/segment data), not only force plates. `bumpem/vicon.py` must stream markers too.
Alternatives: rolling pre-pulse baseline; stride-time placeholder criterion (dropped).

## D8 — 2026-09-29 — Recovery hook and stand-in
Decision: `bumpem/recovery.py` defines `RecoveryDetector` (`start(t)`, `update(t, frame) -> bool`). `Scheduler(recovery=...)` counts foot strikes toward the next perturbation only after `update` returns True; `recovery=None` keeps the MATLAB behavior. Stand-in `FixedWaitRecovery(wait_s)` = fixed time after the perturbation, no default value. Marked `TODO(recovery)` where the lab algorithm goes.
Reason: lets the trial loop and UI be built before the algorithm is integrated (D7).

## D9 — 2026-09-29 — UI is a web page served by a local bumpem server (replaces D4)
Decision: `bumpem serve` runs on the PC the Teensy is plugged into, owns the serial port, and exposes the HTTP/WebSocket API in `docs/API.md`. The UI is a browser page served by it (FastAPI; plain HTML/JS with vendored libraries, no Node build, works offline). Bound to 127.0.0.1 by default.
Reason: same UI on Windows/Linux/macOS; one process owns the port (no v0 port contention); closing the UI does not stop control; MATLAB and future apps use the same API.
Alternatives: PySide6 + pyqtgraph (D4: better real-time plotting, but UI and logic in one process, no API for other apps); NiceGUI (Python-only UI, more version churn).
Open: installer route (`uv` + lockfile proposed), Linux udev rule script, Vicon SDK availability per OS.

## D10 — 2026-09-29 — Server is the product; UI is a separate client in the same repo
Decision: firmware + protocol + `bumpem` package (server) form the product and stay together. The web UI lives in `ui/` and talks to the server only through `docs/API.md`, never by importing `bumpem`. Same repo for now; `ui/` can move to its own repo later without changes.
Reason: firmware, protocol and server change together (CLAUDE.md rule 4); the UI is the replaceable part. Future students can replace the UI or script the server directly. One repo keeps setup simple for a small team.
Alternatives: two repos now (two versions to keep in step, two clones for a new student).

## D11 — 2026-09-29 — Workspace split into BumpemServer and BumpemUI
Decision: the workspace `IBMS_Offenburg/` holds two folders, each shaped as a future repo: `BumpemServer/` (everything that existed: firmware, protocol, `bumpem` package, docs, tests) and `BumpemUI/` (web client). Each has its own README, CLAUDE.md, STATUS.md and DECISIONS.md. The `bumpem/ui/` PySide6 stub, the `ui` extra and the `bumpem-ui` entry point were removed (superseded by D9).
Reason: D10 in folder form; either folder can become its own git repo without moving files.
Contract: `BumpemServer/docs/API.md`. The UI records which API version it targets.

## D12 — 2026-09-29 — Recreate the on-board calibration sketch before flashing
Decision: the unknown load-cell sketch on Teensy 16922250 is recreated from its observed output (pin A1 found by jumper probe; format, 200 ms period and formulas measured) in `firmware/tools/loadcell_check/`, flashable with `scripts/flash.sh loadcell`. The board is flashed only after the project lead accepts the recreation.
Reason: Teensy flash cannot be read back; the project lead wants the sketch kept. A recreation makes flashing v1 reversible.
Alternatives: find the original source (still preferred if it turns up); use a second Teensy for development.

## D13 — 2026-10-01 — Preliminary tests with the drivers' current ESCON configuration
Decision: module C (and other modules) are tested as configured now (module C: Diagnostics passed after the Hall-GND fix). Uploading and comparing each driver's config, and re-running auto-tuning where needed, is deferred to "Before final testing" (`docs/TODO.md`).
Reason: project lead's choice; the configuration is either module-specific tuning or the untuned Stanford reference, both workable for low-force preliminary tests.
Alternatives: check/auto-tune every driver first.

## D14 — 2026-10-02 — Git holds only the code and docs in use
Decision: the repo tracks code (`bumpem/`, `firmware/src`, `firmware/platformio.ini`), tests, `scripts/`, `.md` docs, ESCON `.edc` files and one diagram, `docs/diagrams/cabling-4-modules.png` (4 modules, same cabling per module). Thesis, reference PDFs, photos, `legacy/`, `firmware/legacy/`, `firmware/tools/` and diagram sources/exports stay on disk, listed in `.gitignore`. History squashed to one commit before the first push so the PDFs (≈ 30 MB) never reach the remote.
Reason: project lead's choice: upload only what is used.
Consequence: `legacy/` (MATLAB/v0 reference for rule 5) and the thesis must be shared separately with anyone who needs them.

## D15 — 2026-10-02 — Carrier board: 2-layer PCB, generated from a netlist
Decision: replace the breadboard with `hardware/carrier/`: Teensy 4.1 and MCP4728 on female headers, one 5-way terminal per module (pin order EN, SP+, SP−, GND, F), protection on each force input (1 kΩ series, 1 MΩ pull-down, BAT85 to 3.3 V). 2 layers, through-hole, ordered from a PCB maker; the makerspace helps with ordering and soldering. KiCad files are generated (`netlist.py` → `gen_schematic.py`, `gen_carrier.py`) and checked by `build.sh` (ERC, DRC, schematic parity).
Reason: per-module terminals force the enable, setpoint and force wires to cross; single-sided would need ~10 wire jumpers. Sockets keep Teensy and DAC replaceable. Protection values keep the calibrated 0–3.3 V signal (99.9 %) and make an unplugged input read 0 N.
Alternatives: single-sided milled board with jumpers; perfboard; direct force connection without protection.
Update 2026-10-05: makerspace review → all corners 45° (no 90° bends), ground fill 0.5 mm from other copper (no solder mask there), separate top/bottom PDFs. Their process has no solder mask / silkscreen; plating of holes and vias still to confirm.
Update 2026-10-02 (b): module D confirmed back; board label updated.
Update 2026-10-02: force tracks rerouted under the Teensy and past its end (were 0.37 mm from unused socket pins; now ≥ 1.39 mm from any other pad); all other gaps ≥ 0.74 mm. Module D treated as active (repaired before ordering); its direction stays unlabelled until confirmed.

## D16 — 2026-10-02 — Perturbation angle: Vicon axes, vector split over neighbouring cables
Decision: the API takes a pull direction in Vicon axes seen from above (0 front, +90 left, −90 right, 180 back; normalised to (−180, 180]) and a resultant amplitude above baseline. Modules sit at A +90, B 0, C −90, D 180 (D back confirmed by the project lead). Between two neighbouring modules the amplitude is split as a vector (cos / sin of the angle past the first); on a module's axis that module alone pulls. A module is usable when its channel is on (`ch_X = 1`); other angles are refused (422). Implemented in `bumpem/geometry.py`, used by `POST /api/v1/perturbation` and `bumpem perturb`.
Reason: project lead's choice of convention (Vicon axes); the split reproduces the legacy diagonals (`legacy/Arduino_Script.ino:82`, force × 1/√2 per cable).
Assumptions: horizontal cables at right angles, attached at one point. With B missing, baseline tension leaves a constant pull of `baseline_n` towards D.
Alternatives: clockwise 0–360 convention (the lab's verbal description of the setup); per-module amplitudes only (already available as `POST /pulse`).
