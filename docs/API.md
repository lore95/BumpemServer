# bumpem server API

The contract between the bumpem server and every client (the web UI in `BumpemUI`, MATLAB, scripts,
future apps). Clients use only this API, never the Python internals (DECISIONS D10).

**Version:** 1.0-draft. Server 0.4.0 (2026-10-12): `board` and `host` endpoints implemented in `bumpem/server.py` (tests `tests/test_server.py`, `tests/test_geometry.py`, simulator). `planned` endpoints not implemented. Breaking changes bump the major
version and the path prefix (`/api/v1` → `/api/v2`). Additions do not.

**Status tags:** `board` = maps directly onto protocol v1 (`docs/PROTOCOL.md`), **implemented**. Interactive test page: `http://127.0.0.1:8000/docs`.
`host` = computed by the server, then sent as protocol v1 commands, **implemented**.
`planned` = needs gait events / trials (PTO, scheduling); schema is a proposal.

## Basics
- Server: `bumpem serve`, listens on `http://127.0.0.1:8000` (this PC only). Other hosts only if started with `--host`.
- UI: the same server serves the browser UI (`../BumpemUI/web`) at **`http://127.0.0.1:8000/ui/`**; `/` redirects there. Other folder: `bumpem serve --ui PATH`. Same origin, so the UI needs no cross-origin setup.
- One server per PC. The server alone opens the Teensy's serial port (or the simulator).
- JSON everywhere. Units: force N, time ms, angle degrees.
- Angle (Vicon Forward/Left/Up axes, counter-clockwise seen from above): **0 = front, +90 = left, −90 = right, 180 = back**. Any value is accepted and normalised to (−180, 180]. The angle is the direction the subject is pulled.
- Modules: A +90 (left), B 0 (front), C −90 (right), D 180 (back). A module is available when its channel is on (`ch_A`…`ch_D` = 1). **On connect the server sets the channels to the mounted modules** (`bumpem serve --modules ACD`, default `ACD`; `--modules ""` keeps the firmware's power-up defaults A, B, C on, D off). Channels only change while DISARMED: if the board is armed (or in ESTOP) at connect, the server sets them as soon as it next reports DISARMED. `PATCH /params` can still change them. Setup 2026-10-02: A, C, D mounted, B not installed → reachable +90 … 180 … −90 (left, back, right and the back diagonals).
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

## Endpoints

### Connection
| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/info` | | `{"server": "0.4.0", "api": "1.0", "mode": "production" \| "testing", "port": "sim", "board": {...INFO fields} or null}` | board |
| GET | `/api/v1/ports` | | `["/dev/tty.usbmodem123", ...]` | board |
| POST | `/api/v1/connect` | `{"port": "COM7"}` or `{"port": "sim"}` | `info` | board |
| POST | `/api/v1/disconnect` | | `{}` | board |

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

| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/settings` | | `{"file": "…/settings.json" or null, "saved": "2026-10-12T14:03:00" or null, "params": {...} or null, "applied": true, "pending": false, "message": null}` | host |
| POST | `/api/v1/settings` | | saves the board's **current** parameters to the file → same object | host |
| DELETE | `/api/v1/settings` | | removes the file (the board keeps its current values) → same object | host |

- Not saved, not applied: `ch_A`…`ch_D` (owned by `--modules`), `wd_ms` (owned by the server), `loop_ms`, `tel_div` (timing).
- `applied`: the file was written to the board on this connection. `pending`: waiting for DISARMED. `message`: why a value was refused, if any (the rest is still applied).
- Sensor zero offsets (`offset_*`) are saved like every other parameter: re-zero and save again when a sensor or its wiring changes.
- Both modes. In testing mode a test pull still restores the parameters it changed.

### Recording (`host`)
Writes the board's telemetry at the **full board rate** (not thinned like the stream) to CSV files in `bumpem serve --log-dir PATH` (default `BumpemServer/Logs/`, not in git).

| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/log` | | `{"recording": false, "file": null, "events_file": null, "rows": 0, "duration_s": 0}` | host |
| POST | `/api/v1/log/start` | `{"label": "closedloop_A"}` (optional; letters, digits, `_`, `-`, max 40) | same object, `recording: true` | host |
| POST | `/api/v1/log/stop` | | same object with the final `rows` and `duration_s`; `recording: false` | host |

- `force_<YYYYMMDD_HHMMSS>[_label].csv`: `time_ms,state,pulse_id,target_A,measured_A,dac_A,…,dac_D` (one row per telemetry line; `time_ms` = board clock).
- `events_<same>.csv`: `time_ms,kind,args`: board events (`STATE`, `PSTART`, `PEND`, `FAULT`, `WD`, …) and one `CMD` row per pulse the server sent (`args` = the request as JSON: angle, amplitude, amps per module, pulse id), stamped with the latest board time.
- Start while recording → 409 `board_rejected` ("already recording"). Stop while idle → the idle object. Needs a connected board (409 `not_connected`); recording stops by itself at disconnect.
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
The server, in one call: saves the parameters → open loop (gains 0, `kff` 2), `baseline_n` 0, `fmax_n` = `force_n`, `arm_ms` 0, only `module` enabled → `ARM` (target 0 N, rope stays slack) → one `PULSE` (50 ms ramps, `dur_ms` 100–1000 incl. ramps) → `RELEASE 0` → restores the parameters. Starts only from DISARMED or ESTOP (else 409 `board_rejected`); one test pull at a time. Force is calculated from the motor current (open loop), not measured. `estop` works throughout.

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
→ {"pulse_id": 12}
```
Perturbation form (`host`): the server converts angle → channel amplitudes, then sends one `PULSE`.
```json
POST /api/v1/perturbation
{"angle_deg": 135, "amplitude_n": 20, "phase1_ms": 50, "dur_ms": 400, "phase2_ms": 50, "delay_ms": 0}
→ {"pulse_id": 13, "amps": {"A": 14.14, "D": 14.14}}
```
- `amplitude_n`: resultant force above baseline along `angle_deg`. `phase1_ms` / `phase2_ms`: ramp up / ramp down (acceleration phases one and two, `perturbation_definitions.md`); `dur_ms` start → end, ramps included; `delay_ms`: board-side delay before the start.
- Split: on a module's axis that module alone gets `amplitude_n`. Between two neighbouring modules (90° apart) the first gets `amplitude_n·cos(Δ)`, the second `amplitude_n·sin(Δ)`, Δ = angle past the first module. At 45° each gets `amplitude_n/√2`, the rule of the original firmware (`legacy/Arduino_Script.ino:82`). Assumes horizontal cables at right angles.
- An angle needing a module whose channel is off → 422 `invalid`, message names the module. Force limits stay on the board (`fmax_n` → 409 `board_rejected`).
- At baseline the cables do not cancel when a module is missing: with B not installed, the subject feels a constant pull of `baseline_n` towards D (back).

PTO (`planned`): adds `"pto": {"mode": "ms" | "stance_pct" | "cycle_pct", "value": 20}, "trigger": {"event": "FS", "side": "any"}` → waits for the next matching gait event, response adds `"scheduled": "same_fs" | "predicted_fs"`. `cycle_pct`: % of the gait cycle after the trigger foot strike (running: stance 0–40, float 40–55, swing 55–85, float 85–100, thesis Fig. 1); the server converts it with the measured stride time. The UI's gait-phase picker produces it.

| Method | Path | Returns | Status |
|---|---|---|---|
| GET | `/api/v1/geometry` | `{"convention": "...", "modules": {"A": {"angle_deg": 90, "enabled": true}, ...}, "reachable": [{"from_deg": 90, "to_deg": -90}]}` (arcs counter-clockwise from → to; `enabled`/`reachable` null when no board is connected) | host |

### Trials (`planned`)
| Method | Path | Body |
|---|---|---|
| POST | `/api/v1/trials` | trial config (below) → `{"trial_id": "20260929_142301"}` |
| POST | `/api/v1/trials/{id}/start` | |
| POST | `/api/v1/trials/{id}/stop` | ends scheduling; does not release tension |
| GET | `/api/v1/trials/{id}` | progress, log file paths, per-pulse measured vs commanded |

```json
{
  "perturbations": [{"angle_deg": 90, "amplitude_n": 95, "phase1_ms": 50, "dur_ms": 600, "phase2_ms": 0}],
  "blocks": 5, "shuffle": true,
  "pto": {"mode": "stance_pct", "value": 20},
  "interval": {"steps_min": 50, "steps_max": 75, "count_from": "recovery"},
  "recovery": {"method": "fixed_wait", "wait_s": 10},
  "baseline_window_s": 3
}
```
`recovery.method` is `fixed_wait` (stand-in, D8) until the lab algorithm is added. Values above are examples.

## Live stream (WebSocket)
`ws://127.0.0.1:8000/api/v1/stream?telemetry_hz=30`

Server → client, one JSON object per message:
```json
{"type": "telemetry", "t_ms": 1234, "state": "ARMED", "pulse_id": 0,
 "target": {"A": 5.0, ...}, "measured": {"A": 5.1, ...}, "dac": {"A": 1846, ...}}
{"type": "event", "t_ms": 1300, "kind": "PSTART", "args": ["12"]}
{"type": "gait", "t_s": 12.345, "event": "FS_VALID", "side": "left"}        // planned
{"type": "trial", "trial_id": "...", "done": 3, "total": 25}                   // planned
```
Telemetry is thinned to `telemetry_hz` for display. Logs always keep the full board rate.

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
