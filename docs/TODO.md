# To do

Ordered by **urgency**: each section must be done before the one below it matters. Rewritten 2026-11-05.
Tick items off and tell Claude what you found so `STATUS.md` stays current.

**Danger:** 🔴 injury or burnt hardware if skipped / done wrong · 🟠 damaged electronics or misleading data · 🟢 low.
**Needs:** `lab` (at the treadmill) · `subject` (a person on the treadmill) · `parts` · `electrician` / `supervisor` · `Mac` (no lab) · `Claude`.
**status?** = no result recorded since the item was written: tell Claude whether it is done.
Teensy on the Mac: `/dev/cu.usbmodem169222501`, good USB socket. Lab PC: double-click `.bat` files only.

---

## 1 · 🔴 Safety: before anyone is in the harness
Blocks every session with a person. None of the study checks below need a person in the harness.
- [ ] 🔴 **E-stop parts:** Hirose DF11-12DS housing + DF11 crimp terminals per RSP-2000 (CN501), or plan to solder · `parts` · status?
- [ ] 🔴 **Wire the e-stop:** CN501 pin 7 + pin 11, one NO contact per 48 V supply (A, B, C, D) (`knowledge/wiring.md` → e-stop) · `lab` `parts`
- [ ] 🔴 **Test the e-stop** before every session: 48 V on, press → every ESCON LED off; release → back on · `lab`
- [ ] 🔴 Ask the technician for a **fail-safe** e-stop (now a cut wire means the button does nothing) · `supervisor`
- [ ] 🔴 **Electrician:** hand over `docs/electrician/power-requirements.pdf`: breakers / circuits for the towers' sockets (4 towers ≤ ~2.1 kW peak), cover for the RS-15-24's open 230 V terminals, earth ⏚ → chopper terminal 3 on tower B, RSP-2000 mains side · `electrician` · status?
- [ ] 🔴 Electrical safety inspection (DGUV V3)? One power strip per tower, each on its own wall socket (no strip in a strip; RSP-2000 inrush 50 A) · `supervisor`
- [ ] 🔴 **Tower B chopper → ESCON cable:** replace the 14 AWG wire with 1.5 mm² fine-stranded + insulated ferrules (48 V off, chopper < 1 V, photo both ends, + to +, − to −, no short) · `lab` `parts` (ordered 2026-10-19) · status? (B was driven on 2026-11-03)

