# To do

Ordered by **danger** first, then by **what it blocks**. Work top to bottom; items in the same step can run in parallel.
Tick items off and tell Claude what you found so `STATUS.md` stays current. Last reordered 2026-09-30, updated 2026-10-01.

**Danger:** 🔴 high = injury or burnt hardware if skipped/done wrong · 🟠 medium = damaged electronics or misleading test · 🟢 low.
**Blocks:** the steps that cannot start until this one is done.

Teensy port on the Mac: `/dev/cu.usbmodem169222501` (written `PORT` below). Every new Terminal: `conda activate BumpemHome`.
Current state (2026-10-01): module C's 48 V chain wired and checked; **module C's driver healthy** (Hall wiring fixed, Diagnostics passed, LED green = ready); e-stop not wired; 24 V supply not yet inspected; Teensy not yet connected to module C.

---

## ▶ Tomorrow morning (2026-10-02): preliminary open-loop test, module C
Procedure: `docs/tests/open-loop-test-module-C.md` (no amplifier; PD gains 0, kff 2, baseline 2 N, fmax 30 N, only C).
- [x] Wiring done (2026-10-02, recabled to ESCON-side colours, `docs/diagrams/cabling-4-modules.png`)
- [x] Settings checked with `bumpem get` (via `scripts/open_loop_test.sh`)
- [x] Module C: **motor pulled correctly** (2026-10-02); only C active, as intended
- [x] Details: tug grew with 5 → 10 → 20 N; release back to normal (2026-10-02)
- [x] Module A first test (2026-10-02): **pull far too strong** → cause: A's J3 **green and grey swapped**
- [x] A's J3 recabled: 1 yellow, 2 pink, 3 grey, 4 green, 5 blue (2026-10-02)
- [ ] A's 48 V on (Teensy disarmed) → LED green blinking → ESCON Studio **Diagnostics on A: Hall test must pass** (rope slack)
- [x] `scripts/open_loop_test.sh A` **passed** (2026-10-02)
- [x] Both together: `scripts/open_loop_test.sh AC` **passed** (2026-10-02)
- [ ] Repeat C's pulses through `bumpem serve --board PORT` → http://127.0.0.1:8000/docs

## Start today, in parallel (lead time, no risk)
- [x] Multimeter (2026-09-30)
- [ ] Order a **Hirose DF11-12DS** housing + **DF11 crimp terminals** for the 48 V supply's CN501 (or plan to solder). Needed by 3
- [ ] Ask your **supervisor**: has this setup had an electrical safety inspection (DGUV Vorschrift 3), and who fixes mains cables if one is damaged?

## 1. 🔴 Mains side: inspect, don't rewire · blocks everything powered
No technician available: do **no work on 230 V yourself**. The mains cables appear to be still attached (48 V supply photo). Checklist: `docs/power-estop-checklist.md`.
- [x] 24 V supplies: **4 × RS-15-24, one per amplifier** (2026-10-01). Still to confirm: one RSP-2000-48 per module
- [ ] Photo of module C's **IAA100 amplifier terminal labels** → Claude confirms where RS-15-24 +V / −V go (don't touch its DIP switches / zero / span screws)
- [x] RSP-2000-48: L, N, −V, +V connected; **2 wires on ⏚** = mains earth + safety earth to shunt pin 3, as in Stanford guide p. 16 (2026-09-30)
- [x] RSP-2000-48: clear terminal cover on · strain relief OK · plug and insulation intact (2026-09-30)
- [x] RSP-2000-48 output wires connected → shunt **pin 5 (−V), pin 4 (+V), pin 3 (⏚)** (2026-09-30)
- [x] `docs/tests/power-checks-module-C.md` T0–T7 **all passed** (2026-09-30). First power-on: ESCON **red LED blinking** (error, power stage off). Count the blinks → meaning in `escon/README.md`; read the error text in ESCON Studio (step 5)
- [ ] RS-15-24 (24 V), **unplugged**: intact plug · L / N / ⏚ tight, **earth connected** · cover · strain relief · insulation
- [x] RS-15-24 outputs were fully detached. Thesis §2.7: 24 V powers **only the IAA100** → not the Hall cause. Later: RS-15-24 +V / −V → IAA100 Vin / GND (step 4)
- [ ] Anything fails or a cable is missing → stop; get it fixed via the university (facilities / electrical workshop / supervisor)
- [ ] First test: module C's RSP-2000 + the RS-15-24 into a wall socket or **one 16 A switched power strip** (no daisy-chained strips). The strip switch = **48 V mains switch**, reachable from the operator position
- [ ] Later, all modules: each RSP-2000 on its own socket/circuit

