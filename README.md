# bumpem

Host software for the IBMS Bump'em multi-directional perturbation system.

## Quick start
```sh
git clone <repo> && cd bumpem
python -m venv .venv && source .venv/bin/activate   # or conda
pip install -e ".[dev]"
pytest                                   # no hardware needed
bumpem monitor --sim                     # simulated board
```

## With hardware
No person attached for first tests. Stop the treadmill before `release` or `estop`.
```sh
pip install platformio
scripts/flash.sh                         # firmware v1  (scripts/flash.sh legacy = v0 reference)
bumpem ports                             # find the Teensy
bumpem info  --port /dev/tty.usbmodemXXXX
bumpem arm   --port /dev/tty.usbmodemXXXX --watch 3     # ramp to 5 N baseline
bumpem pulse A=95 --rise 50 --dur 600 --fall 0 --port /dev/tty.usbmodemXXXX --watch 2
bumpem release --port /dev/tty.usbmodemXXXX              # ramp to 0, drivers off
bumpem estop   --port /dev/tty.usbmodemXXXX              # drivers off now
```
Pulse amplitudes are relative to baseline. Protocol and parameters: `docs/PROTOCOL.md`.

ESCON setup is still done once in ESCON Studio. See `escon/README.md` and `docs/thesis/manual.pdf` §4.3.1.

Docs: `docs/knowledge/` (system facts), `docs/PROTOCOL.md`, `docs/STATUS.md`.

## Server
```sh
pip install -e ".[server,dev]"
bumpem serve --board sim                      # or --board /dev/tty.usbmodemXXXX
```
Open http://127.0.0.1:8000/docs to try every endpoint from the browser. API contract: `docs/API.md`.
While the server runs it owns the serial port: stop the board through the API (`POST /api/v1/estop`), not the CLI.