## 2 · Next lab visit: accurate pulls, then the study (blocked: no lab access since 2026-11-05)
In this order. Ask Claude for an update bundle first (`build_bundle.sh --update`: study page, calibration).
- [ ] 🟢 Install the update on the D-Flow PC: `update.bat` → `apply_calibration.bat` (gains A 1.013, B 2.075, C 0.953, D 0.998) → `start_server.bat` · `lab` `Claude`
- [ ] 🟠 **Zero sensors** with the ropes installed and slack → **Save as default** (again after any rope / sensor change; ropes were changed, reported 2026-11-05) · `lab`
- [ ] 🟠 **After moving a tower:** back at its place (front / left / back / right, same distance), rope at harness height, cables not pulled at the plugs, then Zero sensors. Mark the floor positions once so they can be found again · `lab`
- [ ] 🟠 New ropes: with the tower at its furthest pull, ≥ 3 turns stay on each drum; splices hold after the first pulls (look at them before each session for a while) · `lab`
- [ ] 🟠 **Rope paths B and C:** power off, pull each rope by hand vs A / D (B reaches only 44–48 % of the target, C was stuck; B's drive shaft was worn at the collar, 2026-10-29) · `lab`
- [ ] 🟠 **Pull strength:** kff 3.5 test with Record (14 / 34 N per tower, ropes on a fixed point) → send the CSVs → then `kp_pulse` stepwise (D34) · `lab`
- [ ] 🟢 Rope-force noise: one recording at rest + one pull, for the oversampling decision (D39) · `lab`
- [ ] 🟢 **Vicon in the UI:** Nexus Live → Ground force → `192.168.1.60:801` → Connect → Arm → Record → a `vicon_*.csv` in `Logs/`; Fz positive when standing · `lab`
- [ ] 🟢 **Left belt:** stand on one belt, see which plate rises → pick it under "Left belt" on the study page; plates zeroed in Nexus before each session · `lab`
- [ ] 🟠 **Contacts on real data:** someone runs (and walks) on the treadmill, not in the harness; protocol with 1 block → study page → Arm → Record gait pattern 20 s at each speed used → note thresholds, noise, stride, contact time → Release → send force, events, Vicon CSVs. Claude checks them against the SLAP script (CLAUDE.md rule 5) · `lab` `subject`
- [ ] 🟠 **System delay (`latency_ms`) = board ↔ Vicon timing:** one sharp pull with someone standing on the plates, recorded → Claude measures plates → server → board → rope → enter it in "System delay" · `lab` `subject`
- [ ] 🟠 **Test block without a person in the harness** (ropes on a fixed point): pulls land at the set phase in the recording · `lab`

## 3 · Study protocol (no lab needed)
- [ ] 🟢 **Parameter list** for the protocol page (replaces the placeholder fields): per parameter subject or block, unit, limits, required, example · `Mac` (user brings the list)
- [ ] 🟢 Walking, running or both? (contact thresholds and gait phase depend on it) · `supervisor`
- [ ] 🟢 Check the protocol template opens cleanly in Excel on the lab PC (German Excel may put everything in one column) · `lab`

## 4 · Software and repos (no lab needed)
- [ ] 🟢 `git push` BumpemServer and BumpemUI (user runs `git -C … push`) · `Mac`
- [ ] 🟢 `scripts/open_loop_test.sh`: finish your uncommitted edit (`AC` mode, usage text, ACD prompt), then commit · `Mac`
- [ ] 🟢 Decide: firmware oversampling for the rope-force noise (D39; `PROTOCOL.md` first, re-flash) · `Claude` after the noise recording
- [ ] 🟢 Decide: firmware boots with `ch_D = 1` (`PROTOCOL.md` first, re-flash) · `Claude`
- [ ] 🟢 Validate the legacy `bumpem/gait.py` on a recorded MATLAB `Log_event_data_*.csv` (only if the previous student sends logs; the study uses the SLAP logic, D45) · `Claude`

## 5 · Hardware finish (status? most of these may be done: tell Claude)
- [ ] 🟠 Carrier board: in use, or still the breadboard (2026-10-27)? If needed: order v1 (Aisler / JLCPCB, `hardware/carrier/fab/bumpem-carrier-gerbers.zip`) or mill the single-sided one (`hardware/carrier/milled/fab/`), solder with its guide, meter checks (3.3 V ↔ GND no short, each MSTB pin → its socket pin), then one module at a time (ferrules, Pull 10 N → only that rope moves) · `lab` · status?
- [ ] 🟠 **Amplifier range** per module: pull hard, IAA100 output ≤ 3.3 V (`knowledge/calibration.md`) · `lab`
- [ ] 🟢 Tower B: label the old ESCON "faulty: USB + enable" (repair quote only as a spare); motor test 3d (red wire ↔ motor body: OL) · `lab`
- [ ] 🟢 Tower B: keep the 200 kg cell (gain 2.075 works) or buy a 100 kg DYMH-103 like A / C / D? · `supervisor`

## 6 · Before final testing
- [ ] 🟢 ESCON configs of C and D: upload in ESCON Studio (look only) → `escon/`; confirm 0–10 V = 0–30 A like A / B; then decide `i_full` / `kt` (`knowledge/control.md`) · `lab`
- [ ] 🟢 Screenshot each ESCON's firmware version (look only) · `lab`
- [ ] 🟢 Pull direction: measure tower positions and rope height vs harness height (geometry assumes 0 / 90 / 180 / −90°, horizontal ropes; `bumpem/geometry.py`) · `lab`

## Scheduled
- [ ] 🟢 Call with the previous student: `QUESTIONS.md`, ask for recorded MATLAB logs

## Done (recent first)
- [x] Study runner + study page (D44, D45, U14, U15; 2026-11-05): gait pattern per belt (SLAP logic, thresholds from plate noise), blocks, random / predefined steps, phase of stance or stride, simulator-tested
- [x] All four channels on by default: `bumpem serve --modules` default ABCD; the lab `.bat` files already pass ABCD (2026-11-05)
- [x] New 3 mm ropes spliced and fitted on the towers (reported 2026-11-05)
- [x] All printed parts mounted (incl. RSP-2000 brackets); every tower carries all its own components, so it moves as one unit (reported 2026-11-05)
- [x] Load cells calibrated with weights (2026-11-03): A 1.013, B 2.075, C 0.953, D 0.998 (`calibration/`, D42 / D43)
- [x] Settings re-applied after a board restart + UI warning (D41, 2026-11-03)
- [x] Closed-loop pull tests on A, B, C, D (2026-11-03, tests 1–3): firmware defaults found, kff 2 too weak → kff 3.5 next
- [x] Tower B driven by the Teensy with its new ESCON and 24 V amplifier (2026-11-03 tests)
- [x] Vicon: server on the D-Flow PC, Nexus at 192.168.1.60:801, SDK shipped as a wheel (D36), `vicon_check` connects (2026-11-02)
- [x] Offline bundle + update path for the lab PC (D28, D35; 2026-11-02)
- [x] ESCON J6 wiring fixed on all four towers (2026-10-28)
- [x] Replacement ESCON for B configured from A's `.edc` (2026-10-15)
- [x] Recording + saved settings (2026-10-12); 3 mm rope ordered (2026-10-19)
- [x] Earlier (2026-09-29 … 10-08): firmware v1, open-loop tests A / C / D, broken tower diagnosed, "no reply" = USB socket, carrier board designed, makerspace meeting
