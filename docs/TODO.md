# To do

Ordered by **date**, then by **danger**. Items on the same day can run in parallel.
Tick items off and tell Claude what you found so `STATUS.md` stays current. Rewritten 2026-10-07, updated 2026-10-12.

**Danger:** 🔴 high = injury or burnt hardware if skipped/done wrong · 🟠 medium = damaged electronics or misleading test · 🟢 low.
Teensy port: `/dev/cu.usbmodem169222501` (`PORT`), in the **good USB socket** (the other hub socket drops data). Every new Terminal: `conda activate BumpemHome`.

**State (2026-10-07):**
- **A (left), C (right), D (back):** test pulls work (`bumpem serve --testing`); A + D held at 2 N closed loop (kff 2, offsets zeroed). C's force reads ~73 N at rest (cut ground wire).
- **B (front, the former broken tower):** chopper OK (DIP set to 55 V), motor windings + Halls OK, new 48 V supply OK. Replacement ESCON configured + stored 2026-10-15 (`escon/moduleB_front_2026-10-15.edc`). **Not yet driven by the Teensy.**
- **Breadboard taken apart (2026-10-15):** no tower can be driven from the Teensy until the carrier board is in.
- E-stop **not wired**: the power strip switch is the only stop.
- Printed tower parts (`hardware/enclosures/`): being printed 2026-10-12. Carrier board: at the makerspace (Sebastian Stulz), expected **Fri 2026-10-16**. Replacement ESCON **arrived 2026-10-15**, mounted and wired except the 24 V supply (IAA100).

---

## Mon 2026-10-12 · today
- [ ] 🟠 Printed parts **failed 4× (2026-10-19)**: tall parts standing on end toppled halfway. Re-exported **flat, key side down** (`hardware/enclosures/out/`, fit_check 174 × 170 × 18 mm): send the new STLs to the makerspace; supports under the plate wings + DIN rail flanges; keep the fit dimensions (`hardware/enclosures/README.md`)
- [ ] 🟢 **Send print job 2 to the makerspace (2026-10-22):** `hardware/enclosures/out/bumpem-druckauftrag-2026-10-22.zip` (handoff PDF + 4 STLs: 4 × RS-15 plate, 1 × bracket B, 3 × bracket pair, 3 × IAA100 mount; bracket B 20 mm longer at the tower side)
- [ ] 🟢 **Print `hardware/enclosures/out/tower_set.stl` 4 times (2026-10-22):** one tower's RS-15 plate, IAA100 mount, 48 V A + B (zip: `out/bumpem-druckauftrag-2026-10-22.zip`). Check: RS-15 bolt + T-nut go in at both ends, the mains cables don't touch the bolt heads; bracket B's hole over the RSP's middle hole at the fan end (34.5 mm from the end, 59 mm from the edge) → M4 × 12, its T-nuts fit. Off → measure, tell Claude
- [ ] 🟢 **Second print file (2026-10-23):** print `hardware/enclosures/out/second_print.stl` once (in the zip): carrier board plate + 4 ground bar plates. Ground bars: Buy 8 × M3 × 12 + 8 M3 nuts. Check: both holes of the ONPIRA bar fall inside the slots (spacing 62–74 mm); if not, measure the hole spacing → tell Claude
- [ ] 🟢 **Carrier board plate (2026-10-23):** in `second_print.stl`. Buy 4 × M3 × 16 + 4 M3 nuts. Check: nuts fit the back pockets, board sits on all 4 standoffs, nothing underneath touches the plate
- [ ] 🟢 Printed parts (when printed): test plate slides into the slot without play? M6 bolt long enough (≥ ~5 mm thread in the T-nut; probably **M6 × 16**)? Tell Claude → `KEY_CLEAR` / bolt length, regenerate if needed
- [x] Ordered 2026-10-19: M3 × 6 (RS-15 plates), M4 × 12 (RSP brackets), M6 × 16 button heads, slot-10 T-nuts; **ferrules 0.25–0.5 mm²** for the 5 signal wires per MSTB plug; 1.5 mm² wire + ferrules for B's chopper cable
- [ ] 🟢 Per tower, following `hardware/enclosures/out/fit_check.pdf`: IAA100 on its DIN rail mount, RS-15-24 on its plate, then remove the tape
- [ ] 🔴 RSP-2000 brackets: supply **unplugged**, two people, fans free, 10 mm gap. Mains side stays with the electrician
- [ ] 🔴 Front tower chopper → ESCON cable (14 AWG, too thick for the chopper's 1.5 mm² terminals; European pin terminals do not fit it, 2026-10-15): **replace with new 1.5 mm² fine-stranded wire** (H05V-K / H07V-K, red + black, or 2×1.5 mm² cable), 1.5 mm² insulated ferrules, short as the old one (**ordered 2026-10-19**); when it arrives: 48 V off and chopper < 1 V, photo of both ends, swap, meter check + to +, − to −, no short. Must be done before B's 48 V is used again
- [ ] 🔴 Order the e-stop parts (Hirose DF11-12DS + crimp terminals per 48 V supply)
- [ ] 🔴 Give the building electrician `docs/electrician/power-requirements.pdf` (per-tower mains data, expected load, 6 questions; 2026-10-21). Ask the electrician: which breakers / circuits feed the towers' wall sockets (4 towers ≤ ~2.1 kW peak at the current 9.9 A limit, `knowledge/hardware.md` → Power); cover for the RS-15-24's open 230 V terminals; earth wire supply ⏚ → chopper terminal 3 on the front tower
- [ ] 🟢 `git push`; motor test 3d on the front tower; label the old ESCON

## Fri 2026-10-16 · carrier board (makerspace is making it; expected Friday)
- [ ] 🟠 Solder sockets, MSTB headers, protection parts (`hardware/carrier/README.md`); **nothing plugged in yet**. Board sockets = **female** (Teensy 2 × 1×24 tall, DAC 2 × 1×6); male pins only on the Teensy / DAC (already there)
- [ ] 🔴 Meter checks, board bare: **3.3 V ↔ GND no short**, 5 V not connected anywhere, each MSTB pin → its Teensy/DAC socket pin (enable 27/28/29/30, VA–VD, force 14–17), neighbouring pins **not** connected
- [ ] 🟠 Insert Teensy + DAC, USB only (no 24 V / 48 V): `bumpem monitor --port PORT` streams 100 lines/s; `bumpem info` answers
- [ ] 🟠 Move **one module at a time** to its MSTB plug (5 wires: yellow enable, blue SP+, green SP−, white GND, brown force; colours `knowledge/wiring.md`): cut each wire back to clean copper, crimp a **ferrule** (do not tin the tip: solder creeps under a screw and the contact loosens), screw into the plug. After each: testing page, Pull 10 N, 500 ms → only that rope moves
- [ ] 🔴 **C's cut white ground wire** is repaired in this step (cut behind the damage, new ferrule, into C's plug); C's rest reading must then drop from ~73 N to a few N
- [ ] 🟠 **B's first Teensy-driven pull** happens here (J2); see Front tower (B)

