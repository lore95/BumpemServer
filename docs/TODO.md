# To do

Ordered by **urgency**: each section must be done before the one below it matters. Rewritten 2026-11-19 after the first walking and running studies.
Tick items off and tell Claude what you found so `STATUS.md` stays current. PDF of this file: `scripts/todo_pdf.sh` → `docs/todo.pdf`.

**Danger:** 🔴 injury or burnt hardware if skipped / done wrong · 🟠 damaged electronics or misleading data · 🟡 small data error · 🟢 low.
**Needs:** `lab` (at the treadmill) · `subject` (a person on the treadmill) · `parts` · `electrician` / `supervisor` · `Mac` (no lab) · `Claude`.
**status?** = no result recorded since the item was written: tell Claude whether it is done.

---

## Works now (2026-11-19)
- **Carrier board** (JLC, plated): soldered, DAC in sockets underneath (D52), Teensy finds it at power-up, all 4 module cables plugged in.
- **Lab PC:** server on COM3 + Vicon `192.168.1.60:801`, clocks in sync (Teensy ±0.3 ms, Vicon ±0.4 ms), no lost frames.
- **All four towers pull.** Send → rope force rising ≈ 36 ms (delay test 2026-11-18; thesis 36 ms).
- **Walking study:** stride 949–968 ms, contact ≈ 560 ms, pulls at 33 % of the cycle as set, the pattern's step gaps followed exactly.
- **Delay test page** (pulls A → B → C → D, report with plates-vs-board timing) and **session zip** + **Import saved study** (update `BumpemUpdate_2026-11-19_1558`, built, not installed yet).