## 2. 🔴 Shunt regulator setting · blocks 3
- [x] T6 passed: threshold > 48 V (2026-09-30). Still note the exact setting: photo of the **actual DIP switch block** on its internal board (the label only shows examples). Switch n = 2^(n−1); Vth = 75 V − sum; must be clearly > 48 V. Stanford: **55 V = switches 3 and 5 ON** (label: Vth = 75 V − binary × 1 V). Tell Claude before changing anything

## 3. 🔴 E-stop · blocks every step with 48 V on (5, 8)
Details: `knowledge/wiring.md` → Power supplies and e-stop.
- [x] Pins found (2026-09-30): RSP-2000 **CN501 pin 7** (Remote ON-OFF) + **pin 11** (+5V-AUX); short = 48 V **off**
- [x] E-stop contact block is **NO** (T5 passed, 2026-09-30)
- [ ] Wire it → CN501 pin 7 + pin 11, either way round. One NO contact per 48 V supply
- [ ] Ask the technician whether a **fail-safe** version is possible (in this design a cut wire means the button does nothing)
- [ ] **Test:** 48 V on, press → 48 V off (ESCON LED off); release → back on. **Repeat before every session**

## 4. 🟠 Low-voltage power wiring, module C (all unplugged) · blocks 5, 6
- [x] RSP-2000 **−V** → shunt **pin 5**, **+V** → **pin 4**, **⏚** → **pin 3** (T3, 2026-09-30)
- [x] Shunt **pins 6 / 7** → ESCON **J1 + / −** (T3.5–3.6, 2026-09-30)
- [ ] Confirm this supply feeds module C: follow the thick cable from the shunt regulator's pins 4/5
- [ ] RS-15-24 **+V / −V** → IAA100 **Vin / GND**
- [x] 48 V output: no short (T2, 2026-09-30)
- [ ] 24 V output: no short (+V ↔ −V), after the RS-15-24 is inspected

## 5. 🟠 Motor drivers (ESCON Studio) · blocks the real baseline in 8
Steps: `knowledge/wiring.md` → Power order; details and history: `escon/README.md`. ⚠️ Diagnostics and auto-tuning turn the motor: rope slack, nobody near, hand on the strip switch.
- [x] Module C: Hall error fixed (blue = Hall GND moved J2 pin 4 → J3 pin 5); Diagnostics all passed; LED green blinking (2026-10-01)
- [x] Module A config uploaded → `escon/moduleA_left_2026-10-01.edc`: Stanford base + auto-tuned, intact; confirms 10 V = 30 A (2026-10-01)
- [x] All motors are **maxon EC 90 flat 500267** (2026-10-01) → one base config fits all
- [x] Decision (2026-10-01): **preliminary tests use module C's current driver config as is** (Diagnostics passed). Config upload / auto-tuning moved to "Before final testing"
- [ ] Every other module: motor connector colours (blue on motor pin 6?) → same fix; Diagnostics; upload config as `escon/module<X>_<side>_<date>.edc`
- [ ] Always: USB in before 48 V on; 48 V off before USB out

