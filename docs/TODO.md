# To do

Ordered by **date**, then by **danger**. Items on the same day can run in parallel.
Tick items off and tell Claude what you found so `STATUS.md` stays current. Rewritten 2026-10-07, updated 2026-10-12.

**Danger:** 🔴 high = injury or burnt hardware if skipped/done wrong · 🟠 medium = damaged electronics or misleading test · 🟢 low.
Teensy port: `/dev/cu.usbmodem169222501` (`PORT`), in the **good USB socket** (the other hub socket drops data). Every new Terminal: `conda activate BumpemHome`.

**State (2026-10-07):**
- **A (left), C (right), D (back):** test pulls work (`bumpem serve --testing`); A + D held at 2 N closed loop (kff 2, offsets zeroed). C's force reads ~73 N at rest (cut ground wire).
- **B (front, the former broken tower):** chopper OK (DIP set to 55 V), motor windings + Halls OK, new 48 V supply OK, breadboard wired (T28, VB, T15). **Its ESCON is faulty** (enable + USB dead) → replacement **ordered 2026-10-07**.
- E-stop **not wired**: the power strip switch is the only stop.
- Printed tower parts (`hardware/enclosures/`): being printed 2026-10-12. Carrier board: at the makerspace (Sebastian Stulz), expected **Fri 2026-10-16**. Replacement ESCON: not arrived yet (2026-10-12).

---

## Mon 2026-10-12 · today
- [ ] 🟢 Printed parts (ready in a few hours): test plate slides into the slot without play? M6 bolt long enough (≥ ~5 mm thread in the T-nut; probably **M6 × 16**)? Tell Claude → `KEY_CLEAR` / bolt length, regenerate if needed
- [ ] 🟢 Buy: M3 × 6 (RS-15 plates), M4 × 12 (RSP brackets), M6 × 16 button heads, slot-10 T-nuts; **ferrules 0.25–0.5 mm²** for the 5 signal wires per MSTB plug; pin terminals (blue, 1.5–2.5 mm²) for the chopper cables
- [ ] 🟢 Per tower, following `hardware/enclosures/out/fit_check.pdf`: IAA100 on its DIN rail mount, RS-15-24 on its plate, then remove the tape
- [ ] 🔴 RSP-2000 brackets: supply **unplugged**, two people, fans free, 10 mm gap. Mains side stays with the electrician
- [ ] 🔴 Front tower chopper → ESCON cable (14 AWG, too thick for the chopper's 1.5 mm² terminals): crimp pin terminals, 48 V off and chopper < 1 V first; check terminals 6/7 on the working towers
- [ ] 🔴 Order the e-stop parts (Hirose DF11-12DS + crimp terminals per 48 V supply)
- [ ] 🔴 Ask the electrician: cover for the RS-15-24's open 230 V terminals; earth wire supply ⏚ → chopper terminal 3 on the front tower
- [ ] 🟢 `git push`; motor test 3d on the front tower; label the old ESCON

## Fri 2026-10-16 · carrier board (makerspace is making it; expected Friday)
- [ ] 🟠 Solder sockets, MSTB headers, protection parts (`hardware/carrier/README.md`); **nothing plugged in yet**
- [ ] 🔴 Meter checks, board bare: **3.3 V ↔ GND no short**, 5 V not connected anywhere, each MSTB pin → its Teensy/DAC socket pin (enable 27/28/29/30, VA–VD, force 14–17), neighbouring pins **not** connected
- [ ] 🟠 Insert Teensy + DAC, USB only (no 24 V / 48 V): `bumpem monitor --port PORT` streams 100 lines/s; `bumpem info` answers
- [ ] 🟠 Move **one module at a time** to its MSTB plug (5 wires: yellow enable, blue SP+, green SP−, white GND, brown force; colours `knowledge/wiring.md`): cut each wire back to clean copper, crimp a **ferrule** (do not tin the tip: solder creeps under a screw and the contact loosens), screw into the plug. After each: testing page, Pull 10 N, 500 ms → only that rope moves
- [ ] 🔴 **C's cut white ground wire** is repaired in this step (cut behind the damage, new ferrule, into C's plug); C's rest reading must then drop from ~73 N to a few N

