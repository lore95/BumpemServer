# Bump'em: power and e-stop checklist

**What:** bring the Bump'em power supplies back into use and set up the emergency stop.
**Who:** done by the project lead (no technician available). **No work on the 230 V side**: inspect only; anything faulty goes to the university's facilities / electrical workshop. Ask the supervisor about the electrical safety inspection (DGUV Vorschrift 3).
**Date:** ______________

The system pulls a person on the GRAIL treadmill through ropes driven by motors (one module per direction).
All supplies are currently **disconnected from the mains**. The low-voltage side (48 V / 24 V DC) is wired by us;
the 230 V side is only inspected here.

---

## 1. The power supplies
Per mounted module (2026-10-02: A left, C right, D back; B front not installed). Counts to be confirmed on site.

| Unit | Qty | Mains input (label / datasheet) | Output | Feeds |
|---|---|---|---|---|
| **Mean Well RSP-2000-48** | ___ | 200–240 VAC **12.3 A** max (label); 10 A typ. @ 230 VAC full load; inrush 50 A typ. (cold start); leakage < 2 mA @ 240 VAC | 48 V DC, 42 A, 2016 W | maxon shunt regulator 235811 → maxon ESCON 70/10 motor driver |
| **Mean Well RS-15-24** | ___ | 100–240 VAC 0.35 A (label) | 24 V DC, 0.625 A (15 W) | Futek IAA100 load-cell amplifier |

Sources: unit labels (photos in `docs/hardware-photos/`), Mean Well RSP-2000 datasheet (`docs/reference/meanwell-rsp-2000-spec.pdf`).

Expected load: motor current is limited by each driver (configured limit 30 A in the reference configuration → about 1.4 kW per module at 48 V, peak, during pulses of ≤ 1 s). Normal operation is far below that. The label maximum above is the conservative figure.

## 2. Checks
- [ ] **Mains cable** on each supply (unplugged): intact plug; RSP-2000 screw terminals **⏚ / L / N** tight, **earth connected**, terminal cover on, cable strain-relieved; RS-15-24 likewise. Faulty → university, not DIY.
- [ ] **Circuit capacity**: first test = 1 × RSP-2000-48 (12.3 A max, 50 A inrush) + RS-15-24 (0.35 A) on one wall socket or one 16 A switched strip. All modules: each RSP-2000 on its own socket/circuit.
- [ ] **A switch for the 48 V supplies** reachable from the operator position (the RSP-2000 has no power switch): the switched strip.
- [ ] **Earthing** (ask the supervisor if unsure): the RSP-2000 ⏚ goes to the shunt regulator's safety-earth terminal (pin 3). The motor drivers' signal ground is joined to a microcontroller that is USB-connected to a PC. maxon warns about potential differences between the driver supply and a PC (ESCON 70/10 hardware reference, "Hot plugging the USB interface…"). Is anything else needed?
- [ ] **Emergency stop** (section 3): low-voltage side, CN501 is isolated from the mains per the datasheet; wire it yourself with the supply unplugged.

## 3. Emergency stop: current design and question
Design from the Stanford Bump'em build guide (pp. 13–15), which this system follows:

- Mushroom e-stop with an **SPST-NO** contact block, wired to each RSP-2000's control connector **CN501 pin 7 (Remote ON-OFF)** and **pin 11 (+5V-AUX)**.
- Datasheet: **short** between pin 7 and pin 11 = **output OFF**; **open** = **output ON**. Pressing the button closes the contact → 48 V output off.
- CN501 = Hirose DF11-12DP; mating housing DF11-12DS + DF11 crimp terminals.
- One NO contact block per RSP-2000, stacked on one button.

**Known weakness:** not fail-safe. A broken wire or loose connector leaves the contact open → the supply stays **ON** and the button does nothing.
The mains, and the supply's own +5 V/+12 V auxiliary outputs, stay live after pressing.

**Open question for the supervisor:** is this acceptable under the lab's safety rules, or is a fail-safe variant required (e.g. an NC e-stop contact holding a relay, so a wire break also switches off)? Until answered: **test the e-stop before every session**.

Pressing the stop removes all rope force (intended). The treadmill has its own e-stop, which stays the primary stop for the person on it.

## 4. Sign-off
| Item | Checked by | Date | Notes |
|---|---|---|---|
| Mains cables inspected, earth connected, covers fitted | | | |
| Circuit capacity checked | | | |
| 48 V switch position | | | |
| E-stop wired (CN501 pin 7 + 11), supervisor informed | | | |
| E-stop tested (press → 48 V off, release → on) | | | |
