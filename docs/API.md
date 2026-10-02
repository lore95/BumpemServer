# bumpem server API

The contract between the bumpem server and every client (the web UI in `BumpemUI`, MATLAB, scripts,
future apps). Clients use only this API, never the Python internals (DECISIONS D10).

**Version:** 1.0-draft. Server 0.2.0 (2026-10-02): `board` and `host` endpoints implemented in `bumpem/server.py` (tests `tests/test_server.py`, `tests/test_geometry.py`, simulator). `planned` endpoints not implemented. Breaking changes bump the major
version and the path prefix (`/api/v1` → `/api/v2`). Additions do not.

**Status tags:** `board` = maps directly onto protocol v1 (`docs/PROTOCOL.md`), **implemented**. Interactive test page: `http://127.0.0.1:8000/docs`.
`host` = computed by the server, then sent as protocol v1 commands, **implemented**.
`planned` = needs gait events / trials (PTO, scheduling); schema is a proposal.

## Basics
- Server: `bumpem serve`, listens on `http://127.0.0.1:8000` (this PC only). Other hosts only if started with `--host`.
- One server per PC. The server alone opens the Teensy's serial port (or the simulator).
- JSON everywhere. Units: force N, time ms, angle degrees.
- Angle (Vicon Forward/Left/Up axes, counter-clockwise seen from above): **0 = front, +90 = left, −90 = right, 180 = back**. Any value is accepted and normalised to (−180, 180]. The angle is the direction the subject is pulled.
- Modules: A +90 (left), B 0 (front), C −90 (right), D 180 (back). A module is available when its channel is on (`ch_A`…`ch_D` = 1). Setup 2026-10-02: A, C, D mounted, B not installed → reachable +90 … 180 … −90 (left, back, right and the back diagonals).
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

## Endpoints

### Connection
| Method | Path | Body | Returns | Status |
|---|---|---|---|---|
| GET | `/api/v1/info` | | `{"server": "0.1.0", "api": "1.0", "port": "sim", "board": {...INFO fields} or null}` | board |
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

PTO (`planned`): adds `"pto": {"mode": "ms" | "stance_pct", "value": 20}, "trigger": {"event": "FS", "side": "any"}` → waits for the next matching gait event, response adds `"scheduled": "same_fs" | "predicted_fs"`.

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
