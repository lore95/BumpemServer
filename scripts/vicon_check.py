"""Vicon connection report for Claude, read-only (vicon_check.bat). Nothing is changed or installed.

Collects: this PC's addresses, TCP port 801 on the candidate Nexus addresses, the Vicon SDK (load, version, connect
attempt, and if it connects: rate, devices, Fz per plate), every ViconDataStreamSDK*.dll on C: with its FileVersion
(e.g. the one D-Flow uses with this Nexus), and lines in D-Flow / Motek settings files that mention Vicon or port 801.
Writes everything to vicon_check_<date_time>.txt (--out) as well as the screen.

  python scripts/vicon_check.py --host 192.168.1.60:801 --out ..
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CANDIDATES = ["192.168.1.60", "192.168.10.1", "192.168.1.101", "192.168.70.50"]   # Nexus PC, legacy script, D-Flow peers
TEXT = (".xml", ".ini", ".cfg", ".config", ".json", ".txt", ".settings")
HINT = re.compile(r"vicon|datastream|:801\b|\b801\b", re.I)
WALK_S = 300


class Report:
    def __init__(self):
        self.lines: list[str] = []

    def __call__(self, *parts):
        s = " ".join(str(p) for p in parts)
        print(s, flush=True)
        self.lines.append(s)

    def section(self, title):
        self("")
        self(f"=== {title}")


def tcp(host: str, port: int) -> str:
    try:
        socket.create_connection((host, port), 2).close()
        return "open"
    except socket.timeout:
        return "timed out"
    except OSError as e:
        return type(e).__name__ + f" ({e})"


def sdk(r: Report, host: str) -> None:
    try:
        from vicon_dssdk import ViconDataStream as V
    except Exception as e:
        r("vicon_dssdk does not load:", repr(e))
        return
    import vicon_dssdk
    r("vicon_dssdk from", Path(vicon_dssdk.__file__).parent)
    client = V.Client()
    r("SDK client version", client.GetVersion())
    connected = None
    for h in dict.fromkeys([host, host.split(":")[0]]):
        t0 = time.monotonic()
        try:
            client.Connect(h)
            r(f"Connect({h!r}): OK in {time.monotonic() - t0:.1f} s")
            connected = h
            break
        except Exception as e:
            r(f"Connect({h!r}): FAILED after {time.monotonic() - t0:.1f} s:", str(e).strip() or repr(e))
    if not connected:
        return
    try:
        r("IsConnected", client.IsConnected())
        client.EnableDeviceData()
        end, got = time.monotonic() + 5, False
        while time.monotonic() < end and not got:
            try:
                got = client.GetFrame()
            except V.DataStreamException as e:
                r("GetFrame:", str(e).strip())
                time.sleep(0.2)
        if not got:
            r("no frame within 5 s (Nexus in Live mode?)")
            return
        r("frame", client.GetFrameNumber(), "rate", client.GetFrameRate(), "Hz")
        plates = []
        for name, kind in client.GetDeviceNames():
            outs = client.GetDeviceOutputDetails(name)
            r(f"device {name!r} ({kind}):", ", ".join(f"{o}/{c}" for o, c, _u in outs))
            plates += [(name, o) for o, c, _u in outs if c == "Fz"]
        r("Fz per plate, 3 s (stand on one belt):")
        end = time.monotonic() + 3
        while time.monotonic() < end:
            if client.GetFrame():
                vals = []
                for name, o in plates:
                    v, _ = client.GetDeviceOutputValues(name, o, "Fz")
                    vals.append(f"{name}: {sum(v) / max(len(v), 1):8.1f} N ({len(v)} sub)")
                r("   " + "   ".join(vals))
            time.sleep(0.25)
    except Exception as e:
        r("after connecting:", repr(e))
    finally:
        try:
            client.Disconnect()
        except Exception:
            pass


def dll_version(p: Path) -> str:
    try:
        t = p.read_bytes().decode("utf-16-le", "ignore")
        m = re.findall(r"FileVersion\W+([\d.]+)", t)
        return m[0] if m else "?"
    except OSError as e:
        return f"unreadable ({e.strerror})"


def walk(r: Report) -> None:
    """One pass over C: (Windows folder skipped, max WALK_S): Vicon SDK DLLs, and D-Flow/Motek text settings."""
    dlls, hints, t0 = [], [], time.monotonic()
    root = Path(os.environ.get("SystemDrive", "C:") + os.sep)
    skip = {"windows", "$recycle.bin", "system volume information"}
    stopped = False
    for d, subdirs, files in os.walk(root, onerror=lambda e: None):
        if time.monotonic() - t0 > WALK_S:
            stopped = True
            break
        subdirs[:] = [s for s in subdirs if s.lower() not in skip]
        low = d.lower()
        dflow = any(k in low for k in ("d-flow", "dflow", "motek"))
        for f in files:
            fl = f.lower()
            if fl.startswith("vicondatastreamsdk") and fl.endswith(".dll"):
                dlls.append(Path(d) / f)
            elif dflow and fl.endswith(TEXT) and len(hints) < 60:
                p = Path(d) / f
                try:
                    if p.stat().st_size > 2_000_000:
                        continue
                    for i, line in enumerate(p.read_text(errors="ignore").splitlines()):
                        if HINT.search(line):
                            hints.append(f"{p} : {i + 1}: {line.strip()[:200]}")
                except OSError:
                    pass
    r.section(f"Vicon SDK DLLs on {root} ({time.monotonic() - t0:.0f} s{', search stopped at the time limit' if stopped else ''})")
    for p in dlls:
        r(f"{dll_version(p):>14}  {p}")
    if not dlls:
        r("none found")
    r.section("D-Flow / Motek settings lines mentioning Vicon or 801")
    for h in hints:
        r(h)
    if not hints:
        r("none found")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="192.168.1.60:801", help="Nexus address:port")
    ap.add_argument("--out", default=".", help="folder for vicon_check_<date_time>.txt")
    a = ap.parse_args()
    r = Report()
    r(f"Vicon check {datetime.now():%Y-%m-%d %H:%M:%S} on {socket.gethostname()}, Python {sys.version.split()[0]},"
      f" {platform.platform()}")
    r.section("ipconfig")
    try:
        out = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=15, errors="ignore").stdout
        for line in out.splitlines():
            if line.strip() and ("IPv4" in line or "Subnet" in line or "Gateway" in line or "adapter" in line):
                r(line.rstrip())
    except Exception as e:
        r("ipconfig failed:", repr(e))
    host = a.host
    r.section("TCP port 801")
    for h in dict.fromkeys([host.split(":")[0]] + CANDIDATES):
        r(f"{h:>15}:801  {tcp(h, 801)}")
    r.section(f"Vicon SDK, connect to {host}")
    sdk(r, host)
    r("")
    r(f"Searching C: for Vicon DLLs and D-Flow settings (up to {WALK_S // 60} min)...")
    walk(r)
    path = Path(a.out).resolve() / f"vicon_check_{datetime.now():%Y%m%d_%H%M%S}.txt"
    path.write_text("\n".join(r.lines) + "\n", encoding="utf-8")
    print(f"\nSaved: {path}\nCopy this file to the USB stick and give it to Claude.")


if __name__ == "__main__":
    main()
