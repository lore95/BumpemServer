# Safety

Sources: thesis §2.10; manual "Safety Considerations", §6.1 step 8; `legacy/Arduino_Script.ino`.

## Claimed
- 200 N max force "enforced in the control software" (thesis §2.10).
- Global `stop` command (thesis §2.10, manual).
- GRAIL treadmill e-stop in reach; overhead fall-arrest harness; breakaway cable.
- Shutdown order: treadmill fully stopped **before** stopping control (loss of tension = risk).

## Actual firmware behavior (gaps to close)
1. **No force clamp on the target.** `maxForce = 200` is only the ADC scale (`.ino:40`). The effective limit is DAC saturation + ESCON current limit.
2. `stop` disables drivers, zeroes the DAC and **halts forever** (`while(true)`, `.ino:172`). Tension drops to zero. Recovery needs a power cycle or re-flash.
3. `stop` is not read during an impulse (blocking loop, up to 600 ms).
4. **Serial port contention.** MATLAB opens the port at the first perturbation (`MATLAB_script.m:99`). From then on, the Arduino Serial Monitor cannot open it, so the manual's "type stop in the serial monitor" path is unavailable during a trial.
5. No host watchdog: if the PC crashes, the Teensy keeps running at baseline (acceptable) but cannot be stopped from the software.

The new host must own the single port and expose stop as a first-class, always-available action.
