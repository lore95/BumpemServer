# bumpem server API

The contract between the bumpem server and every client (the web UI in `BumpemUI`, MATLAB, scripts,
future apps). Clients use only this API, never the Python internals (DECISIONS D10).

**Version:** 1.0-draft. Server 0.6.0 (2026-11-05, study runner): `board` and `host` endpoints implemented in `bumpem/server.py` (tests `tests/test_server.py`, `tests/test_geometry.py`, simulator). `planned` endpoints not implemented. Breaking changes bump the major
version and the path prefix (`/api/v1` → `/api/v2`). Additions do not.

**Status tags:** `board` = maps directly onto protocol v1 (`docs/PROTOCOL.md`), **implemented**. Interactive test page: `http://127.0.0.1:8000/docs`.
`host` = computed by the server, then sent as protocol v1 commands, **implemented**.
`planned` = schema is a proposal, not implemented.

## Basics
- Server: `bumpem serve`, listens on `http://127.0.0.1:8000` (this PC only). **No authentication** (D22): a `--host` other computers can reach is refused unless `--allow-network` is given.
- UI: the same server serves the browser UI (`../BumpemUI/web`) at **`http://127.0.0.1:8000/ui/`**; `/` redirects there. Other folder: `bumpem serve --ui PATH`. Same origin, so the UI needs no cross-origin setup. UI files are sent with `Cache-Control: no-cache` (the browser re-checks them on every load, so an update shows at once).
- One server per PC. The server alone opens the Teensy's serial port (or the simulator).
- JSON everywhere. Units: force N, time ms, angle degrees.
- Angle (Vicon Forward/Left/Up axes, counter-clockwise seen from above): **0 = front, +90 = left, −90 = right, 180 = back**. Any value is accepted and normalised to (−180, 180]. The angle is the direction the subject is pulled.
- Modules: A +90 (left), B 0 (front), C −90 (right), D 180 (back). A module is available when its channel is on (`ch_A`…`ch_D` = 1). **On connect the server sets the channels to the mounted modules** (`bumpem serve --modules ABCD`, default `ABCD` since 2026-11-05, was `ACD`; `--modules ""` keeps the firmware's power-up defaults A, B, C on, D off). Channels only change while DISARMED: if the board is armed (or in ESTOP) at connect, the server sets them as soon as it next reports DISARMED. `PATCH /params` can still change them. All four towers driven since 2026-11-03 (2026-10-02 … 11-02: A, C, D only, B's driver was broken) → every direction reachable.
- Pulse terms follow `docs/knowledge/perturbation_definitions.md`: amplitude is relative to baseline; duration runs start → end, ramps included.

## Errors
HTTP 4xx/5xx with:
```json
{"error": {"code": "board_rejected", "message": "exceeds fmax_n"}}
```
| code | HTTP | meaning |
|---|---|---|
| `invalid` | 422 | request failed validation before reaching the board |
| `board_rejected` | 409 | board answered `A,ERR` (message = board reason) |
| `not_connected` | 409 | no board or simulator connected |
| `board_timeout` | 504 | no reply from the board |
| `board_lost` | 503 | serial link gone (USB unplugged or Teensy reset): replug, then `POST /disconnect` + `POST /connect` |
| `wrong_mode` | 409 | endpoint belongs to the other server mode (testing / production) |
| `not_found` | 404 | nothing to return (e.g. no finished recording) |

## Endpoints