## 6. 🟠 Protect the Teensy · blocks 7
- [ ] Remove the 4 **loopback wires** (DAC VA–VD → pins 14–17). Pin 16 takes module C's force wire
- [ ] Confirm "right-side motor" = the **subject's right** (walking direction) → module C. If it's your right facing the subject, it is **A**: tell Claude (wrong pins otherwise)
- [ ] **Amplifier range** (needs multimeter + 24 V): blue force wire **not** in the Teensy, pull the rope hard → Futek output **≤ 3.3 V**. Higher: stop, tell Claude
- [ ] Futek terminal of the yellow ground wire is labelled **GND**

## 7. 🟠 Wire module C to the breadboard (all power off) · blocks 8
- [ ] Label jumper ends: black = EN, red = SP+, orange = SP−, blue = F, purple = GND. Tape the spares (yellow, white)
- [ ] Teensy **G** → breadboard **− rail**; **purple** and **orange** into the rail
- [ ] **black** → pin **29**'s row (left edge, a/b) · **red** (female) → DAC **VC** · **blue** → pin **16**'s row (right edge, h/i/j)
- [ ] Multimeter beep test of each jumper to its pin; 3V ↔ GND must not beep
- [ ] Photo into `docs/hardware-photos/`

## 8. 🔴 First motor test, module C
Rope tied to a fixed anchor · no person · treadmill off · everyone clear · **hand on the e-stop**.
Power order: Teensy USB → **24 V** → check force → **48 V** → arm. Down: release → 48 V off → 24 V off.
- [ ] Claude: CSV logging for `--watch` (to compare with `knowledge/results.md`)
- [ ] `bumpem info --port PORT` → `proto=1`
- [ ] E-stop tested today
- [ ] Disarmed, only C: `bumpem set ch_A 0 --port PORT`, `bumpem set ch_B 0 --port PORT`
- [ ] If step 5 not done: `bumpem set baseline_n 1 --port PORT`
- [ ] **24 V only:** `bumpem monitor --port PORT`, pull the rope → C's force rises, A and B don't (Ctrl+C)
- [ ] **48 V on:** `bumpem arm --port PORT --watch 5` → rope tightens gently
- [ ] `bumpem pulse C=10 --port PORT --watch 2`, then `C=20`, `C=50`; note target vs measured peak
- [ ] End: `bumpem release --port PORT` (or `estop`), then 48 V off, 24 V off
- [ ] **Stop at once** (e-stop) if the rope pulls hard at arm or the force keeps rising
- [ ] Tell Claude the results

## Before final testing (not needed for preliminary tests)
- [ ] Module C config upload → `escon/moduleC_right_<date>.edc` → Claude compares with module A / Stanford. If gains equal the Stanford file (integral time 20000 µs) → load module A's file, then auto-tune C
- [ ] Every module: same base config + auto-tuning per driver (manual §4.3.1); upload each result into `escon/module<X>_<side>_<date>.edc`
- [ ] Screenshot the ESCON **firmware version** of each driver (look only, no update)
- [ ] Correct firmware `i_full` (9.9, setpoint 10 V = 30 A) and `kt` (0.231 Nm/A) (`knowledge/control.md`, `STATUS.md`)

## 9. Afterwards / scheduled (not blocking the test)
- [ ] 🟢 Call with the previous student, **week of 2026-10-05**: read `QUESTIONS.md`, bring the "Files to ask for" list
- [ ] 🟠 Modules **A** and **B**: trace cables like C, then steps 2–5 for each
- [ ] 🟢 Carrier board (`hardware/carrier/README.md`): check terminal orientation in KiCad's 3D viewer and a 1:1 print, then order (makerspace can help) and solder. Move the modules over one at a time, re-run `scripts/open_loop_test.sh` for each
- [x] 🟢 `git init` both folders + first commit (2026-10-02)
- [x] 🟢 Claude: `bumpem serve`, the server API: built + tested on the simulator (2026-10-02)

## Done
- [x] Mac: conda env `BumpemHome` (Python 3.12), `pip install -e ".[dev]" platformio`, pytest 24 passed (2026-09-30)
