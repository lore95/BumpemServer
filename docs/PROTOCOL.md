# Host ↔ Teensy serial protocol

Single source of truth. `bumpem/protocol.py` must mirror this file.

## v0 — legacy (current firmware, `legacy/Arduino_Script.ino`)

Transport: Teensy USB serial (baud ignored by USB; 115200 set). Line-terminated `\n`, case-insensitive, trimmed.

### Commands (host → Teensy)
| Cmd | Action | Modules |
|---|---|---|
| `a` `b` `c` `d` | single impulse, 100 N | A / B / C / D |
| `ab` `bc` `cd` `da` | diagonal, 70.7 N each | pair |
| `stop` | enable LOW, DAC 0, **halt forever** | all |

Impulse: 50 ms ramp from 5 N → target, hold to 600 ms, then back to baseline. Blocking.
Unknown commands are silently ignored.

### Telemetry (Teensy → host)
Every loop (~10 ms + print time), one line per module:
```
<millis>,<A|B|C|D>,<target_N>,<measured_N>
```
Interleaved with free-text status lines (e.g. `Running impulse on MODULE 1 (A)...`, `Stopped.`).
Host parser: accept lines matching `^\d+,[ABCD],-?\d+\.\d+,-?\d+\.\d+$`; treat everything else as a status message.

### Known issues (fix in v1)
- No ack / no error on unknown command.
- No force clamp; `stop` is irreversible; commands ignored during impulse.
- Telemetry and status share one stream without a type prefix.

## v1 — current (`firmware/src/main.ino`)

Board-agnostic: the firmware knows channels, forces and times only. Angles, gait, PTO and
sequences live on the host. Parameter defaults reproduce v0 behavior.

Transport: USB serial, one ASCII line per message, `\n` terminated. Host→board tokens are
space-separated, case-insensitive. Board→host lines are comma-separated, first field = type.
Every command gets exactly one `A` line, in order. Any received line feeds the watchdog.

### Commands (host → board)
| Command | Allowed in | Effect |
|---|---|---|
| `INFO` | any | `I,proto=1,fw=<ver>,board=teensy41,channels=4,f_hard_max=200` |
| `GET [name]` | any | One `P,<name>,<value>` per parameter (or the one named), then ack |
| `SET <name> <value>` | no pulse pending/active | Set a parameter (table below). Range-checked |
| `ARM` | DISARMED, ESTOP | Enable drivers, ramp 0 → baseline over `arm_ms` → ARMED |
| `PULSE <id> <delay> <rise> <dur> <fall> <aA> <aB> <aC> <aD>` | ARMED, no pulse pending/active | Schedule one pulse (below) |
| `ABORT` | any | Cancel pending pulse; ramp an active one back to baseline over its `fall` |
| `RELEASE [ms]` | ARMED, FAULT | Ramp all targets to 0 over `ms` (default 1000), then disable → DISARMED |
| `ESTOP` (alias `STOP`) | any | Drivers disabled and DAC 0 immediately → ESTOP. Recover with `ARM` |
| `CLEAR` | FAULT | → ARMED |
| `STATS` | any | `I,loop_us_max=..,overruns=..,tx_drops=..,uptime_ms=..` (resets max) |
| `PING` | any | Ack only (watchdog feed) |

**Safety:** only ESTOP and RELEASE drop tension. Stop the treadmill before either (`docs/knowledge/safety.md`).

### Pulse
Times in ms, amplitudes in N **relative to baseline** (`docs/knowledge/perturbation_definitions.md`).
Target per channel, `e` = time since pulse start:
```
e < rise                : baseline + a * e/rise
rise <= e < dur - fall  : baseline + a
dur - fall <= e < dur   : baseline + a * (dur-e)/fall
```
- `delay` 0–10000: start = receipt + delay (host computes it from PTO).
- `dur` = start to end, ramps included. Requires `rise + fall <= dur <= pulse_max_ms`. `rise = fall = dur/2` is triangular.
- Rejected (`A,ERR`) if any `a < 0`, `a > 0` on a disabled channel, or `baseline + a > fmax_n`.
- v0 `a` equivalent: `PULSE 1 0 50 600 0 95 0 0 0`. v0 `ab`: amplitudes `65.71 65.71 0 0`.