### Connection
| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/info` | | `{"server": "0.5.0", "api": "1.0", "mode": "production" \| "testing", "port": "sim", "board": {...INFO fields} or null, "reliable_n": 50}` | board |
| GET | `/api/v1/ports` | | `["/dev/tty.usbmodem123", ...]` | board |
| POST | `/api/v1/connect` | `{"port": "COM7"}` or `{"port": "sim"}` | `info` | board |
| POST | `/api/v1/disconnect` | | `{}` | board |

#### Automatic connection (`host`, D49)
`bumpem serve --board COM3 --vicon 192.168.1.60:801` makes them the **targets**: the server connects at startup and, whenever a target is not connected (failed, or lost: no board telemetry for 2 s, Vicon link ended or no frame for 2 s), retries every 5 s. Startup never fails because of them. `POST /connect` / `POST /vicon/connect` set a new target; `POST /disconnect` / `POST /vicon/disconnect` stop the retries until the next connect. A lost board stops the recording and a running study block (`stopped`).

### Clocks and sync (`host`, D49)
The station PC's clock is the reference: `pc_s` = seconds since the server started (monotonic). The server maps the board clock (`t_ms`) and the Vicon frame clock (frame / rate) onto it, continuously: per 1 s of device time the least-delayed arrival is kept, a straight line through the last 60 s of those gives offset and drift (`pc_s = a + b · device_s`); jitter = spread of those points around the line. Restarts (device clock jumps back) start a new fit.

| Method | Path | Returns |
|---|---|---|
| GET | `/api/v1/sync` | below |

```json
{"pc_s": 812.403, "wall": "2026-11-05T15:02:11.123+01:00",
 "board": {"target": "COM3", "connected": true, "message": null,
           "clock": {"ok": true, "drift_ppm": 18.2, "jitter_ms": 0.4, "late_ms": 0.9, "span_s": 60.0, "age_ms": 7}},
 "vicon": {"target": "192.168.1.60:801", "connected": true, "message": null,
           "clock": {"ok": true, "drift_ppm": -3.1, "jitter_ms": 0.8, "late_ms": 2.5, "span_s": 60.0, "age_ms": 9, "lost_frames": 0}},
 "in_sync": true, "problems": []}
```
- `message`: why a target is not connected (last error, or how it was lost), else null. `clock` null until 3 s of data. `late_ms`: 95th percentile of how much later than the fitted line samples arrive (transport jitter). `age_ms`: since the last sample. `lost_frames`: Vicon frames missing in the last 60 s.
- `in_sync`: both clocks `ok`: span ≥ 5 s, jitter ≤ 2 ms (board) / 5 ms (Vicon), age ≤ 200 ms, no Vicon frame lost in the last 10 s. `problems`: the reasons when not.
- **Handshake:** `POST /study/start` runs this check first and answers 409 `board_rejected` with the `problems` when not in sync; the result is written to the events file (`SYNC` row, the object above). The study's gait-phase delay uses the Vicon mapping (time since the touch-down sample on the PC clock).

### Board state and parameters
| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/status` | | `{"state": "ARMED", "pulse_id": 0, "telemetry": {...last}}` | board |
| GET | `/api/v1/params` | | `{"kp_track": 0.24, ...}` (all protocol v1 parameters) | board |
| PATCH | `/api/v1/params` | `{"baseline_n": 5, "kff": 7.5}` | updated params | board |

`PATCH` applies keys one by one and stops at the first rejection; the error names the key.

