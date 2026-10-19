# Gait event detection (as implemented)

Source: `legacy/MATLAB_script.m`, thesis §4.3 + Appendix.

## Vicon
- Host `192.168.10.1:801` (`:3`). .NET DataStream SDK. StreamMode ClientPull. Axis mapping Forward/Left/Up.
- Device data: force plates 0 and 1 (GRAIL belts), all subsamples per frame.
- Signal: `Fz_total = Fz_plate0 + Fz_plate1` (sum, so any foot).

## Lab system (project lead, 2026-10-19)
- Vicon cameras + **GRAIL treadmill, split belt: independent left and right belts, each with its own force plate**, platform tilts on 2 axes. **All data (markers, force plates) is read through Vicon** (DataStream).
- Consequence: FS / TO can be detected **per foot** (one plate per belt) instead of on the sum. The sum (legacy) only works for running: in walking one foot is always down, so the sum never falls below `Fz_th` and TO is never seen. Per-belt detection gives left/right events for walking and running.
- Access: Nexus serves DataStream on port 801 while it runs in Live mode; clients use the free Vicon DataStream SDK (Python package `vicon_dssdk`). First check: `scripts/vicon_probe.py` (read-only, lists devices, prints Fz per plate). Nexus shows **192.168.10.1** once opened (project lead, 2026-10-19) = the legacy MATLAB host. Still to confirm: port 801 LISTENING while live, and whether that address is the camera network (then the server runs on the Nexus PC, or the administrator says which port to use).
- Still to check: which Vicon device index is the left belt (Nexus device names); crossover steps (a foot landing on the other belt) mislabel the side; platform tilt: use each plate's own Fz (normal to the belt), as legacy did.
- The towers stand on the floor, the platform moves: when it tilts, rope angle and length change. Test tilting with the towers before using it in a protocol.

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