### States
`DISARMED` (boot) → `ARMING` → `ARMED` ⇄ `FAULT`; `RELEASING` → `DISARMED`; any → `ESTOP`.
Boot does **not** ramp to baseline (v0 did). Send `ARM`.

### Board → host
| Line | Meaning |
|---|---|
| `T,<ms>,<state>,<pulse_id>,<tgtA>,<fA>,<dacA>,<tgtB>,<fB>,<dacB>,<tgtC>,<fC>,<dacC>,<tgtD>,<fD>,<dacD>` | Telemetry every `tel_div` loops. `f` = raw measured N, `dac` = 0–4095 (4095 = saturated). `pulse_id` 0 = none |
| `A,OK,<CMD>[,<detail>]` / `A,ERR,<CMD>,<reason>` | Ack |
| `E,<ms>,<kind>[,...]` | `PSTART,<id>` `PEND,<id>` `PABORT,<id>` `STATE,<name>` `FAULT,<ch>,<f>` `WD` |
| `I,...` / `P,<name>,<value>` | Info / parameter |

Telemetry is dropped (counted in `tx_drops`) rather than blocking the control loop when the USB buffer is full.

### Parameters (`SET`/`GET`)
Defaults = v0 firmware. † only settable when DISARMED.
| Name | Default | Range | Meaning |
|---|---|---|---|
| `loop_ms`† | 10 | 1–50 | Control period (fixed-rate; v0 was ~10 ms + overhead) |
| `kp_track` `kd_track` | 0.24, 3.5 | 0–100 | PD gains outside pulses |
| `kp_pulse` `kd_pulse` | 0.24, 3.5 | 0–100 | PD gains during a pulse. `kp = kd = 0` → open-loop |
| `kff` | 7.5 | 0–20 | Feedforward multiplier (Stanford guide: 1) |
| `rc` | 0.01905 | 0.001–0.2 | Drum radius, m |
| `kt` | 0.1524 | 0.001–10 | Torque constant |
| `i_full` | 30 | 1–100 | Current at DAC full scale (ESCON AnIn2 scaling) |
| `f_full` | 200 | 1–1000 | Force at ADC full scale |
| `baseline_n` | 5 | 0–30 | Tracking force |
| `fmax_n` | 200 | 0–200 | Target clamp (hard ceiling 200) |
| `fault_n` `fault_ms` | 195, 20 | 0–200, 1–1000 | Measured ≥ `fault_n` for `fault_ms` → abort pulse, FAULT (0 = off) |
| `filter_hz` | 0 | 0 or < 500/`loop_ms` | 2nd-order Butterworth on measured force (0 = off, v0) |
| `d_window` | 1 | 1–8 | D term over m samples: `(f - f[i-m]) / (m*loop_ms)` (Stanford: 3) |
| `arm_ms` | 2000 | 0–10000 | Arm ramp |
| `pulse_max_ms` | 1000 | 1–5000 | Longest allowed `dur` |
| `tel_div` | 1 | 0–1000 | Telemetry every n loops (0 = off) |
| `wd_ms` | 0 | 0–60000 | No line for this long → abort pulse, `E,WD` (0 = off) |
| `ch_A`..`ch_D`† | 1,1,1,0 | 0/1 | Channel enabled (default D off: it was out of service; `set ch_D 1` to use it) |
| `gain_A`..`gain_D`, `offset_A`..`offset_D` | 1, 0 | 0.5–2, −20–20 | Per-sensor calibration: `f = raw/1023*f_full*gain + offset` |

Control law (per enabled channel, every loop), unchanged from v0 with defaults:
```
ff    = filter(f)                       # identity when filter_hz = 0
d     = (ff - ff[i-m]) / (m*loop_ms)
ides  = kp*(tgt - ff) - kd*d + kff*tgt*rc/kt
dac   = clamp(ides/i_full, 0, 1) * 4095
```