## After the carrier board · force sensing → closed loop
- [ ] 🟠 `scripts/force_check.py`: each module rests at a few N, a hand pull moves only its own reading
- [ ] 🟠 **Amplifier range** per module (meter): pull hard, IAA100 output **≤ 3.3 V** (`knowledge/calibration.md`: 0–3.3 V = 0–200 N)
- [ ] 🟠 Weight calibration 6 / 8 / 12 kg per module (incl. the 200 kg cell on the 4th amplifier)
- [ ] 🟠 Closed-loop test one module at a time: production page, Arm at 2–5 N, perturbation 10 N → 20 N; note target vs measured → Claude compares with `knowledge/results.md`
- [ ] 🟢 Decide `i_full` 9.9 / `kt` (`knowledge/control.md`) after reading C's and D's ESCON configs
- [ ] 🟢 Claude: CSV logging for the server (compare with `knowledge/results.md`); server applies saved settings (kff, offsets, baseline) at connect

## Front tower (B)
- [x] Replacement **ESCON 70/10** (maxon 422969) ordered (2026-10-07); not arrived by 2026-10-12
- [ ] 🟢 Label the old one "faulty: USB + enable"; repair quote from maxon only as a spare (no rush)
- [ ] 🟢 Motor test 3d (red wire ↔ motor body: OL), optional 3e–3h (`docs/tests/broken-tower-diagnosis.md`)
- [ ] 🟠 New ESCON: mount, wire as before, load module A's `.edc` in ESCON Studio, save as `escon/moduleB_front_<date>.edc`; enable unplugged → LED slow green; then test pull B 5 N → 10 N
- [ ] 🟢 Start the server with `--modules ABCD` from then on

## 🔴 Safety · before long sessions or anyone attached
- [ ] Order **Hirose DF11-12DS** housing + DF11 crimp terminals per RSP-2000 (CN501), or plan to solder
- [ ] **Wire the e-stop**: CN501 pin 7 + pin 11, one NO contact per 48 V supply (A, B, C, D) (`knowledge/wiring.md` → e-stop)
- [ ] Ask the technician about a **fail-safe** e-stop (here a cut wire means the button does nothing)
- [ ] **Test** before every session: 48 V on, press → every ESCON LED off; release → back on
- [ ] Supervisor: electrical safety inspection (DGUV V3)? One power strip per tower, each on its own wall socket (no strips plugged into strips; RSP-2000 inrush 50 A)
- [ ] 🟠 **Ropes** worn: measure rope / drum / eyebolt, photos → Claude proposes a low-stretch rope with the breakaway as weakest link

## Software (Claude builds, you test)
- [ ] Step 2 **PTO**: perturb a set time after a foot strike (gait events, simulated / replayed until Vicon)
- [ ] Step 3 **trials**: blocks, shuffle, 50–75 steps between perturbations, baseline first 3 s, logs
- [ ] Step 4 **Vicon live** on the lab PC (DataStream SDK)
- [ ] Validate `bumpem/gait.py` on a recorded MATLAB `Log_event_data_*.csv` (needs a file from the lab)
- [ ] 🟢 Fix `scripts/open_loop_test.sh` (your uncommitted edit: `AC` mode, usage text, ACD prompt), then commit
- [ ] 🟢 `git push` BumpemServer (many commits since 10-02); give BumpemUI a GitHub remote
- [ ] Decide: firmware boots with `ch_D = 1` (firmware change → `PROTOCOL.md` first, re-flash)

## Before final testing
- [ ] ESCON configs of C and D → `escon/`; Claude compares with A / Stanford; same base config + auto-tuning per driver
- [ ] Screenshot each ESCON's firmware version (look only)

## Scheduled
- [ ] 🟢 Call with the previous student: `QUESTIONS.md`, ask for recorded MATLAB logs

## Done (since 2026-10-05)
- [x] Makerspace meeting with Sebastian Stulz; carrier board in production (2026-10-08)
- [x] "No reply" timeouts: bad USB socket/cable, not software (2026-10-06)
- [x] D pulled too hard: green SP− on the 3.3 V rail, fixed; A no-pull: loose pin (2026-10-06)
- [x] Test pulls A, C, D; closed-loop arm A + D at 2 N (2026-10-06)
- [x] Broken tower diagnosed: old 48 V supply faulty; chopper OK at 24 V and 48 V after DIP 75 V → 55 V; ESCON power stage OK; motor windings OK (2026-10-06/07)
- [x] Front tower ESCON found faulty (enable + USB dead, A's ESCON works on the same PC) (2026-10-07)
- [x] Server: `board_lost` 503 when the USB link is gone (2026-10-07)
- [x] Tower profile identified: 90×90 light B-type, slot 10; bolts M6 ISO 7380 (2026-10-07)
- [x] Printed parts designed from datasheets + fit-check print and PDF (2026-10-07)
- [x] Multimeter available
- [x] Earlier: conda env, firmware v1 flashed, breadboard recabled, open-loop tests A/C/D, server board API + perturbation, repo on GitHub, carrier board v1 designed (2026-09-29 … 10-02)