## 0 · Not working now (found in the studies of 2026-11-19)
Files: `tests/*_20261119_112556_*` (walking 1.7 m/s, 100 N), `tests/*_20261119_120754_*` (running 3.33 m/s, 150 N); kff 5.5, baseline 5 N.
- [x] ~~🔴 **Running: steps detected wrong.** Measured stride 325–347 ms, real ≈ 704 ms: steps counted ≈ 2×, pulls 65 ms after touch-down instead of ≈ 141 ms (20 % of the cycle), "right" also fired on left-foot landings. Causes: runner on / across the right belt (both plates > 300 N 19 % of the time, impossible in running), impact bounce (73 contacts < 60 ms on the left plate), thresholds left at 100 / 25 N (plate noise 28–37 N). Fix: one foot per belt (tape line) `lab` + ignore contacts < 60 ms, pause after each touch-down, running thresholds from body weight `Claude`~~ → fixed with the summed belts (D57, 2026-11-23)
- [ ] 🔴 **Start allowed with an implausible gait pattern:** the mode check flagged the running stride, the block started anyway. Fix: refuse Start (or explicit "use anyway") · `Claude`
- [ ] 🔴 **Pulls never reach the asked force:** the motor command is at maximum (DAC 4095) for 130–180 ms in all 24 pulls. 100 N → 58–91 N net, 150 N → 58–90 N net; single towers at most B 56–74, C 49–98, A 82–96, D ≤ 111 N. Limit = driver current at full scale (ESCON 3.3 V = 9.9 A, `knowledge/control.md`), not kff. The saved amplitude (100 / 150 N) is not what the person felt: analyse the measured rope force. Fix: warn in BumpemSetUp above the deliverable force `Claude`; more current needs the ESCON scaling changed `supervisor` (technician; motor / driver limits first)
- [ ] 🟠 **Participant ID was a first name** ("Carlo" in the events file and every file name). Fix: ID must contain a digit (e.g. S014) `Claude`; keep those files out of git
- [ ] 🟠 **Pulls 20–25 ms late** (System delay 0). Walking: enter **25 ms** at Start `lab`. Running value unusable until the step detection works
- [ ] 🟠 **Rope tension between pulls** 6.5–9 N for 5 N, ±2–4 N; **B slack (< 1 N) 3–4 % of the time** (jerk at the next pull). kff 5.5 also raises the rest tension. Fix: tune for the baseline (test together) `lab` `Claude`
- [ ] 🟠 **B and C weakest;** diagonals off by up to 11° (B's side pulls less). Rope paths B and C (section 2)
- [ ] 🟡 **Walking: 5 foot strikes missed**, 4 right before a pull (recovery step across the belts): the next pull one step late
- [ ] 🟡 **Board settings:** calibration not applied (gains 1.0 / 2.12 / 1.0 / 1.0 instead of 1.013 / 2.075 / 0.953 / 0.998); max force 200 N above the fault limit 195 N
- [ ] 🟡 **Plates not zeroed:** down to −70 N (running), −22 N (walking); foot-off threshold is 25 N
- [ ] 🟢 Foot strikes not logged during the warm-up, foot-offs are (counts 172 vs 234: confusing) · `Claude`
- [ ] 🟢 STOP 51 s into the running recording, before the study load, forces normal: on purpose? · status?
- [ ] 🟢 Delay report: "scatter" overstated (adds each part's worst case), command delay shows negatives (below the method's resolution), lag meaningless while pulls fall short, gains missing in the header · `Claude`
- [ ] 🟢 Plate and board data reach the server up to 15 ms late (95 %), both: Windows' 15.6 ms timer? (unverified) · `Claude`

## 1 · 🔴 Safety: before anyone is in the harness
Studies with a person already ran on 2026-11-19 (100 N walking, 150 N running) **without the e-stop**. Nothing below is done.
- [ ] 🔴 **E-stop parts:** Hirose DF11-12DS housing + DF11 crimp terminals per RSP-2000 (CN501), probably not at the makerspace (Reichelt / Mouser, or pre-crimped leads) · `parts`
- [ ] 🔴 **Wire the e-stop, two-box version** (chosen 2026-11-16): box 1 → supplies A + B, box 2 → C + D, CN501 pin 7 + 11; mount side by side, label "PRESS BOTH". Not fail-safe (`docs/makerspace-list.md`) · `lab` `parts`
- [ ] 🔴 **Test the e-stop** before every session: 48 V on, press → every ESCON LED off; release → back on · `lab`
- [ ] 🔴 Technician to agree with the two-box version (a cut wire = button does nothing) · `supervisor`
- [ ] 🔴 **Electrician:** `docs/electrician/power-requirements.pdf` (breakers, cover on the RS-15-24's 230 V terminals, earth → chopper terminal 3 on tower B, RSP-2000 mains side) · `electrician` · status?
- [ ] 🔴 Electrical safety inspection (DGUV V3)? One power strip per tower, each on its own wall socket · `supervisor` · status?
- [ ] 🔴 **Tower B chopper → ESCON cable:** 1.5 mm² fine-stranded + insulated ferrules instead of the 14 AWG wire · `lab` `parts` · status?

## 2 · Next lab visit
- [ ] 🟢 Install `BumpemUpdate_2026-11-20_1503` (sets the 20 A control values and the 75 N cap, D55, D56): `update.bat` → `start_server.bat` → Firefox Ctrl + Shift + R · `lab`
- [ ] 🟠 `apply_calibration.bat` (gains above), then max force 196 N / fault 200 N → Apply → **Save as default** · `lab`
- [ ] 🟠 **Zero the plates in Nexus** before each session (look only in D-Flow) · `lab`
- [ ] 🟠 **After any rope change: rope wound neatly on every drum** (side by side, no crossing turns): a badly wound rope catches and releases, the tower then jumps 0–15 N while holding (C, 2026-11-20) · `lab`
- [ ] 🟠 **Zero sensors** with the ropes on and slack → Save as default (after any rope / sensor change) · `lab`
- [ ] 🟠 **Rope paths B and C:** power off, pull each rope by hand vs A / D; B's drum bolts, B's shaft at the collar (worn, 2026-10-29) · `lab`
- [ ] 🟠 **Running (D57, after the next update): check left / right once:** record a short running block with video (or foot markers) and compare the page's left steps with the real left foot; gait pattern stride ≈ 0.7 s per side. Feet may land on either belt · `lab` `subject`
- [ ] 🔴 **C's drum slips on its shaft** (marker check 2026-11-20; slips again at 75 N on the 20 A range: holds only 58 N, 2026-11-20). Marker line broken after the 75 N pull (size not measured). User: the shaft profile will be changed anyway (new shaft). Collars are **clamp type** (user, 2026-11-20). D slips too (100 N, also after tightening): same fix. Before: caliper on the shaft under the collar vs 2 cm away (wear). Which joint: drum ↔ collar or collar ↔ shaft? Fix with the collar guide (`hardware/motor_unit/`: 3 × #6-32 × 1/2" bolts + washers, threadlocker, clean bore), marker check again after 10–20 N pulls. No high-force pulls on C until then · `lab` `parts`
- [ ] 🟠 **Marker check B and D** (line across shaft, collar, drum hub; pull by hand; offset = slip). B slipped in October · `lab`
- [ ] 🟠 Repeat the ceiling test on A and C after C's fix (A: 57 / 75 N, 7 sudden drops per pull without slipping: cause open) · `lab`
- [ ] 🟠 **Ceiling test, each tower (A + C done 2026-11-20 with C slipping; B, D open):** ropes on a fixed anchor that holds > 150 N, nobody attached, stand clear. Delay test page: one tower ticked at a time, force **100 N**, rounds 2, pull duration **500 ms**, gap 3000 ms → the DAC is at full scale (9.9 A) the whole pull: plateau = that tower's real maximum, vs ≈ 118 N in theory = its friction loss. Send the report (.html) · `lab`
- [ ] 🔴 **ESCONs are on 3.3 V → 20 A (2026-11-20): the board settings must match on every PC before any pull.** `i_full` 20, kff 0.9, kp 0.08, kd 0.2 (A on target at 20 / 50 / 100 N on the Mac). Mac: saved as default 2026-11-20. **Lab PC: the next update (`update.bat`) sets them** (D55; its window lists the old → new values). Then start_server → Connect → check kff 0.9 / `i_full` 20 on the page before the first pull · `lab`
- [ ] 🟠 **Start overshoot on a solid anchor:** 50 and 100 N on A on a load-rated point. Wobbly anchor (2026-11-20): 50 N → 72 N peak, 100 N → 144 N peak in the first ~100 ms. Gone on a solid anchor = anchor; else tune kp / ramp · `lab`
- [ ] 🟠 **C flips 17 ↔ 27 N every 10 ms at 20 N** even at kd 0.2 (A: calm): check C's rope seating, attachment, shaft under load · `lab`
- [ ] 🟠 **Delay test with the 20 A settings** (2 rounds, 10 / 20 N): ratio ≈ 0.85–1.0? · `lab`
- [ ] 🟢 System delay 25 ms for walking; check the delay report's recommendation after the next block · `lab`
- [ ] 🟢 Rope-force noise: one recording at rest + one pull, for the oversampling decision (D39) · `lab`

## 3 · Software (`Claude`, no lab needed)
- [x] Running step detection: summed belts, side from the weight shift (D57, 2026-11-23; replay stride 701 / 700 ms)
- [ ] 🟢 New update package with D57 for the lab PC · `Claude`
- [ ] 🔴 Refuse Start when the gait pattern is implausible (or explicit "use anyway", logged)
- [ ] 🟠 BumpemSetUp: warn when a block asks more than the towers deliver (≈ 60–90 N now)
- [ ] 🟠 Participant ID must contain a digit
- [ ] 🟢 Log foot strikes in the warm-up; delay report fixes (section 0); Windows timer check
- [ ] 🟢 Lab-week guide PDF still names an older update
- [ ] 🟢 `git push` BumpemServer and BumpemUI (user runs `git -C … push`) · `Mac`
- [ ] 🟢 `scripts/open_loop_test.sh`: finish your uncommitted edit, then commit · `Mac`
- [ ] 🟢 Decide: firmware oversampling (D39), firmware boots with `ch_D = 1` (`PROTOCOL.md` first, re-flash)

## 4 · Hardware finish
- [ ] 🔴 **Steel drive shafts for all four towers** (aluminium shafts slip with the 20 A range: C 75 N, D 100 N, B creeps at 120 N; 2026-11-20). Stanford: "3/8in x 3in Linear Shaft" (build guide p. 11; material not stated, linear shafts are hardened steel; the guide's "6061 T6" is the force-sensor dogbone, not the shaft) · `parts` `lab` `supervisor`
  1. **Measure first** (caliper): shaft diameter 9.52–9.53 mm (3/8 in) or 10.00 mm (metric: order 10 mm h6 instead), length (Stanford 76.2 mm), collar and bearing bore.
  2. **Order** one 1 m rod, hardened and ground, h6, CF53 (1.1213), 9.525 mm (≈ 30 cm needed for 4 + spares): [metallstore.de](https://www.metallstore.de/stahl/1.1213-gehaertete-praezisionswelle-cf53/) (from ≈ €43), [grafe-shop.de](https://www.grafe-shop.de/index.php?view=overview&categories_catid=1156) ("Welle, Stahl W 9,525mm x 1000mm, h6 - CF53", ≈ 59 HRC); or cut to length 4 × 76.2 mm: [PBC Linear Europe](https://www.pbclinear.eu/product/linear-shafting/) (Düsseldorf, confirm hardened), [LTK](https://shop.ltk.de/de/praezisionswellen). Prices checked 2026-11-20, via the lab's purchasing.
  - **Ready cut, no work (preferred; user expects inch, 2026-11-20):** ask for a quote for 4 (+2 spare) × 3/8" × 76.2 mm, hardened and ground, h6 / Class L, ends chamfered: [PBC Linear Europe](https://www.pbclinear.eu/product/linear-shafting/) (Düsseldorf, cut to length), [Thomson 3/8 L CTL](https://www.thomsonlinear.com/en/product/3/8%20L) (via a Thomson distributor), [metallstore.de](https://www.metallstore.de/stahl/1.1213-gehaertete-praezisionswelle-cf53/) (9.525 mm in stock; ask for Zuschnitt).
  3. **Cut** (only for the 1 m rod) with an abrasive cut-off wheel (hardened: no hacksaw), deburr; optional D-flat by grinding (workshop).
  4. **Fit** (`hardware/motor_unit/disassembly-guide.pdf`, `collar-fix-manual.pdf`): clean, clamp collar tight, blue threadlocker; check the drum screws (joint 4: with no slip the drum takes the full torque, ≈ 4.4 N·m at 20 A).
  5. **Test** on a solid anchor: marker line after 50 / 100 / 150 N; no fade over the hold. Then raise the study limit (now ≤ 50 N).
- [x] ~~Driver current: read the ESCON scaling of all four~~ → done 2026-11-20 (D55, `escon/`)
- [ ] 🟠 **Amplifier range** per module: pull hard, IAA100 output ≤ 3.3 V (`knowledge/calibration.md`) · `lab`
- [ ] 🟢 **Reprint the carrier plate** (19 mm standoffs, `hardware/enclosures/out/carrier_plate.stl`) + 4 × M3 × 25 · `parts`
- [ ] 🟢 Fix the DAC rows in `hardware/carrier/gen_carrier.py` before any new board order (D52) · `Claude`
- [ ] 🟢 Update the soldering guide PDF to as-built (1 MΩ in the D1–D4 places, R5–R8 empty) · `Claude`
- [ ] 🟢 Tower B: label the old ESCON "faulty: USB + enable"; keep the 200 kg cell or buy a 100 kg DYMH-103 · `supervisor`
- [ ] 🟢 Pull direction: measure tower positions and rope height vs harness height (geometry assumes 0 / 90 / 180 / −90°, horizontal ropes) · `lab`

## Later · optional: hardware clock sync (Vicon ↔ Teensy)
- [ ] 🟢 Vicon sync output (voltage, connector, permission) · `supervisor`; Teensy pin 2 is free (3.3 V max: divider for 5 V) · `Claude` `lab`

## Done (recent first)
- [x] ESCON range 3.3 V → 20 A on all four (backups + 20 A files `escon/`); A pulls 20 / 50 / 100 N on target (23.3 / 53.6 / 100.4 N, 14.3 A) with kff 0.9, kd 0.2 (2026-11-20)
- [x] Replay of recorded plates as the Vicon source: walking + running of 2026-11-19 (D54)
- [x] Session zip per study, study name, participant ID, Import saved study (D53, U26, 2026-11-19)
- [x] First walking and running studies with a person, analysed (2026-11-19)
- [x] kff 2 → 3.5 → 5.5 (delay tests 2026-11-18: 0.5 → 0.7 of the target at 10 / 20 N)
- [x] Delay test page with plates-vs-board timing (U24, U25, 2026-11-18)
- [x] Carrier board (JLC) soldered and working; DAC underneath (D52, 2026-11-18)
- [x] Welcome page (U23), delay report + error log (D51), final protocol + BumpemPattern (D50) (2026-11-16)
- [x] Lab PC connections + clock sync in use (D49); Vicon recorded with the board; left / right plates mapped
- [x] Study runner + study page (D44, D45, U14, U15)
- [x] New 3 mm ropes; printed parts mounted; load cells calibrated (D42 / D43); settings re-applied after a board restart (D41)
