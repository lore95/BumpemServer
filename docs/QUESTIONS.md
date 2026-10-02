# Questions for the previous student

For the call about the Bump'em setup. Write each answer under its question.
After the call, the answers go into the docs named in *(→ …)* and the question is marked done.

Open questions on 2026-09-30.

---

## Files to ask for
Ask them to send these if they still have them:

- [ ] The **load-cell calibration sketch** that is on the Teensy now (prints `ADC: … | Voltage: … | Force: … N`)
- [ ] The **ESCON Studio parameter files** they loaded onto the drivers (`.edc`), and any saved after auto-tuning
- [ ] **Recorded trial logs** from MATLAB (`Log_event_data_*.csv` and `Perturbation_log_*.csv`)
- [ ] Any **photos or videos of the setup when it was fully wired and working**
- [ ] The earlier **Bachelor's project** documents (who built the first version?)

---

## 1. The wiring (most urgent)

**1.1** The Teensy breadboard was found disconnected from the motors. Who disconnected it, and why? Was anything else changed at the same time?
> Answer:

**1.2** Each motor driver (ESCON) has a cable with 7 wires ending in jumper pins: a set of 4 (red, blue, purple, orange) and a set of 3 (white, black, yellow). **Which colour went to which place** on the breadboard (Teensy pin, DAC output, ground)?
> Answer (traced 2026-09-30 on one driver, see `wiring.md`): black = enable, red (female) = setpoint +, orange = setpoint −, blue = force, purple = ground, yellow + white = spares. This is module C (right). Ask: are A, B, D wired with the same colours?

**1.3** Per driver, only 5 of those 7 wires should be needed: enable, setpoint +, setpoint −, and two grounds. **What are the other 2 wires for?**
> Answer (found 2026-09-30): 2 of the 7 are spare extensions, not connected at the driver.

**1.4** There is a small board with blue parts and 3 thin wires, mounted in the aluminium frame next to each motor driver. **What is it?** (A Futek amplifier? A strain-gauge board from the Bachelor's project? Something else?)
> Answer (found 2026-09-30): it is the module's **ground distributor**: joins ESCON J5.5 + J6.7 + IAA100 GND into the white wire. Ask only: anything else on it?

**1.5** Where is the **ground distributor** (the shared ground terminal strip), and what was connected to it?
> Answer:

**1.6** Where are the **Futek IAA100 amplifiers**, and how is each one powered (24 V supply)?
> Answer:

**1.7** How was the ground between the Teensy and each driver connected?
> Answer (found 2026-09-30): J5.5 + J6.7 → frame board → white wire → breadboard. Ask: where on the breadboard did the white wire go (distributor? Teensy G?)

**1.8** The motor harnesses came pre-pinned **4 + 4**: on modules C and one other, the motor's **Hall GND (blue, motor pin 6) sits on ESCON J2 pin 4 (cable shield)** and J3 pin 5 is empty. With this wiring both drivers now show a Hall sensor error. Who made these harnesses? Did the motors run with exactly this wiring during the thesis?
> Answer: (found 2026-10-01: moving blue to J3 pin 5 cleared the error on module C)

*(→ `docs/knowledge/wiring.md`, `docs/hardware-photos/README.md`)*

---

## 2. The motor drivers (ESCON 70/10)

**2.1** Did you load the **Stanford configuration file** onto the drivers as it was, or did you change settings?
> Answer:

**2.2** In that file, **10 V on the setpoint input = 30 A** of motor current. The Teensy code assumes **3.3 V = 30 A**. Which one is true on our drivers? (If it's the Stanford file, the motors never got more than about 10 A.)
> Answer:

**2.3** Which driver belongs to which module (A left, B front, C right, D)? When was each one last **auto-tuned**?
> Answer:

**2.4** Is there a **shunt regulator** (maxon DSR 70/30) for each module, and what cut-off voltage was it set to?
> Answer (found 2026-09-30): yes, maxon 235811 on the frame. Ask: DIP setting (cut-off voltage)? Where is each 48 V supply and its on/off switch? Is there an e-stop in the 48 V circuit?

**2.5** The e-stop button: how was it wired before (which terminals on the 48 V supply)? Did one button stop all modules? Was it tested before sessions?
> Answer:

**2.6** How many **48 V supplies (RSP-2000-48)** and **24 V supplies (RS-15-24)** are there, and which module does each one feed? Who in the lab handles the mains (230 V) connections?
> Answer:

*(→ `escon/README.md`, `docs/knowledge/control.md`, `docs/knowledge/wiring.md`)*

---

## 3. Module D (the 4th motor)

**3.1** Why is module D out of service? The thesis says **mechanical damage**; the manual says **a new motor driver needs to be bought**. Which is it?
> Answer:

**3.2** ~~Which direction was D meant to pull: backwards?~~ Answered 2026-10-02: back (project lead), in `knowledge/hardware.md`.
> Answer:

*(→ `docs/knowledge/hardware.md`)*

---

## 4. Force sensors and calibration

**4.1** Which **load cell** (sensor 1–4 in the calibration table) is on which **module** (A–D)?
> Answer:

**4.2** The calibration sketch reads only **Teensy pin A1** (module B's input). Was it used for all four sensors one by one, or only for module B?
> Answer:

**4.3** The thesis gives the load cell rating as 100 kg, 1000 N and 980 N in different places. What is the correct maximum?
> Answer:

**4.4** How were the amplifiers set (DIP switches, zero and span knobs)? Were they changed after calibration?
> Answer:

*(→ `docs/knowledge/calibration.md`)*

---

## 5. The control code (Teensy)

**5.1** The code holds a pulse for **600 ms**, but the thesis says **300 ms**. Which was used for the thesis experiments?
> Answer:

**5.2** At start-up the code prints "baseline = 10 N" but actually uses **5 N**. Which baseline did you use in the trials?
> Answer:

**5.3** The feedforward term is multiplied by **7.5**. Where does that number come from (tuning, a calculation, trial and error)?
> Answer:

**5.4** The motor torque constant in the code is **0.1524**. Is that from the datasheet, or measured? (The Stanford file says 0.227.)
> Answer:

**5.5** The thesis says the **200 N limit was "enforced in the control software"**, but the code has no such limit. What was meant?
> Answer:

*(→ `docs/knowledge/control.md`, `docs/knowledge/safety.md`)*

---

## 6. Running the experiments

**6.1** During a trial, **how did you stop** the system in an emergency? (MATLAB holds the USB port, so typing `stop` in the Arduino monitor wasn't possible.)
> Answer:

**6.2** Where are the **recorded trial data** (MATLAB logs, force data), and which files belong to which participant/trial?
> Answer:

**6.3** Vicon: which **PC**, which **DataStream SDK version**, and is the IP still **192.168.10.1**? Which force plate is **left** and which is **right**?
> Answer:

**6.4** Was the treadmill (**D-Flow**) ever controlled by the scripts, or always by hand?
> Answer:

*(→ `docs/knowledge/gait_detection.md`, `docs/knowledge/experiment.md`)*

---

## 7. Anything else
**7.1** Is there anything that was known to be broken, fragile or "just worked that way" that we should know about?
> Answer:
