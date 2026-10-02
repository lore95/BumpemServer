# Gait event detection (as implemented)

Source: `legacy/MATLAB_script.m`, thesis §4.3 + Appendix.

## Vicon
- Host `192.168.10.1:801` (`:3`). .NET DataStream SDK. StreamMode ClientPull. Axis mapping Forward/Left/Up.
- Device data: force plates 0 and 1 (GRAIL belts), all subsamples per frame.
- Signal: `Fz_total = Fz_plate0 + Fz_plate1` (sum, so any foot).

## Parameters
| Name | Value | Line | Note |
|---|---|---|---|
| `Fz_th` | 250 N | 5 | FS and TO threshold |
| `minGaitCycle` | 0.30 s | 6 | comment says 400 ms (stale) |
| `minStanceTime` | 0.15 s | 7 | comment says 200 ms (stale) |
| min time since TO | 0.1 s | 89 | hardcoded ("minSwingTime" in thesis) |

## Logic
- **FS**: not in stance, |Fz_prev| < th, |Fz| ≥ th, t − lastFS ≥ minGaitCycle, t − lastTO > 0.1 → valid FS; else `FS_NOISE`.
- **TO**: in stance, |Fz_prev| ≥ th, |Fz| < th, stance ≥ minStanceTime → valid TO; else `TO_NOISE` (stays in stance).
- Trigger on valid FS when `fsSinceLast >= fsTarget`; `fsTarget = randi([50 75])` after each perturbation.

Python port: `bumpem/gait.py` (must match this exactly; test against MATLAB logs).

## Timing (thesis Table 5, 3.3 m/s)
Stance 246.7 / 253.8 ms; stride 660 / 789 ms; onset delay 36.0 ± 4.9 ms (~14–15 % stance).