### Saved settings (`host`)
Board parameters live in the Teensy's RAM: a replug resets them to the firmware defaults. The server keeps one JSON file
(`bumpem serve --settings PATH`, default `BumpemServer/settings.json`, not in git; `--settings ""` = off) and writes its
parameters to the board **at every connect**, after the channels. If the board is not DISARMED or in ESTOP at connect
(server restarted while armed), nothing changes until it next reports DISARMED.
**Board restart:** when the board's uptime (`t_ms` in telemetry) jumps back by more than 1 s while connected (Teensy
reset, brown-out), the board is on firmware defaults again: the server re-sends the channels, its watchdog and the saved
file, then sends the stream event `RESTART` (also written to a running recording's events file).

| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/settings` | | `{"file": "…/settings.json" or null, "saved": "2026-10-12T14:03:00" or null, "params": {...} or null, "applied": true, "pending": false, "message": null}` | host |
| POST | `/api/v1/settings` | | saves the board's **current** parameters to the file → same object | host |
| DELETE | `/api/v1/settings` | | removes the file (the board keeps its current values) → same object | host |

- Not saved, not applied: `ch_A`…`ch_D` (owned by `--modules`), `wd_ms` (owned by the server), `loop_ms`, `tel_div` (timing).
- `applied`: the file was written to the board on this connection (and after its last restart). `pending`: waiting for DISARMED. `message`: why a value was refused, if any (the rest is still applied).
- `RESTART` args: `settings applied`, `settings pending` (board not DISARMED yet), `settings partly applied`, `no saved settings`.
- Clients compare `GET /params` with `params` here and warn when they differ (board running other values than the saved ones).
- Sensor zero offsets (`offset_*`) are saved like every other parameter: re-zero and save again when a sensor or its wiring changes.
- Both modes. In testing mode a test pull still restores the parameters it changed.

### Recording (`host`)
Writes the board's telemetry at the **full board rate** (not thinned like the stream) to CSV files in `bumpem serve --log-dir PATH` (default `BumpemServer/Logs/`, not in git), and the Vicon force plates when Vicon is connected (also if it connects during the recording).

| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/log` | | `{"recording": false, "file": null, "events_file": null, "vicon_file": null, "rows": 0, "vicon_rows": 0, "duration_s": 0}` | host |
| POST | `/api/v1/log/start` | `{"label": "closedloop_A"}` (optional; letters, digits, `_`, `-`, max 40) | same object, `recording: true` | host |
| POST | `/api/v1/log/stop` | | same object with the final `rows` and `duration_s`; `recording: false` | host |
| GET | `/api/v1/log/file?kind=force\|events\|vicon` | | the last **finished** recording's CSV as a download (`text/csv`, attachment, same file name). 404 `not_found` if none since the server started; 409 `board_rejected` while recording | host |

- `force_<YYYYMMDD_HHMMSS>[_label].csv`: `time_ms,state,pulse_id,target_A,measured_A,dac_A,…,dac_D,pc_s` (one row per telemetry line; `time_ms` = board clock, `pc_s` = the same moment on the PC clock, empty until the clock fit exists).
- `events_<same>.csv`: `time_ms,kind,args,pc_s`: first row `CLOCK` (`{"pc_s": …, "wall": "…"}`: ties `pc_s` to the date and time), then `PARAMS` (all board parameters at the start, as JSON), then board events (`STATE`, `PSTART`, `PEND`, `FAULT`, `WD`, …) and one `CMD` row per pulse the server sent (`args` = the request as JSON: angle, amplitude, amps per module, pulse id), stamped with the latest board time.
- `vicon_<same>.csv` ends with `latency_ms`: Vicon's own latency estimate for that frame (SDK `GetLatencyTotal`, camera → DataStream; empty from the simulator).
- **Delay report** (D51): `GET /api/v1/log/delay` analyses the last finished recording (409 while recording, 404 none) and returns `{"file": "…/delay_<stem>.txt", "text": "…", "pulses": [...], "recommended_latency_ms": 38.5 or null}`; `?format=text` returns the text only (for a browser tab). The text file is written next to the CSVs. Per pulse: `command_ms` (server sent → board started it, minus the requested delay: USB + firmware), `rise_ms` (board start → rope force over baseline + max(2 SD, 2 N) for 3 samples, the lab's start definition), `lag_ms` (measured force reaches half the amplitude after the target does), `ratio` (plateau measured / target amplitude: pull strength). Study pulls also: `timing_error_ms` = rope force start − intended start (touch-down on the PC clock − Vicon latency + phase); `recommended_latency_ms` = the System delay used + the median timing error.
- Start while recording → 409 `board_rejected` ("already recording"). Stop while idle → the idle object. Needs a connected board (409 `not_connected`); recording stops by itself at disconnect.
- Both modes.

### Error log (`host`, D51)
Everything that went wrong, in one file per day for Claude: `<log-dir>/errors_<YYYYMMDD>.jsonl`, one JSON object per line: `{"wall": "…", "pc_s": 812.4, "level": "error" | "warn" | "info", "source": "api" | "board" | "vicon" | "study" | "server" | "client", "message": "…", …context}`. Written: API answers ≥ 400 (warn; 5xx error) with method, path and the message; unhandled server exceptions (with traceback); board reader errors, FAULT / ESTOP / WD events; connections failed / lost (board, Vicon); study blocks stopped or ended early, refused pulses, gait-pattern messages; browser page errors (sent by the pages).

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/v1/errors?limit=200` | | the latest entries (newest last) |
| POST | `/api/v1/errors` | `{"page": "BumpemActivation.html", "message": "…", "stack": "…"}` | `{}` (a page's own error; source `client`) |
| GET | `/api/v1/errors/file?day=YYYYMMDD` | | that day's file as a download (default today); 404 when none |

### Vicon force plates (`host`)
The GRAIL belts' force plates, read from Vicon Nexus over Ethernet (DataStream SDK, `vicon_dssdk`; device data only, no markers: DECISIONS D31). Independent of the board connection.
`bumpem serve --vicon HOST:PORT` connects at startup (e.g. `192.168.1.60:801`, `127.0.0.1:801` on the Nexus PC; `sim` = two simulated plates, running gait; `replay:<name>` = a participant's recorded plates, `replays/<name>.csv`, played back in real time and looped: D54). The UI can also connect with its own address.
- Replays: `python scripts/make_replay.py <vicon_*.csv> <name> --from S --to S` cuts a stretch of a recording (seconds from its start) into `replays/<name>.csv` (`t_s,frame,sub,Fz_<plate>…`, no names or clocks). `replays/` is not in git (participant data). `rate_hz` = the recording's frame rate; `latency_ms` none; frame numbers keep counting across the loop; at the loop point the gait jumps once.

| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/vicon` | | `{"connected": true, "host": "192.168.1.60:801", "default_host": "…" or null, "rate_hz": 100, "plates": ["Left", "Right"], "message": null}` | host |
| POST | `/api/v1/vicon/connect` | `{"host": "192.168.1.60:801"}`, `{"host": "sim"}` or `{"host": "replay:running_3.33ms"}` | same object. A replay that does not exist → 422 `invalid` (names the ones there). Waits up to 5 s for the first frame: no reply → 504 `board_timeout`; SDK missing, bad address or no plate with an `Fz` output → 422 `invalid` | host |
| POST | `/api/v1/vicon/disconnect` | | same object (a running recording's Vicon file ends there) | host |

- `plates`: Vicon device names that have an `Fz` output (Nexus names them). `message`: why the reader stopped (link lost), else null.
- Recorded with the board (see Recording): `vicon_<same stem>.csv`: `host_s,frame,sub,board_ms,Fz_<plate>,…,pc_s`, one row per force-plate **subsample** (full rate, e.g. 1000 Hz). `host_s` = arrival on the server clock (s since the server started), `pc_s` = the subsample's moment on the PC clock from the Vicon clock fit (empty until it exists; see Clocks and sync), `board_ms` = the latest board telemetry time when the frame arrived (for lining up with `force_*.csv`), `Fz` in N = **vertical ground reaction force, positive up** (standing ≈ +body weight): the server negates Vicon's `GetGlobalForceVector` Z (lab axes, force exerted **on** the plate, which reads negative). Plate names: Nexus device names, else `Plate <id>`.
- Both modes.

### Modes
`bumpem serve --testing` or `--production` (default). The UI at `/ui/` follows the mode (production page / testing page), and the server refuses what belongs to the other mode with 409 `wrong_mode`:

| Mode | Allowed | Refused |
|---|---|---|
| production | everything except `/test/pull` | `POST /test/pull` |
| testing | connection, status, params, settings, recording, `POST /test/pull`, `abort`, `release`, `estop`, `clear`, stream | `POST /arm`, `POST /pulse`, `POST /perturbation` |

### Test pull (`host`, testing mode)
One pull on one motor, without leaving the system armed:
```json
POST /api/v1/test/pull
{"module": "C", "force_n": 5, "dur_ms": 400}
→ {"pulse_id": 3, "module": "C", "force_n": 5, "dur_ms": 400}
```
The server, in one call: saves the parameters → open loop (gains 0, `kff` 2), `baseline_n` 0, `fmax_n` = `force_n`, `arm_ms` 0, only `module` enabled → `ARM` (target 0 N, rope stays slack) → one `PULSE` (50 ms ramps, `force_n` ≤ 150, `dur_ms` 100–1000 incl. ramps) → `RELEASE 0` → restores the parameters. Starts only from DISARMED or ESTOP (else 409 `board_rejected`); one test pull at a time. Force is calculated from the motor current (open loop), not measured. `estop` works throughout.

### Actions
| Method | Path | Body | Status |
|---|---|---|---|
| POST | `/api/v1/arm` | | board |
| POST | `/api/v1/abort` | | board |
| POST | `/api/v1/release` | `{"ms": 1000}` | board |
| POST | `/api/v1/estop` | | board |
| POST | `/api/v1/clear` | | board |

`estop` is never queued behind another request. Only `release` and `estop` drop tension:
stop the treadmill first (`docs/knowledge/safety.md`).

### Pulses
Channel form (`board`): exactly one protocol v1 `PULSE`. The server assigns the id.
```json
POST /api/v1/pulse
{"amps": {"A": 65.71, "B": 65.71}, "delay_ms": 0, "rise_ms": 50, "dur_ms": 600, "fall_ms": 0}
→ {"pulse_id": 12, "warning": null}
```
Perturbation form (`host`): the server converts angle → channel amplitudes, then sends one `PULSE`.
```json
POST /api/v1/perturbation
{"angle_deg": 135, "amplitude_n": 20, "phase1_ms": 50, "dur_ms": 400, "phase2_ms": 50, "delay_ms": 0}
→ {"pulse_id": 13, "amps": {"A": 14.14, "D": 14.14}, "warning": null}
```
- **Reliable force** (D56): `reliable_n` (`/info`, 50 N until the steel shafts, `docs/tower-limits.md`) = the largest pull per rope the towers reach without slipping. Above it the pull is still sent (up to the board's Max force, 79 N = 75 N pull + 4 N rest since 2026-11-20) and the reply's `warning` says the force may not be reached; `null` otherwise. A study load lists every block above it in `warnings` (per rope, all four towers assumed on).
- `amplitude_n`: resultant force above baseline along `angle_deg`. `phase1_ms` / `phase2_ms`: ramp up / ramp down (acceleration phases one and two, `perturbation_definitions.md`); `dur_ms` start → end, ramps included; `delay_ms`: board-side delay before the start.
- Split: on a module's axis that module alone gets `amplitude_n`. Between two neighbouring modules (90° apart) the first gets `amplitude_n·cos(Δ)`, the second `amplitude_n·sin(Δ)`, Δ = angle past the first module. At 45° each gets `amplitude_n/√2`, the rule of the original firmware (`legacy/Arduino_Script.ino:82`). Assumes horizontal cables at right angles.
- An angle needing a module whose channel is off → 422 `invalid`, message names the module. Force limits stay on the board (`fmax_n` → 409 `board_rejected`).
- At baseline the cables do not cancel when a module is missing: with B not installed, the subject feels a constant pull of `baseline_n` towards D (back).

PTO (`planned`): adds `"pto": {"mode": "ms" | "stance_pct" | "cycle_pct", "value": 20}, "trigger": {"event": "FS", "side": "any"}` → waits for the next matching gait event, response adds `"scheduled": "same_fs" | "predicted_fs"`. `cycle_pct`: % of the gait cycle after the trigger foot strike (running: stance 0–40, float 40–55, swing 55–85, float 85–100, thesis Fig. 1); the server converts it with the measured stride time. The UI's gait-phase picker produces it.

| Method | Path | Returns | Status |
|---|---|---|---|
| GET | `/api/v1/geometry` | `{"convention": "...", "modules": {"A": {"angle_deg": 90, "enabled": true}, ...}, "reachable": [{"from_deg": 90, "to_deg": -90}]}` (arcs counter-clockwise from → to; `enabled`/`reachable` null when no board is connected) | host |

### Perturbation patterns (`host`, D50)
A pattern = a saved sequence of directions and step gaps, made once (BumpemUI `BumpemPattern.html`) and used by a block for **every participant**, so all get the same pulls in the same order at the same step counts. Stored as JSON files in `bumpem serve --patterns DIR` (default `BumpemServer/patterns/`; `update.bat` keeps them). A saved pattern never changes: the same name again → 409.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/v1/patterns` | | `[{"name": "lateral-12", "n": 12, "created": "…", "angles": [90, -90], "gap_min": 40, "gap_max": 60, "note": ""}]` (summary, newest first) |
| GET | `/api/v1/patterns/{name}` | | the pattern; 404 `not_found` |
| POST | `/api/v1/patterns` | pattern | the saved pattern (`created` set by the server); 409 `board_rejected` when the name exists; 422 `invalid` |

```json
{"name": "lateral-12", "note": "balanced, max 2 same in a row",
 "items": [{"angle_deg": 90, "gap_steps": 52}, {"angle_deg": -90, "gap_steps": 47}, ...],
 "rules": {"angles": [90, -90], "n": 12, "gap_min": 40, "gap_max": 60, "balanced": true, "max_run": 2, "seed": 1234}}
```
- `name`: letters, digits, `_`, `-`, max 40. `items`: 1–500; `angle_deg` API convention (normalised); `gap_steps` 1–1000 = steps (touch-downs, either foot) after the previous perturbation; item 1: after the block's warm-up. `rules`: how it was generated (kept, not used).

### Study (`host`, production mode)
One subject and a list of blocks (BumpemUI `BumpemSetUp.html`, run from `BumpemActivation.html`), run block by block: foot strikes per belt from the Vicon plates, a perturbation at a gait phase after a foot strike (DECISIONS D44). One study at a time; it lives until replaced or the server stops.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/v1/study` | | status (below); `"state": "none"` when no study is loaded |
| POST | `/api/v1/study` | protocol (below) | status + `"warnings": ["block 2: 60 N on one rope is above 50 N: …"]` (reliable force, below). Replaces the loaded study; 409 `board_rejected` while a block runs or the gait recording runs |
| DELETE | `/api/v1/study` | | status (`none`); 409 while a block runs |
| GET | `/api/v1/study/protocol` | | the loaded protocol as accepted (numbers as numbers, defaults filled in, `plates` resolved); 404 `not_found` when none |
| POST | `/api/v1/study/gait` | `{"duration_s": 20}` (5–120) | status (`gait`). Needs Vicon (409 `not_connected`) and the board ARMED (409 `board_rejected`: Arm first, so the recording holds it). Leaving ARMED during it cancels it. Records both plates, sets the contact thresholds from the swing noise, then stride and stance time per side → `ready`. Fewer than 5 strides on a side → back to the previous state with a `message` |
| POST | `/api/v1/study/start` | `{"latency_ms": 0}` (optional, 0–1000) | status (`running`). Starts the current block (after `block_done`: the next one), or resumes a `stopped` block where it was (warm-up and duration count again from the resume). Needs: board ARMED, a recording running (BumpemActivation starts one if needed), Vicon, a gait pattern recorded at this block's `speed_ms`, the clocks in sync, the board's `baseline_n` = the subject's `baseline_n` (when given), the block's force within `fmax_n − baseline_n`, its directions reachable with the enabled channels, and its perturbations fitting in `duration_s` at the measured cadence. Else 409 `board_rejected` with the reason (for the duration: the maximum number that fits) |
| POST | `/api/v1/study/stop` | | status (`stopped`): no further perturbations; a pulse already sent still runs. Does not release tension |
| POST | `/api/v1/study/export` | | session zip (below) → `{"file": "…/Logs/S014_KneeStudy_2026-11-19_1430.zip", "name": "S014_KneeStudy_2026-11-19_1430.zip", "files": ["…"], "recordings": 2}`. 409 `board_rejected` while recording (Stop rec first), a block runs or the gait pattern is being recorded; 404 `not_found` when no study is loaded |
| GET | `/api/v1/study/export` | | the last session zip as a download (`application/zip`); 404 when none since the server started |
| GET | `/api/v1/studies` | | saved sessions: the session zips in the log folder, newest first: `[{"name": "S014_KneeStudy_2026-11-19_1430.zip", "subject_id": "S014", "study_name": "KneeStudy", "loaded": "2026-11-19T14:30:05", "blocks": 3, "mode": "walking"}]` (zips without a readable `protocol.json` are left out) |
| GET | `/api/v1/studies/{name}/protocol` | | that zip's `protocol.json` (to start a new session from it: BumpemSetUp → Import saved study); 404 `not_found` |

Protocol (numbers as numbers; other keys are kept and written to the events file, not used). BumpemSetUp sends this form:
```json
{"subject": {"subject_id": "S014", "study_name": "KneeStudy", "mass_kg": 72.5, "height_cm": 178, "mode": "running", "baseline_n": 4},
 "blocks": [{"label": "Main 1", "speed_ms": 2.5, "duration_s": 300, "warmup_s": 60, "n_perturbations": 10,
             "pattern": "lateral-12", "trigger_side": "left", "gait_phase_pct": 30,
             "phase1_ms": 50, "dur_ms": 400, "phase2_ms": 50, "amplitude_mode": "percent_bw", "amplitude": 10}],
 "plates": {"left": "Left", "right": "Right"}}
```
- Subject: `subject_id` (letters, digits, `-`, `_`, max 40): the participant ID that points to the lab's master file, never a name; `study_name` (optional; letters, digits, spaces, `-`, `_`, max 40); `mass_kg` > 0 (≤ 300); `mode` `walking` (default) | `running`: sets the cadence assumed by BumpemSetUp's duration check and the plausibility check of the gait pattern (walking: stride 0.7–1.8 s, contact ≥ 0.35 s; running: stride 0.45–1.0 s, contact ≤ 0.4 s; outside → `message`, the pattern is still kept); `baseline_n` (0–50, optional): rope tension between pulls; BumpemActivation sets it on the board before Arm and Start checks it.
- Block: `speed_ms` > 0; `duration_s` (10–7200, optional): the block ends when all perturbations are done or this time has passed since its start, whichever first (`message` says which); `warmup_s` ≥ 0 (default 0): no perturbation and no step counted in the first seconds; `n_perturbations` 1–500.
- Directions and timing: **`pattern`** (name of a saved pattern, D50): perturbation k gets the pattern's item k: its angle, `gap_steps` after the previous one (the first after the warm-up); `n_perturbations` ≤ the pattern's length (the first n are used). The server reads the pattern at load; `GET /study/protocol` shows it under `pattern_items`. Without `pattern` (scripts, tests): `directions_deg` (≥ 1 angle; taken in turn, shuffled when several) and `timing_mode` `random` (`interval_min_steps` ≤ `interval_max_steps`, 1–1000, a new random count after each perturbation) or `predefined` (`schedule_steps`, increasing step numbers from the block start, one per perturbation).
- Force: `amplitude_mode` `newton` (`amplitude` in N) or `percent_bw` (`amplitude` in % body weight: amplitude_n = amplitude / 100 × mass_kg × 9.81); legacy `intensity_pct_bw` = `percent_bw`. Split over the modules as in Perturbation form. `phase1_ms` (ramp up), `dur_ms` (start → end, ramps included), `phase2_ms` (ramp down) as Perturbation form.
- Phase: `trigger_side` `left` | `right` | `any` (the leg whose touch-down starts the phase); `gait_phase_pct` 0–<100 of `gait_phase_of` `cycle` (stride, touch-down → touch-down; **default since D50**) or `stance` (contact time, touch-down → foot-off).
- Steps = touch-downs on either belt, counted while the block runs after the warm-up. A perturbation is due when its gap is reached (pattern / random: steps since the last perturbation; predefined: steps since the block started), and is sent at the **next touch-down of `trigger_side`**. Board-side delay = phase − age of that touch-down sample − `latency_ms`, phase = `gait_phase_pct` / 100 × that side's stance (or stride) time. When that is below 0 the pull aims at the same phase of the side's **next** contact (+ one stride; as `AAPertAnalogTrig_SLAP.m`). `latency_ms` = plates → board → rope delay, from Start (default 0: to be measured, TODO board ↔ Vicon timing).
- Contacts (`bumpem/gait.py` `ContactDetector`, from `scripts/Pertubation_analog/AAPertAnalogTrig_SLAP.m`): per plate, touch-down when Fz rises above `td_n`, foot-off when it falls below `fo_n` (hysteresis). Defaults 100 / 25 N (the script). The gait pattern lowers them to the plate's swing noise: `td_n` = swing mean + max(6 × sd, 20 N), `fo_n` = swing mean + max(3 × sd, 10 N), never above the defaults; kept only if they find the same touch-downs as the defaults (± 1 per side), else the defaults stay and `message` says why.
- Sample time: Vicon frame number / frame rate + subsample index (steady 1 ms at 1000 Hz), not the arrival time on the PC. `gait.rate_hz` = plate samples per second during the gait pattern. `plates` names the plate of each belt (`GET /vicon` `plates`); default: plates named left/right, else the first plate = left.
- A gait pattern being recorded is cancelled (`message` = why) and a block stops (`stopped`, `message` = why) when the board leaves ARMED (STOP, FAULT, Release), Vicon is lost or a pulse is refused. After the last perturbation of a block: `block_done`; after the last block: `finished`.
- Events file of a running recording: `STUDY` (load, block start / stop / done, gait pattern), `FS` (touch-down, `{"side": "left", "step": 12}`), `FO` (foot-off), `PERT` (pulse id, block, index, angle, amplitude, side, delay, `next_contact` when it aims at the following contact, `td_pc` = the touch-down sample on the PC clock, `phase_ms`, `age_ms`, `latency_ms`: for the delay report).

Session zip (D53): one zip per loaded study, in the log folder, named `<subject_id>_<study_name>_<YYYY-MM-DD>_<HHMM>.zip` (date and time = when the study was loaded; `study_name` left out when empty; `_2`, `_3` … if the name exists). Inside, one folder of the same name with: every recording made while the study was loaded (`force_`, `events_`, `vicon_` CSVs; a recording already running at load counts too), a delay report `delay_<stem>.txt` per recording (written now if missing), `protocol.json` (as accepted), `study.json` (final status with the gait patterns), `params.json` (the board's parameters at export, if connected), `settings.json` (saved defaults, if any) and the error logs `errors_<day>.jsonl` of the session's days. Exporting again (e.g. after another recording) makes a new zip with the same rule. BumpemActivation exports by itself when the last recording of a finished study stops.

Status:
```json
{"state": "running", "message": null, "subject_id": "S014", "block": 1, "blocks": 4, "label": "Familiarisation",
 "speed_ms": 2.5, "amplitude_n": 71.1, "done": 3, "total": 10, "steps": 212, "next_in_steps": 41, "ends_in_s": 184,
 "next_block": 1, "next_speed_ms": 2.5, "gait_ok": true,
 "latency_ms": 0,
 "gait": {"speed_ms": 2.5, "rate_hz": 1000, "until_s": null,
          "left": {"stride_ms": 721, "sd_ms": 9, "n": 14, "stance_ms": 251, "stance_sd_ms": 6, "td_n": 31.2, "fo_n": 15.6, "noise_sd_n": 1.9},
          "right": {...}},
 "plates": {"left": "Left", "right": "Right"}}
```
`state`: `none` | `loaded` (no gait pattern yet) | `gait` (recording it; `gait.until_s` = seconds left) | `ready` | `running` | `stopped` | `block_done` | `finished`. `block` is 1-based. `next_in_steps`: steps until a perturbation is due (then it waits for the trigger foot), null when not running. `ends_in_s`: seconds left of `duration_s` while running, else null. `next_block` / `next_speed_ms`: the block Start would run and its speed; `gait_ok`: a gait pattern exists at that speed (else Start answers 409).

## Live stream (WebSocket)
`ws://127.0.0.1:8000/api/v1/stream?telemetry_hz=30`

Server → client, one JSON object per message:
```json
{"type": "telemetry", "t_ms": 1234, "state": "ARMED", "pulse_id": 0,
 "target": {"A": 5.0, ...}, "measured": {"A": 5.1, ...}, "dac": {"A": 1846, ...}}
{"type": "event", "t_ms": 1300, "kind": "PSTART", "args": ["12"]}
{"type": "event", "t_ms": 40, "kind": "RESTART", "args": ["settings applied"]}   // from the server, see "Saved settings"
{"type": "vicon", "host_s": 12.345, "frame": 5021, "fz": {"Left": 812.4, "Right": 3.1}}   // mean over the frame's subsamples
{"type": "gait", "t_s": 12.345, "event": "FS", "side": "left", "step": 212}  // study loaded: every valid foot strike
{"type": "study", "state": "running", ...}                                      // study status (GET /study) on every change
```
Telemetry and `vicon` messages are each thinned to `telemetry_hz` for display. In thinned telemetry, `measured` is the
**median of the board samples since the previous message** (per channel; removes single-sample spikes); `target`,
`dac`, `state` are the latest sample's. Logs always keep the full rate, raw.

Client → server: `{"type": "estop"}` (same as `POST /estop`, for the lowest latency from a UI).

## Safety behavior of the server
- While connected to hardware, the server sets the board watchdog (`wd_ms`) and pings it. If the server dies, the board aborts any pending pulse and holds baseline. The `wd_ms` value is set on the bench.
- Clients disconnecting (browser tab closed) changes nothing on the board.
- `bumpem estop` from a terminal goes through the server while one is running, because the server holds the port.

## Examples
```sh
curl -X POST localhost:8000/api/v1/connect -H 'content-type: application/json' -d '{"port":"sim"}'
curl -X POST localhost:8000/api/v1/arm
curl -X POST localhost:8000/api/v1/pulse -H 'content-type: application/json' \
     -d '{"amps":{"A":95},"rise_ms":50,"dur_ms":600,"fall_ms":0}'
```
```matlab
opts = weboptions('MediaType', 'application/json');
webwrite('http://127.0.0.1:8000/api/v1/pulse', struct('amps', struct('A', 95), ...
         'rise_ms', 50, 'dur_ms', 600, 'fall_ms', 0), opts);
```
