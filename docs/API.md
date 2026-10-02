# bumpem server API

The contract between the bumpem server and every client (the web UI in `BumpemUI`, MATLAB, scripts,
future apps). Clients use only this API, never the Python internals (DECISIONS D10).

**Version:** 1.0-draft. **`board` endpoints implemented** in `bumpem/server.py` (server 0.1.0, 2026-10-02; tests `tests/test_server.py`, simulator only so far). `planned` endpoints not implemented. Breaking changes bump the major
version and the path prefix (`/api/v1` → `/api/v2`). Additions do not.

**Status tags:** `board` = maps directly onto protocol v1 (`docs/PROTOCOL.md`), **implemented**. Interactive test page: `http://127.0.0.1:8000/docs`.
`planned` = needs the host layer (angle, PTO, trials); schema is a proposal.

## Basics
- Server: `bumpem serve`, listens on `http://127.0.0.1:8000` (this PC only). Other hosts only if started with `--host`.
- One server per PC. The server alone opens the Teensy's serial port (or the simulator).
- JSON everywhere. Units: force N, time ms, angle degrees.
- Angle: 0 = front, +90 = left, −90 = right (Vicon Forward/Left/Up axes). Reachable: −90…+90 (D out of service).
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
Perturbation form (`planned`): the server converts angle → channel amplitudes.
```json
POST /api/v1/perturbation
{"angle_deg": 45, "amplitude_n": 100, "phase1_ms": 50, "dur_ms": 600, "phase2_ms": 0,
 "pto": {"mode": "ms" | "stance_pct", "value": 20}, "trigger": {"event": "FS", "side": "any"}}
→ {"pulse_id": 13, "amps": {"A": 70.71, "B": 70.71}, "scheduled": "same_fs" | "predicted_fs"}
```
Without `pto`, it fires now. With `pto`, it waits for the next matching gait event.

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
