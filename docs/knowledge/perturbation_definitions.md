# Perturbation definitions (lab standard)

Source: provided by the project lead, 2026-09-29. Written for treadmill belt-velocity perturbations.
All quantities are measured from the recorded signal, not commanded.

## Cable-force mapping (Bump'em, docs/DECISIONS.md D7)
Velocity → force per module (and resultant along the commanded angle). Distance → impulse ∫(F − F_baseline) dt [N·s].
- **Baseline force:** mean measured force over the **first 3 s of the trial** (fixed reference, not rolling). ± 2 SD thresholds use the SD of that window.
- **Balance recovery** (when the next random interval starts) is **not** defined here: it comes from the lab's existing algorithm (gait prediction + whole-body angular momentum). The host calls it through a plug-in interface; see STATUS.md.

| Term | Definition |
|---|---|
| Baseline velocity | Mean belt velocity during a pre-perturbation reference period (e.g., first 3 s). |
| Perturbation temporal offset (PTO) | Time from a reference event (e.g., heel strike) to perturbation start, in seconds or % of stance. |
| Perturbation start | When belt velocity leaves baseline ± 2 SD. |
| Acceleration phase one duration | Time from perturbation start to peak velocity. |
| Peak velocity | When belt acceleration returns to zero and velocity is within ± 2 SD of its maximum. |
| Perturbation duration | Time from perturbation start to end. |
| Perturbation end | Same threshold as start (baseline ± 2 SD), found by analyzing the trial in reverse. |
| Acceleration phase two duration | Time from the end of the perturbation-velocity plateau to perturbation end. The plateau end is found in reverse, where acceleration is zero and velocity is within perturbation velocity ± 2 SD of baseline. |
| Perturbation velocity | Mean belt velocity during the plateau. For triangular perturbations it is roughly the peak velocity. |
| Perturbation distance | Integral of belt velocity during the perturbation minus the integral of baseline velocity over the same time. Positive for slips, negative for trips. |
| Velocity amplitude | Perturbation velocity minus baseline velocity. |