## After the carrier board · force sensing → closed loop
- [ ] 🟠 `scripts/force_check.py`: each module rests at a few N, a hand pull moves only its own reading
- [ ] 🟠 **Amplifier range** per module (meter): pull hard, IAA100 output **≤ 3.3 V** (`knowledge/calibration.md`: 0–3.3 V = 0–200 N)
- [ ] 🟠 Weight calibration 6 / 8 / 12 kg per module (incl. the 200 kg cell, on tower B: also compare its noise at rest with A / C / D; decide whether to buy a 100 kg DYMH-103)
- [ ] 🟠 Closed-loop test one module at a time: production page, Arm at 2–5 N, perturbation 10 N → 20 N; note target vs measured → Claude compares with `knowledge/results.md`
- [ ] 🟢 Decide `i_full` 9.9 / `kt` (`knowledge/control.md`) after reading C's and D's ESCON configs
- [x] Claude: recording to CSV (`POST /log/start`, Record button) and saved settings applied at connect (`settings.json`, Save as default) (2026-10-12)
- [ ] 🟢 On the real Teensy: production page → kff 2, baseline 2 → **Zero sensors** (ropes slack) → **Save as default** → replug the Teensy → Connect: values are back

## Front tower (B)
- [x] Replacement **ESCON 70/10** (maxon 422969) ordered (2026-10-07); arrived and wired 2026-10-15 (24 V still missing)
- [ ] 🟢 Label the old one "faulty: USB + enable"; repair quote from maxon only as a spare (no rush)
- [ ] 🟢 Motor test 3d (red wire ↔ motor body: OL), optional 3e–3h (`docs/tests/broken-tower-diagnosis.md`)
- [ ] 🟠 24 V for B's IAA100: RS-15-24 **unplugged**, +V → IAA100 pin 1, −V → pin 2 (DC side only; its 230 V side is the electrician's)
- [x] New ESCON: A's `.edc` → Download → auto-tune → Store Parameters → power-cycle check → uploaded `escon/moduleB_front_2026-10-15.edc`, config identical to A's (2026-10-15)
- [ ] 🟠 **Test pull B with the Teensy** (waits for the carrier board; breadboard taken apart 2026-10-15): B's 5 wires into plug **J2**, USB → 24 V → 48 V, testing page, Pull 5 N → 10 N, 400 ms → only B's rope moves, 10 N harder; rope slack → B's force a few N
- [ ] 🟢 Start the server with `--modules ABCD` from then on

