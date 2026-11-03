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
Consequence: recovery needs whole-body kinematics (Vicon marker/segment data), not only force plates. `bumpem/vicon.py` must stream markers too. (Deferred by D31: force plates only for now.)
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
Update 2026-10-05 (b): module connectors changed to pluggable Phoenix MSTB 2,5 (board header MSTB 2,5/5-GF-5,08 1776537, cable plug MSTB 2,5/5-STF-5,08 1778014, both with screw flanges; optional coding CP-MSTB 1734634) so a module cable pops in and locks instead of 5 screws per module. Flanges make each header 35.7 mm wide → board 154 × 96 mm. Pin order unchanged (1 EN … 5 F), now left to right.
Update 2026-10-05: makerspace review → all corners 45° (no 90° bends), ground fill 0.5 mm from other copper (no solder mask there), separate top/bottom PDFs. Their process has no solder mask / silkscreen; plating of holes and vias still to confirm.
Update 2026-10-02 (b): module D confirmed back; board label updated.
Update 2026-10-02: force tracks rerouted under the Teensy and past its end (were 0.37 mm from unused socket pins; now ≥ 1.39 mm from any other pad); all other gaps ≥ 0.74 mm. Module D treated as active (repaired before ordering); its direction stays unlabelled until confirmed.

## D16 — 2026-10-02 — Perturbation angle: Vicon axes, vector split over neighbouring cables
Decision: the API takes a pull direction in Vicon axes seen from above (0 front, +90 left, −90 right, 180 back; normalised to (−180, 180]) and a resultant amplitude above baseline. Modules sit at A +90, B 0, C −90, D 180 (D back confirmed by the project lead). Between two neighbouring modules the amplitude is split as a vector (cos / sin of the angle past the first); on a module's axis that module alone pulls. A module is usable when its channel is on (`ch_X = 1`); other angles are refused (422). Implemented in `bumpem/geometry.py`, used by `POST /api/v1/perturbation` and `bumpem perturb`.
Reason: project lead's choice of convention (Vicon axes); the split reproduces the legacy diagonals (`legacy/Arduino_Script.ino:82`, force × 1/√2 per cable).
Assumptions: horizontal cables at right angles, attached at one point. With B missing, baseline tension leaves a constant pull of `baseline_n` towards D.
Alternatives: clockwise 0–360 convention (the lab's verbal description of the setup); per-module amplitudes only (already available as `POST /pulse`).

## D17 — 2026-10-05 — The server serves the browser UI; websockets is a server dependency
Decision: `bumpem serve` mounts `../BumpemUI/web` at `/ui/` (`--ui PATH`), `/` redirects there (BumpemUI U2). The `server` extra now includes `websockets`: plain uvicorn rejects WebSocket requests (404, "No supported WebSocket library"), so `/api/v1/stream` never worked outside the test client.
Reason: one URL, no CORS; the live stream is required by the UI.
Consequence: reinstall the extras once: `pip install -e ".[server,dev]"`.

## D18 — 2026-10-05 — The server sets the channels to the mounted modules at connect
Decision: `bumpem serve --modules ACD` (default `ACD`) switches ch_A..ch_D at connect: listed modules on, others off (only while DISARMED). `--modules ""` keeps the firmware defaults (A, B, C on, D off).
Reason: the firmware's power-up defaults date from when D was out of service; on the real board the UI showed the front (B, not installed) reachable and the back (D, installed) refused, so a back pull reached only A. Fixing it in the server needs no re-flash and is one option to change when B is mounted.
Alternatives: change the firmware defaults (PROTOCOL.md + re-flash); tick channels in the UI after every power-up.

## D19 — 2026-10-05 — Testing and production modes
Decision: `bumpem serve --testing` / `--production` (default). Testing: `POST /api/v1/test/pull` does one open-loop pull on one module (save params → gains 0, kff 2, baseline 0, cap = force, arm_ms 0, only that module → ARM → PULSE → RELEASE 0 → restore params); arm / pulse / perturbation refused. Production: the full UI (arm with force feedback, perturbations); test pulls refused. Error code `wrong_mode` (409). UI: `/ui/testing.html` vs `/ui/`.
Reason: the project lead wants a plain "does each motor react?" check without arming or constant tension, separate from the arming / feedback workflow; mixing both on one page caused confusion.
Alternatives: one page with a test card (tried, confusing); CLI only.

## D20 — 2026-10-12 — Saved settings, applied at connect
Decision: one JSON file (`bumpem serve --settings`, default `BumpemServer/settings.json`, not in git) holds the board parameters; `POST /api/v1/settings` stores the board's current values, and the server writes the file to the board at every connect, only while DISARMED or ESTOP (else when it next disarms). Not stored: `ch_*` (owned by `--modules`), `wd_ms`, `loop_ms`, `tel_div`.
Reason: parameters live in the Teensy's RAM; every replug silently brought back kff 7.5, baseline 5 N and zero offsets 0 (closed loop then holds ~15 N instead of the 2 N asked).
Alternatives: store in the Teensy's EEPROM (firmware + PROTOCOL change, re-flash); CLI flags per parameter; the UI re-sends values (every client would need it).

## D21 — 2026-10-12 — Recording on the server
Decision: `POST /api/v1/log/start|stop` writes full-rate telemetry (`force_<ts>[_label].csv`, header of `bumpem/datalog.py`) and an events file (board events + one `CMD` row per pulse the server sent, as JSON) to `--log-dir` (default `BumpemServer/Logs/`, not in git).
Reason: closed-loop tests need target vs measured at the board rate; the stream is thinned to 30 Hz for display, and the server already sees every line.
Alternatives: log in the UI (browser, thinned data); always-on logging (fills the disk, no labels); a separate logger program (cannot share the serial port).
---

## D22 — 2026-10-19 — Access control: the server stays on this computer, no authentication
Decision: the server runs on the computer the operator sits at (setup 1: Teensy on USB, Vicon over Ethernet, browser on the same PC) or on the Vicon PC itself (setup 3). It listens on 127.0.0.1 only; `bumpem serve` refuses a non-loopback `--host` unless `--allow-network` is given. No login or token.
Reason: the project lead wants no unauthorized connections; with the browser on the same computer nothing else needs to connect, so the OS login is the access control and STOP stays reachable without credentials. The Vicon network still has to reach the server's computer (DataStream is Ethernet), so binding to loopback is what keeps the lab network out.
Alternatives: a separate operator laptop over a direct Ethernet cable with a token, one controlling client, STOP open to all (setup 2: API change, kept for later if the operator cannot sit at the server); USB networking between two PCs (same as Ethernet, fiddlier); TLS (pointless without network access).

## D23 — 2026-10-26 — Carrier board force inputs: 1 MΩ pull-up in D1–D4, R5–R8 empty
Decision: as built, each force input has R1–R4 1 kΩ in series, 1 MΩ from the input to 3.3 V in the D1–D4 places (fitted instead of the BAT85 by mistake, kept on purpose) and nothing in R5–R8 (1 MΩ pull-down; ground holes not drilled). Do not fit R5–R8 or swap D1–D4 to BAT85 without revisiting this.
Reason: with an amplifier connected the pull-up costs ≤ 3 mV (≤ 0.2 N near 0 N, removed by Zero sensors). A force cable that comes loose reads ≈ 200 N: the controller drives that motor to 0 A (kp_track 0.24 × (5 − 200) + feed-forward 4.7 < 0) and the over-force check (≥ fault_n 195 N for 20 ms, `main.ino`) trips FAULT and aborts the pulse. With the designed pull-down a loose cable reads 0 N and the controller keeps pulling (~6 A at baseline 5 N); with both fitted it reads ≈ 100 N and trips nothing.
Alternatives: design as drawn (pull-down + BAT85 clamp: over-voltage protection if an IAA100 were set to 0–10 V, but unsafe on a loose cable); BAT85 only (protection, input floats when unplugged). The IAA100s are trimmed to 0–3.3 V (`docs/knowledge/calibration.md`), so the clamp would not act in normal use.

## D24 — 2026-10-26 — Carrier board for the makerspace mill: single-sided, wire links, force pull-up to the enable line
Decision: second carrier layout `hardware/carrier/milled/` for the HS Offenburg PCB mill (no plating, no solder mask): all copper on the bottom, no ground fill, unused socket pins as bare holes, 7 wire links (W1–W7) instead of vias, 1 kΩ resistors used as bridges. Force input: 1 kΩ series, 1 MΩ from the plug-side force pin to the same module's enable line. v1 (`hardware/carrier/`) stays the design for a professional maker (Aisler / JLCPCB).
Reason: the v1 board milled there needed top-side joints under the sockets, hand-made vias and an SCL wire, and its 0.5 mm ground-fill gaps let solder short VIN to ground. A 1 MΩ to 3.3 V on each input (D23) would need a 3.3 V rail across the single layer (more links); tied to the enable line it keeps D23's behaviour where it matters (armed: loose cable → ≈ 200 N → FAULT) and reads 0 N when disarmed.
Alternatives: order v1 from a professional maker (best, ~€25–45, 5–10 days); greedy auto-routing of the single layer (7–17 links, nets boxed in); keep D23's 3.3 V pull-up (≈ 3 more links).

## D25 — 2026-10-27 — Sensor gain range 0.5–3 (firmware 1.0.1)
Decision: `gain_A`..`gain_D` accept 0.5–3 (was 0.5–2), in firmware, PROTOCOL.md and the simulator. Firmware version 1.0.1.
Reason: module B now has a 200 kg load cell on an IAA100 set up for the 100 kg cells. 12 kg check (B zeroed, 0.4 N empty): 56.0 N for 117.7 N → `gain_B` 2.12 needed; the IAA100 SPAN trim is at its end stop (≈ 112 N with `gain_B` 2).
Alternatives: `gain_B` 2 (B reads ≈ 5 % low; with force feedback B pulls ≈ 5 % above the command); change the IAA100 coarse gain switches (switch table not in the repo).

## D26 — 2026-10-27 — Test pull limit 150 N (was 30 N)
Decision: `POST /test/pull` accepts `force_n` up to 150 N; testing page input up to 150.
Reason: 2026-10-27 the modules gave weak or no pulls on the dummy and the user needs larger open-loop pulls to compare (30 vs 50+ N) while finding the cause. Open loop (`kff` 2, `i_full` 30): DAC full scale at ≈ 120 N, so 150 N is a full-current pull; `fmax_n` = `force_n`, the fault cut-out stays as set.
Alternatives: keep 30 N and test larger pulls in production mode (open-loop settings by hand).

## D27 — 2026-10-30 — Recording downloadable through the API
Decision: `GET /api/v1/log/file?kind=force|events` returns the last finished recording's CSV as a download; new error code `not_found` (404). The production page becomes the lab's test UI (BumpemUI U6): Record → Stop downloads the force CSV.
Reason: after the 2026-10-29 lab meeting the user wants pulls by force + angle with the force recording exported as CSV at Stop; the browser can only get the file through the API (and the server PC may not be the one with the browser).
Alternatives: build the CSV in the browser from the stream (30 Hz, not the full board rate); open the Logs folder by hand.

## D28 — 2026-11-02 — Offline Windows bundle: per-user Python 3.12 + venv, repos as source
Decision: `scripts/build_bundle.sh` makes a folder/zip for the Vicon PC: python.org 3.12.10 installer run per-user (no admin), a venv inside the bundle, packages from win_amd64 wheels pinned to the versions tested on the Mac, both repos as plain source (`git archive HEAD`); the server runs as `python -m bumpem.cli serve` from `BumpemServer/` (no install of `bumpem`, so the defaults for `settings.json`, `Logs/` and `../BumpemUI/web` resolve as on the Mac). Teensy is never flashed from that PC.
Reason: the Vicon network has no internet and the PCs are locked down (TODO "Offline install"); the project lead approved starting tests there (user, 2026-11-02).
Alternatives: PyInstaller exe (larger, AV false positives under ESET); conda (bigger, needs its own installer); installing `bumpem` as a wheel (paths would point into site-packages).

## D29 — 2026-11-02 — Bundle: optional conda env via Miniforge (not Anaconda)
Decision: the bundle also carries Miniforge3 25.11.0-1 (Windows x64, checksum checked at build) and `1_install_conda.bat`: per-user install, conda env `BumpemHome` created offline with Python 3.12 (fallback: clone base), packages from the same wheels. The launchers use `venv\` if present, else that env. 25.11.0-1 is the last Miniforge whose base is Python 3.12; the wheels are cp312.
Reason: the user wants the same conda env as on the Mac. Miniforge uses conda-forge only; Anaconda's default channel needs a paid licence for organisations over 200 people.
Alternatives: Anaconda/Miniconda (licence); a newer Miniforge (Python 3.13+: wheels for that version needed); only venv (kept as option a).

## D30 — 2026-11-02 — Bundle conda option: Miniconda (Anaconda) instead of Miniforge (replaces D29's installer)
Decision: `1_install_conda.bat` installs Miniconda3-py312_26.9.4-0 (Windows x64, checksum from repo.anaconda.com checked at build). Before installing, the script shows Anaconda's Terms of Service link and the user must answer Y; only then it installs silently and sets `CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes` for that run. Env creation as in D29.
Reason: the user wants Anaconda's conda; IBMS is its own organisation with 6 employees (user, 2026-11-02), under Anaconda's 200-employee free limit. The user accepts the terms, not the script.
Alternatives: keep Miniforge (no terms, same conda); full Anaconda installer (~1 GB, not needed).

## D31 — 2026-11-02 — Vicon: force plates only, no marker data (for now)
Decision: the host reads only the GRAIL belts' force plates from Vicon DataStream over Ethernet (`EnableDeviceData`; no marker or segment data). `scripts/vicon_probe.py` and the planned `bumpem/vicon.py` enable device data only. Marker streaming (D7's recovery input) is deferred until the recovery algorithm is integrated.
Reason: the user needs only the force data for now (2026-11-02); it is what the previous student used (manual §6.2: LAN cable to the Nexus PC, DataStream SDK, vertical GRF; `legacy/MATLAB_script.m:39,75-82`). Less data per frame, and markers need not be labelled live in Nexus.
Alternatives: stream markers too (D7, needed later for recovery); read the plates from D-Flow instead of Vicon (no SDK or interface known).

## D32 — 2026-11-02 — Vicon force plates in the server: live plot, recording while armed
Decision: the server reads the force plates itself (`bumpem/vicon.py`: `ViconReader` over DataStream, `SimReader` for `sim`), connected at startup with `bumpem serve --vicon HOST:PORT` or from the UI (`POST /vicon/connect`). Each frame's mean Fz per plate goes on the WebSocket stream (`vicon`, thinned like telemetry); every subsample is written to `vicon_<stamp>.csv` **while the board is armed** (any state but DISARMED / ESTOP), started and stopped by the server from the board's telemetry, no button. Each row carries the latest board time (`board_ms`) to line up with `force_*.csv`. Files never overwrite each other (`_2` suffix within one second).
Reason: user (2026-11-02): live ground-force graph under the rope-force graph; record Vicon from Arm until stopped. Recording in the server (not the browser) keeps the full 1000 Hz rate and works with the tab closed.
Alternatives: a Record button for Vicon (forgettable at the start of a trial); recording in the browser (thinned, lost on reload); Vicon in a separate process (second clock, harder to align).

## D33 — 2026-11-02 — One Record for board + Vicon; settings in every recording (replaces D32's automatic recording)
Decision: Vicon is no longer recorded automatically while armed. `POST /log/start` records the board (force + events) and, when Vicon is connected (or connects during the recording), `vicon_<same stem>.csv`; `POST /log/stop` ends all. `GET /log` adds `vicon_file`, `vicon_rows`; `/log/file?kind=vicon`; `GET /vicon/file` removed. The events file starts with a `PARAMS` row (all board parameters as JSON). Release / STOP do not stop a recording.
Reason: user (2026-11-02): one Record button next to Arm, enabled once armed, Stop rec ends it. Same stem = files of one trial belong together. The settings row makes every recording analysable on its own (gains, baseline, gains/offsets per sensor), needed for the force-accuracy issues reported the same day.
Alternatives: keep automatic Vicon recording beside the button (two rules for one trial); stop at Release (loses the release in the data).

## D34 — 2026-11-02 — Closed loop with kff 2 (feedforward ≈ 1 N per N), not 7.5
Decision: run perturbations with `kff` = 2 (set in the UI's Board settings, saved to `settings.json`); gains `kp`/`kd` unchanged for now. Firmware default stays 7.5 (v0 value, no re-flash). Further accuracy by raising `kp_pulse` stepwise (Stanford procedure, `knowledge/controller.md` §5), only on the bench, with recordings.
Reason: with the ESCON scaling confirmed on A and B (0–10 V = 0–30 A → 9.9 A at the DAC's 3.3 V, `knowledge/control.md`) and the motor's 0.231 Nm/A, the feedforward alone pulls **≈ 0.5 · kff × target** (`docs/tests/open-loop-test-module-C.md`): 7.5 → 3.75×, 2 → 1×. The feedback is weak in comparison (kp 0.24 = 0.08 A real ≈ 1 N per N of error). With a tense rope that cannot move (opposite rope tight), nothing absorbs the excess: steady force ≈ (3.75·F + 0.96·F)/1.96 ≈ 2.4 × F, so a 20 N pull reads ~40–48 N; with a moving rope, friction and the derivative term hide part of it. Same at Arm: baseline 4 N → ≈ 9 N. Matches the user's report (2026-11-02) and the 4 N hold of 2026-10-27 (A 3.1, B 4.7, C 3.3, D 5.6 N). Lowering kff lowers the current: the safe direction. Open loop with kff 2 was measured ≈ 1:1 before friction (C: 22 N → 15–16 N).
Alternatives: correct the scaling in firmware terms (`i_full` 9.9, `kt` 0.231, `kff` 1: same feedforward, but kp/kd then act 3× stronger: retune first); integral term (firmware change, later if a steady error remains); per-tower kff (if D still reads high: check D's ESCON scaling, upload only).

## D35 — 2026-11-02 — Updates without reinstalling: update package + update.bat
Decision: `scripts/build_bundle.sh --update` builds `../bumpemInstallation/BumpemUpdate_<date_time>/` + `.zip` (both repos at HEAD, wheels, launchers, guide, `VERSION.txt`; no installers, no settings). On the lab PC the user unzips it and runs its `update.bat`: finds the installation (`%USERPROFILE%\BumpemLab`, then `C:\Users\operator\BumpemLab` = the Vicon PC, else asks), refuses while port 8000 is in use, shows installed vs new `VERSION.txt`, asks Y/N, moves the old `BumpemServer`/`BumpemUI` to `backup\<date_time>\`, copies the new code, puts back `settings.json`, `force_logger_cal.json`, `Logs\` (moved), copies launchers and wheels, `pip install` from the wheels (only changes), import check. A failed copy restores the old folders. Full bundles also carry `VERSION.txt` and `update.bat`.
Reason: user (2026-11-02): updating should not mean reinstalling; the lab PC's own settings (e.g. kff 2, D34) and recordings must survive. Running from the new folder means the script never overwrites itself while cmd reads it.
Alternatives: reinstall each time (loses settings unless copied by hand; the Mac's settings.json in the full bundle overwrote the lab's); git on the lab PC (offline, no git installed); an update.bat living in the install folder that pulls a zip (it would replace itself while running).

## D36 — 2026-11-02 — Vicon SDK shipped as a wheel in the bundle (no SDK installer on the lab PCs)
Decision: `scripts/vicon_wheel.sh <SDK Win64 zip>` takes `Win64/Python/vicon_dssdk` out of Vicon's DataStream SDK 1.13.0 `.msi` (msiextract, nothing run), removes `install_requires=['enum34']` and builds `vendor/vicon_dssdk-1.13.0-py3-none-any.whl` (not in git). `build_bundle.sh` copies it into `wheels\`; `1_install.bat`, `1_install_conda.bat` and `update.bat` install it with `--no-deps` and check `from vicon_dssdk import ViconDataStream` (a failed load only warns). `install_vicon_python.bat` stays as fallback (now `--no-deps`, accepts the Python folder or the package folder).
Reason: the lab PCs have no Python/.NET SDK client (only D-Flow's `ViconDataStreamSDK_CPP.dll`); the SDK installer may need the administrator; Vicon's licence for the Python package is MIT (redistribution allowed, licence in the wheel). `_CoreClient3.pyd` links `python3.dll` (stable ABI): works with Python 3.12. enum34 is a Python 2 backport that shadows the standard `enum` on Python 3. Needs the Visual C++ 2015+ runtime (`MSVCP140.dll`), which Nexus/D-Flow PCs normally have.
Alternatives: run the SDK installer on the lab PC (admin, ESET); the student's route (.NET DLL from MATLAB: not on the lab PCs); `pyvicon-datastream` (source only, needs a compiler, Windows untested, no force plates documented).
SDK facts checked in its ViconDataStream.py: `GetFrame()` returns False on NoFrame (raises on other errors) → reader/probe fixed; force plate device outputs are plate-local, Z up, forces on the plate (standing reads negative Fz).

## D37 — 2026-11-02 — Force plates through Vicon's force-plate API, wait for device data
Decision: `ViconReader` reads `GetForcePlates()` IDs and `GetGlobalForceVector(id)` (Fz = 3rd component, every subsample), like `legacy/MATLAB_script.m:75-82`, instead of device outputs; after `EnableDeviceData` it keeps fetching frames (up to the 5 s timeout) until plates appear. Names: Nexus force-plate device names when they match the IDs one to one, else `Plate <id>`.
Reason: `vicon_check` on the D-Flow PC (2026-11-02): SDK 1.13 connects to Nexus 2.8.1 at 192.168.1.60:801 (100 Hz), but the device list was empty on the first frame (data arrive a few frames after enabling). Global axes = the lab axes our angles use; same numbers as the student's script.
Alternatives: device outputs (plate-local axes, names of outputs vary per plate type).

## D38 — 2026-11-02 — Vicon SDK in its own process
Decision: `ViconReader` starts a separate Python process (`multiprocessing`, spawn) that holds the SDK connection (`_SdkSession`) and sends `("ready", plates, rate)` / `("frame", n, subs)` / `("end", text)` over a pipe; a thread in the server receives them. Closing sends "stop", then joins / terminates. The reader's process exits with the server (daemon).
Reason: user (2026-11-02): with Vicon and the board connected, board commands time out. Vicon's `_CoreClient3.pyd` never releases Python's GIL (no `PyEval_SaveThread` import): its `GetFrame` waits for the next frame holding it, so the server's serial reader and request threads stall. Measured on the Mac with a fake SDK that waits 10 ms per frame holding the GIL (`tests/fake_vicon_sdk.py`, host "gil"): longest pause seen by a 1 ms-sleep thread 14–15 ms with the SDK in-process, 1.5–1.8 ms with it in its own process (≈ without Vicon).
Alternatives: ClientPull with short calls (still holds the GIL per call, can drop frames); a separate Vicon program writing to a file/socket (another window to start).

## D39 — 2026-11-02 — Display telemetry: median of the samples between messages; recordings stay raw
Decision: the WebSocket thins telemetry to `telemetry_hz` by sending, per channel, the median of the board samples since the previous message (`_MedianThin`) instead of dropping samples. The UI asks for 20 Hz → median of 5 samples (50 ms at 100 Hz). Recordings are unchanged: every sample, raw. The firmware's `filter_hz` stays 0.
Reason: user (2026-11-02): rope force signal very noisy with spikes. The noise is in the raw single ADC read per 10 ms loop; dropping samples for display kept spikes at full height. A median removes single-sample spikes without touching control or data. `filter_hz` also filters the controller's input (adds lag to perturbations): bench decision with recordings, not a display fix.
Alternatives: firmware oversampling (several ADC reads per loop, median/mean: cleaner for control too; needs PROTOCOL.md, re-flash); `filter_hz` > 0; smoothing only in the browser (would work on already-dropped samples).

## D40 — 2026-11-02 — Plate force shown and recorded as ground reaction force (positive up)
Decision: `_SdkSession` negates the Z of `GetGlobalForceVector`, so the stream (`vicon.fz`), the plot and `vicon_*.csv` (`Fz_<plate>`) carry the vertical ground reaction force, positive up. The simulator already did. `vicon_check` / `vicon_probe` still print Vicon's raw numbers (diagnostics).
Reason: user (2026-11-02): treadmill forces appear negative. Vicon gives the force on the plate (down); gait analysis and the 250 N step threshold of the legacy script use the upward reaction.
Alternatives: flip only in the plot (CSV would disagree with the screen).
## D41 — 2026-11-03 — Saved settings re-sent when the board restarts; clients warn on a mismatch
Decision: the server watches the board's uptime (`t_ms` in telemetry); a jump back by more than 1 s while connected = board restart. It then re-sends channels (`--modules`), its `wd_ms` and the saved settings (as at connect; waits for DISARMED if needed), and sends the stream event `RESTART` with how it went (also written to a running recording's events file). The UI shows a warning line under the header whenever the board's parameters differ from the saved file, or when no file is saved (BumpemUI U10).
Reason: the perturbation test of 2026-11-03 (`tests/force_20261103_112027.csv`) ran on firmware defaults (kff 7.5, baseline 5 N; kff back-calculated from the DAC) instead of kff 2 (D34): pulls 1.7–1.9 × the target, opposite rope up to 58 N. Settings were written only at Connect; a Teensy reset that keeps the USB link went unnoticed before (2026-10-27). Nothing on the page showed which values the board ran.
Alternatives: block Arm on a mismatch (also blocks deliberate unsaved tuning); store parameters in the Teensy's EEPROM (firmware change, re-flash; still no visible check).

## D42 — 2026-11-03 — Sensor gains from hung weights: calibrate page → CSV → apply_calibration.bat
Decision: BumpemUI `calibrate.html` (U11) records, per sensor, a tara and several known weights as 2 s means of the **raw** reading (telemetry with the board's gain/offset taken out, so its current settings don't matter) and downloads `calibration_<stamp>.csv` (`time,sensor,kind,mass_kg,expected_n,raw_mean_n,raw_sd_n,samples,clipped_pct,tare_n,net_n,board_gain,board_offset,f_full,g,fw,port`, g = 9.81). `scripts/apply_calibration.py` (`apply_calibration.bat`, double-click on the lab PC, newest CSV in BumpemLab or Downloads) fits gain = slope of expected force over raw (with intercept when ≥ 2 weights; else through the tara), writes `gain_X` into settings.json (backup `.bak`), scales an existing `offset_X` by new/old gain, refuses gains outside the firmware's 0.5–3, and writes a report. No API change (page uses `/params`, the stream at full rate, connect, estop).
Reason: user (2026-11-03): pull strength depends on accurate sensors; B's 200 kg cell (1.0 mV/V) vs 100 kg (1.6 mV/V) suggests gain ≈ 3.2, not the 2.12 in use. Offsets are re-zeroed in the lab (Zero sensors) since they depend on the rope setup; the slope does not. Fit with intercept: the 0 N floor of the ADC biases a tara at rest (seen on B and C, 2026-11-03), not the slope.
Alternatives: server endpoint that writes the CSV (API change, no gain); fit in the page and PATCH gains directly (no record, lab PC not where the weights are hung).
Open: if B needs > 3, the firmware range (PROTOCOL.md first, re-flash) or the IAA100 trim must change.

## D43 — 2026-11-03 — Calibration fit through the tara; full-scale points left out (amends D42)
Decision: gain = least-squares slope through the tara (Σ E·net / Σ net², net = raw − tara) instead of a free fit with intercept; points with raw ≥ 99.5 % of `f_full` are left out (script) / refused (page).
Reason: first calibration (2026-11-03, `~/Downloads/calibration_20261103_1413.csv`, 12/16/32 kg): with only 12 and 16 kg below full scale, the free fit gave D an intercept of −5.5 N and A a slope of 0.97 against point ratios 1.005–1.023. Every 32 kg point on A, C, D read exactly 200.00 N, sd 0 = ADC full scale (`f_full` 200 at gain 1): a 100 kg cell reads at most ~20 kg. The tara's 0 N clipping (B 20 %, C 35 % of samples) biases it by tenths of a N: negligible against 57–165 N.
Alternatives: keep the free fit and ask for widely spread weights (the lab's set is 12/16/32 kg).
