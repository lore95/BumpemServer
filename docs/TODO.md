# To do

Ordered by **danger** first, then by **what it blocks**. Work top to bottom; items in the same step can run in parallel.
Tick items off and tell Claude what you found so `STATUS.md` stays current. Rewritten 2026-10-02 (evening), updated 2026-10-05.

**Danger:** 🔴 high = injury or burnt hardware if skipped/done wrong · 🟠 medium = damaged electronics or misleading test · 🟢 low.
**Blocks:** the steps that cannot start until this one is done.

Teensy port on the Mac: `/dev/cu.usbmodem169222501` (written `PORT` below). Every new Terminal: `conda activate BumpemHome`.
**State (2026-10-02):** modules **A (left), C (right), D (back)** mounted and pulled correctly in the open-loop test (no force sensing); B (front) not installed.
Server 0.2.0: board API + perturbation by angle (`bumpem perturb`), simulator-tested only. E-stop **not wired**: the 48 V strip switch is the only stop. Carrier board designed, not ordered.

---

## ▶ Next session
- [ ] 🟢 Fix `scripts/open_loop_test.sh`: keep `AC`, usage text = real modes, `ACD` power-on prompt must name all three supplies (A, C, **D**), "with AC both at once" text. Then commit (`scripts: ...`)
- [ ] 🟠 Try `bumpem perturb` on the hardware, open-loop settings of the script, rope to fixed anchors, nobody attached:
  `bumpem set ch_D 1` (the firmware boots with D off) → `arm` → `perturb 180 10`, `perturb 135 10`, `perturb -90 10`, `perturb 90 10` (`--dur 400 --phase2 50 --watch 2`). Expect D / A+D (7.07 N each) / C / A
- [ ] 🟢 Same through the server: `bumpem serve --board PORT` → http://127.0.0.1:8000/docs → `POST /perturbation`
- [ ] 🟢 `git push` in BumpemServer (9 commits ahead of GitHub); delete the empty clone `IBMS_Offenburg/BumpemServerGit`

## 1. 🔴 Safety · blocks long sessions and anything with a person attached
- [ ] **Multimeter**: borrow one (lab / makerspace) or buy one. Needed for the e-stop test, the 24 V checks and the amplifier range check
Details: `knowledge/wiring.md` → Power supplies and e-stop; `docs/power-estop-checklist.md`.
- [ ] Order a **Hirose DF11-12DS** housing + **DF11 crimp terminals** for each RSP-2000's CN501 (or plan to solder)
- [ ] **Wire the e-stop**: CN501 pin 7 + pin 11, one NO contact per 48 V supply (A, C, D)
- [ ] Ask the technician whether a **fail-safe** e-stop is possible (in this design a cut wire means the button does nothing)
- [ ] **Test:** 48 V on, press → every ESCON LED off; release → back on. **Repeat before every session**
- [ ] Ask your **supervisor**: electrical safety inspection (DGUV Vorschrift 3)? Who fixes mains cables?
- [ ] Mains, look only: confirm **one RSP-2000-48 per module**; each on its own socket/circuit; RS-15-24 (24 V) units: plug, L / N / ⏚ tight, earth, cover, strain relief. Anything wrong → stop, university fixes it
- [ ] Shunt regulator: photo of the DIP switch block (threshold must stay clearly > 48 V; Stanford 55 V). Tell Claude before changing anything

## 2. 🟠 Force sensing → closed loop · blocks real force control, logging, trials with people
Power order: Teensy USB → **24 V** → check force → **48 V** → arm. Down: release → 48 V off → 24 V off.
- [x] RS-15-24 **+V → IAA100 pin 1 (+Vin), −V → pin 2 (GND)** on A, C, D (2026-10-05), supply unplugged while wiring (`knowledge/wiring.md`). Check first: the existing brown wire is on pin 5 and the ground on pin 4; if not, photo to Claude. Don't touch DIP switches / zero / span. 24 V output: no short before connecting
- [ ] **C rests at ~73 N** (`scripts/force_check.py`, 2026-10-05; A 4.6 N, D 1.3 N): swap C/D brown wires (does it follow?), then jumper C's IAA100 pin 4 → − rail (ground?). Don't pull C hard meanwhile (3.3 V reached at ~127 N real force)
- [ ] **Amplifier range** per module (needs the multimeter): brown wire out of the Teensy, pull hard → output **≤ 3.3 V** (`knowledge/calibration.md`: 0–3.3 V = 0–200 N). Hand pulls so far stayed ≤ ~2.4 V at the Teensy, but above 3.3 V the Teensy can't tell (reads 200 N) and can be damaged
- [x] Short wires removed, brown force wires in T14 (A), T16 (C), T17 (D) (2026-10-05)
- [x] Hand-pull check `scripts/force_check.py` (2026-10-05): left → A, right → C, back → D, each moves only its own sensor. Zeros: A 4.6 N, C **73 N** (item above), D 1.3 N
- [ ] Claude: CSV logging for `--watch` / server (to compare with `knowledge/results.md`)
- [ ] **Closed-loop test**, one module at a time (C first): default gains (`kp`, `kd`, `kff` back to boot values: unplug/replug USB), `arm`, `pulse C=10`, `20`, `50`; note target vs measured peak and rise time → Claude compares with `knowledge/results.md`