## 🔴 Safety · before long sessions or anyone attached
- [ ] Order **Hirose DF11-12DS** housing + DF11 crimp terminals per RSP-2000 (CN501), or plan to solder
- [ ] **Wire the e-stop**: CN501 pin 7 + pin 11, one NO contact per 48 V supply (A, B, C, D) (`knowledge/wiring.md` → e-stop)
- [ ] Ask the technician about a **fail-safe** e-stop (here a cut wire means the button does nothing)
- [ ] **Test** before every session: 48 V on, press → every ESCON LED off; release → back on
- [ ] Supervisor: electrical safety inspection (DGUV V3)? One power strip per tower, each on its own wall socket (no strips plugged into strips; RSP-2000 inrush 50 A)
- [x] Ropes worn → **3 mm** low-stretch rope (Dyneema / Kevlar, ≥ 2 kN) **ordered 2026-10-19** (drum tie hole 5.59 mm, `knowledge/hardware.md`)
- [ ] 🟠 When the rope arrives: through the tie hole + eyebolt once before cutting; length W + 71 cm; ≥ 3 turns stay on the drum; figure-eight stopper knot

## Vicon · data access (no hardware from us needed)
- [ ] 🟢 Ask the Vicon administrator: which address the server PC should use (not the camera network), port 801 open, may the SDK / Python be installed (setup 1: own PC on the Vicon network; setup 3: on the Vicon PC, D22)
- [x] Vicon reachable (2026-10-19): Nexus PC 192.168.1.60, DataStream on port 801 (all interfaces); D-Flow PC 192.168.1.50 → 192.168.1.60:801 TCP test OK
- [x] Server runs on the **D-Flow PC** (192.168.1.50, user 2026-11-02, installed in `C:\Users\operator\BumpemLab`); Vicon at `192.168.1.60:801` over the PC network (TCP test OK 2026-10-19)
- [x] Find the Vicon PC (2026-10-19: on the two lab PCs checked, nothing listens on 801; only ESET `ekrn.exe` in the network list, Vicon probably not live). With Nexus **live** (+ GRAIL software running): `netstat -ano | findstr :801`, `tasklist | findstr /I "nexus shogun tracker vicon dflow"`, `ipconfig` on both PCs → Claude. ESET firewall may block 801 between PCs: IT allows it, not us
- [x] Vicon DataStream SDK: 1.13.0 Win64 downloaded by the user; shipped as a wheel in the bundle (D36), no installer on the lab PC
- [ ] 🟢 **Vicon read test:** Nexus in Live mode, force plates on → `python scripts/vicon_probe.py --host 192.168.1.60:801` (needs Python + SDK on that PC: offline install) → frame rate, device names, Fz per plate. Stand on one belt → note which device is the **left** belt. Send the output to Claude
- [ ] 🟢 Note: walking, running or both in the experiments
- [x] Offline bundle built (2026-11-02, D28): `../bumpemInstallation/BumpemLab_2026-11-02.zip` (41 MB; rebuild: `scripts/build_bundle.sh`). Target: Windows 10 IoT LTSC x64, per-user Python 3.12.10, no admin
- [x] 🟢 **Install on the Vicon PC:** add the Vicon DataStream SDK installer to `vicon/`, copy the folder to `C:\Users\<you>\BumpemLab`, `1_install.bat` (→ "All packages OK"), `start_simulator.bat` (page opens), then Teensy + `start_server.bat`. Blocked or gone after reboot → ask the administrator (app lockdown / write filter). Report each step's output to Claude (done 2026-11-02 by the user)
- [ ] 🟢 **Update the Vicon PC** (D35): Mac `scripts/build_bundle.sh --update` → copy `BumpemUpdate_<date>.zip` → unzip → `update.bat` → Y → "All packages OK". Then Board settings: kff 2, Apply, Save as default (D34). Report the window text if it stops

## Software (Claude builds, you test)
- [ ] Step 2 **PTO**: perturb a set time after a foot strike (gait events, simulated / replayed until Vicon)
- [ ] Step 3 **trials**: blocks, shuffle, 50–75 steps between perturbations, baseline first 3 s, logs
- [ ] Step 4 **Vicon live** on the lab PC: server side built (D32, sim-tested). On the lab PC: Nexus Live → UI "Ground force" card → address `192.168.1.60:801` (or `127.0.0.1:801` on the Nexus PC) → Connect; stand on each belt (which name is left? Fz positive or negative?); Arm → Record → Stop rec → a `vicon_*.csv` appears in `Logs/`. Report to Claude
- [ ] Validate `bumpem/gait.py` on a recorded MATLAB `Log_event_data_*.csv` (needs a file from the lab)
- [ ] 🟢 Fix `scripts/open_loop_test.sh` (your uncommitted edit: `AC` mode, usage text, ACD prompt), then commit
- [ ] 🟢 `git push` BumpemServer (many commits since 10-02); first push of BumpemUI (`git push -u origin main`; remote github.com/lore95/BumpemUI added 2026-10-19)
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
- [ ] 🟡 **Carrier board v2 (2026-10-26):** choose: order v1 from Aisler / JLCPCB (`hardware/carrier/fab/bumpem-carrier-gerbers.zip`), or mill the single-sided version (`hardware/carrier/milled/fab/bumpem-carrier-milled.zip`, ask for rub-out); then solder with its guide
