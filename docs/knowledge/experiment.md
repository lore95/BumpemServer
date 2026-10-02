# Experiment protocol (thesis pilot)

Source: thesis §4.1–4.3; manual §6.1; `legacy/MATLAB_script.m:10-17`.

- Speed 3.3 m/s; warm-up 5 min at 2.7 m/s; 3 min rest between trials.
- Per trial: 25 perturbations = 5 blocks × shuffled `["a","b","c","ab","bc"]`.
- Each perturbation at a random valid FS count in [50, 75] since the last one.
- 100 N target, baseline 5 N.
- 2 trials per participant.

## Procedure order (manual §6.1)
Power on → ESCON check → flash Teensy (auto-ramps to baseline) → verify baseline on all modules → treadmill (D-Flow) to speed → start detection script → monitor → script ends after last perturbation → treadmill stop → then stop control.

## Outputs (MATLAB)
- `Logs/Log_event_data_<ts>.csv`: `time_s,frame,subIndex,Fz_total,event`
- `Logs/Perturbation_log_<ts>.csv`: `perturbation_index,fs_number,time_s,frame,subIndex,command`
- Teensy force telemetry is **not** captured by the MATLAB script.