## 3. 🟠 Motor drivers (ESCON Studio)
⚠️ Diagnostics and auto-tuning turn the motor: rope slack, nobody near, hand on the strip switch.
- [ ] Module A: Diagnostics (Hall test must pass) after its J3 recabling
- [ ] Module D: Diagnostics; upload its config as `escon/moduleD_back_<date>.edc`
- [ ] Always: USB in before 48 V on; 48 V off before USB out

## 4. 🟢 Software (Claude builds, you test)
API order: `docs/API.md`, `planned` sections. Each step: API.md first, simulator tests, then hardware.
- [ ] Step 2: **PTO**: perturb a set time after a foot strike (ms or % of stance), from gait events (simulated / replayed recorded trial until Vicon is connected)
- [ ] Step 3: **trials**: blocks, shuffle, 50–75 steps between perturbations, recovery stand-in (D8), baseline = first 3 s (D7), logs
- [ ] Step 4: **Vicon live** (force plates + markers) on the lab PC: needs the Vicon DataStream SDK there
- [ ] Validate `bumpem/gait.py` on a recorded MATLAB `Log_event_data_*.csv` (rule 5: before any live use). Need a recorded file from the lab
- [ ] Minimal web UI in `../BumpemUI`: connect, arm, perturb by angle, stop, live force plot. Give BumpemUI a GitHub remote
- [ ] Decide: firmware boots with `ch_D = 1` now that D works (firmware change → `PROTOCOL.md` first, re-flash)

## 5. 🟢 Hardware build
- [ ] 🟠 **Ropes** worn: measure rope diameter, drum diameter/width, eyebolt inner diameter; photo of worn spots and of the breakaway link → Claude proposes a low-stretch rope (Kevlar / Dyneema, ≥ ~2 kN, breakaway stays the weakest link). Lengths: Stanford guide p. 12 / 20 (drum rope = travel + 28 in, ≥ 3 wraps left at full travel)
- [ ] Carrier board (`hardware/carrier/README.md`): terminal orientation in KiCad's 3D viewer + 1:1 print check → order (makerspace can help) → solder → move modules over one at a time, re-run the open-loop test for each
- [ ] Module **B (front)**: is it planned? When mounted: trace cables, ESCON Diagnostics, open-loop test, `ch_B 1`

## Before final testing (not needed for preliminary tests)
- [ ] Module C config upload → `escon/moduleC_right_<date>.edc` → Claude compares with module A / Stanford. If gains equal the Stanford file (integral time 20000 µs) → load module A's file, then auto-tune C
- [ ] Every module: same base config + auto-tuning per driver (manual §4.3.1); upload each result into `escon/module<X>_<side>_<date>.edc`
- [ ] Screenshot the ESCON **firmware version** of each driver (look only, no update)
- [ ] Correct firmware `i_full` (9.9, setpoint 10 V = 30 A) and `kt` (0.231 Nm/A) (`knowledge/control.md`, `STATUS.md`)

## Scheduled
- [ ] 🟢 Call with the previous student, **week of 2026-10-05**: `QUESTIONS.md` (3.2 answered), bring the "Files to ask for" list (recorded MATLAB logs for step 4 above)

## Done
- [x] Mac: conda env `BumpemHome` (Python 3.12), `pip install -e ".[dev]" platformio`, pytest (2026-09-30)
- [x] 48 V chain of module C wired and checked: T0–T7 passed, shunt threshold > 48 V, e-stop pins found and contact type checked (2026-09-30)
- [x] Module C driver: supply and Hall wiring fixed, Diagnostics passed; module A config saved; all motors maxon 500267 (2026-10-01)
- [x] Teensy flashed with firmware v1, desk test passed, loopback wires removed (2026-09-29 / 10-02)
- [x] Breadboard recabled to ESCON-side colours (`docs/diagrams/cabling-4-modules.png`) (2026-10-02)
- [x] Open-loop tests passed: C, A (after fixing its swapped J3 Hall wires), A + C together, D (2026-10-02)
- [x] Server: board API, perturbation by angle, `bumpem perturb` (simulator) (2026-10-02)
- [x] Git: repo filtered, pushed to GitHub (`lore95/BumpemServer`) (2026-10-02)
- [x] Carrier board v1 designed: ERC / DRC / parity clean, spacing ≥ 0.74 mm (2026-10-02)
