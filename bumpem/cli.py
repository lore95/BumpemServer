"""`bumpem` command-line entry point (protocol v1)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import protocol as P
from .device import Board, BoardError


def _open(args) -> Board:
    if args.sim:
        from .sim import SimLink
        return Board(SimLink())
    if not args.port:
        sys.exit("--port or --sim required (see `bumpem ports`)")
    from .device import SerialLink
    try:
        return Board(SerialLink(args.port))
    except Exception as e:     # busy port, wrong name, unplugged
        sys.exit(f"cannot open {args.port}: {e}")


def _amps(items: list[str]) -> dict[str, float]:
    out = {}
    for it in items:
        ch, _, val = it.partition("=")
        out[ch.upper()] = float(val)
    return out


def _print(msg) -> None:
    if isinstance(msg, P.Telemetry):
        cols = "  ".join(f"{c} {msg.target[c]:6.1f}/{msg.measured[c]:6.1f}" for c in P.CHANNELS)
        print(f"{msg.t_ms:>9} {msg.state:<9} {cols}")
    elif isinstance(msg, P.Event):
        print(f"{msg.t_ms:>9} ** {msg.kind} {' '.join(msg.args)}")
    elif isinstance(msg, str) and msg:
        print(f"# {msg}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bumpem")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ports", help="list serial ports")
    specs = {
        "info": "board info", "get": "read parameters", "set": "set a parameter",
        "arm": "enable drivers, ramp to baseline", "pulse": "one pulse (amplitudes relative to baseline)",
        "perturb": "one pulse by direction: 0 front, +90 left, -90 right, 180 back (split over the cables)",
        "abort": "cancel pulse", "release": "ramp to 0 and disable (stop treadmill first)",
        "estop": "drivers off now (stop treadmill first)", "clear": "clear FAULT",
        "stats": "loop timing", "monitor": "print telemetry and events",
    }
    for name, help_ in specs.items():
        p = sub.add_parser(name, help=help_)
        p.add_argument("--port")
        p.add_argument("--sim", action="store_true")
        if name == "get":
            p.add_argument("name", nargs="?")
        if name == "set":
            p.add_argument("name")
            p.add_argument("value", type=float)
        if name == "release":
            p.add_argument("--ms", type=float, default=1000)
        if name == "pulse":
            p.add_argument("amps", nargs="+", help="e.g. A=95  or  A=65.7 B=65.7")
            p.add_argument("--id", type=int, default=int(time.time()) % 1_000_000 + 1)
            p.add_argument("--delay", type=float, default=0)
            p.add_argument("--rise", type=float, default=50)
            p.add_argument("--dur", type=float, default=600)
            p.add_argument("--fall", type=float, default=0)
        if name == "perturb":
            p.add_argument("angle", type=float, help="pull direction in degrees (Vicon axes)")
            p.add_argument("amplitude", type=float, help="resultant force above baseline, N")
            p.add_argument("--id", type=int, default=int(time.time()) % 1_000_000 + 1)
            p.add_argument("--delay", type=float, default=0)
            p.add_argument("--phase1", type=float, default=50, help="ramp up, ms")
            p.add_argument("--dur", type=float, default=600, help="start to end incl. ramps, ms")
            p.add_argument("--phase2", type=float, default=0, help="ramp down, ms")
        if name in ("pulse", "perturb", "arm"):
            p.add_argument("--watch", type=float, default=0, help="then monitor for N seconds")
    sv = sub.add_parser("serve", help="HTTP/WebSocket API server (docs/API.md); test page at /docs")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000, help="HTTP port")
    sv.add_argument("--board", help="serial device to connect at startup, or 'sim'")
    sv.add_argument("--wd-ms", type=int, default=1000, help="board watchdog while served (0 = off)")
    mg = sv.add_mutually_exclusive_group()
    mg.add_argument("--testing", action="store_const", const="testing", dest="mode",
                    help="testing UI: one pull per motor, no arming (docs/API.md Modes)")
    mg.add_argument("--production", action="store_const", const="production", dest="mode",
                    help="production UI: arm, perturbations, force feedback (default)")
    sv.set_defaults(mode="production")
    sv.add_argument("--modules", default="ACD",
                    help="mounted modules: their channels are switched on at connect, the others off "
                         "(default ACD = setup 2026-10-02; \"\" = keep firmware defaults)")
    sv.add_argument("--ui", default=str(Path(__file__).resolve().parents[2] / "BumpemUI" / "web"),
                    help="browser UI folder, served at /ui/ (default: ../BumpemUI/web)")
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        try:
            import uvicorn
            from .server import create_app
        except ImportError:
            sys.exit('server extras missing: pip install -e ".[server]"')
        page = "/ui/testing.html" if args.mode == "testing" else "/ui/"
        print(f"bumpem server ({args.mode} mode) on http://{args.host}:{args.port}  (UI: {page}, API test page: /docs)")
        uvicorn.run(create_app(wd_ms=args.wd_ms, board=args.board, ui_dir=args.ui, modules=args.modules or None,
                               mode=args.mode),
                    host=args.host, port=args.port)
        return

    if args.cmd == "ports":
        from .device import find_ports
        print("\n".join(find_ports()) or "no ports found")
        return

    with _open(args) as b:
        try:
            if args.cmd == "info":
                print(b.info())
            elif args.cmd == "stats":
                print(b.stats())
            elif args.cmd == "get":
                for k, v in b.get(args.name).items():
                    print(f"{k:<14} {v:g}")
            elif args.cmd == "set":
                b.set(args.name, args.value)
            elif args.cmd == "arm":
                b.arm()
            elif args.cmd == "pulse":
                b.pulse(args.id, _amps(args.amps), delay_ms=args.delay, rise_ms=args.rise,
                        dur_ms=args.dur, fall_ms=args.fall)
            elif args.cmd == "perturb":
                from .geometry import MODULE_ANGLE_DEG, split
                params = b.get()
                amps = split(args.angle, args.amplitude, {m for m in MODULE_ANGLE_DEG if params.get(f"ch_{m}", 0) >= 1})
                print("amps:", " ".join(f"{m}={v:g}" for m, v in amps.items()))
                b.pulse(args.id, amps, delay_ms=args.delay, rise_ms=args.phase1, dur_ms=args.dur, fall_ms=args.phase2)
            elif args.cmd == "abort":
                b.abort()
            elif args.cmd == "release":
                b.release(args.ms)
            elif args.cmd == "clear":
                b.clear()
            elif args.cmd == "estop":
                b.estop()
                time.sleep(0.2)          # let the write go out before closing
        except (BoardError, ValueError) as e:
            sys.exit(f"error: {e}")

        watch = args.cmd == "monitor" or getattr(args, "watch", 0) > 0
        if watch:
            b.add_listener(_print)
            try:
                time.sleep(args.watch if args.cmd != "monitor" else 1e9)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
