"""Tower B load cell only, in a small window: live force, Start / Stop recording, Save as CSV.
For using the 200 kg sensor on its own (e.g. on the harness straps). The board stays DISARMED: no motor current.

  ~/miniconda3/bin/python scripts/b_force_logger.py
  ~/miniconda3/bin/python scripts/b_force_logger.py --port /dev/cu.usbmodemXXXX
  ~/miniconda3/bin/python scripts/b_force_logger.py --sim       # try it without hardware

Needs: Teensy on USB, tower B's 24 V (IAA100) on, brown wire in Teensy pin 15. 48 V can stay off.
The server must be stopped (only one program can open the port).
Calibration gain_B / offset_B is read from settings.json and written to the board at start
(the board forgets it on every restart). Range: 0-3.3 V = 0 to 200 * gain_B N (about 424 N with gain 2.12).
CSV columns: t_s (seconds since Start), board_ms (Teensy clock), force_N.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bumpem import protocol as P  # noqa: E402
from bumpem.device import Board  # noqa: E402

CAL = ("gain_B", "offset_B")
SHOW_S = 0.2        # displayed value = average of the last 0.2 s (~20 samples), so it doesn't flicker
STALE_S = 1.0       # no data for this long -> "no data" (USB dropped / Teensy reset)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="/dev/cu.usbmodem169222501")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--settings", default=str(ROOT / "settings.json"))
    a = ap.parse_args()

    if a.sim:
        from bumpem.sim import SimLink
        board = Board(SimLink())
    else:
        from bumpem.device import SerialLink
        board = Board(SerialLink(a.port))

    saved = json.loads(Path(a.settings).read_text())["params"] if Path(a.settings).is_file() else {}
    for k in CAL:
        if k in saved:
            board.set(k, saved[k])
    cal = board.get()
    print(f"board: {board.info()}  |  gain_B {cal.get('gain_B')}  offset_B {cal.get('offset_B')}")

    lock = threading.Lock()
    recent: list[tuple[float, float]] = []        # (host time, N) for the live display
    rows: list[tuple[float, int, float]] = []     # recording
    rec = {"on": False, "t0": 0.0}

    def on_msg(msg: P.Message) -> None:
        if not isinstance(msg, P.Telemetry) or "B" not in msg.measured:
            return
        now, f = time.monotonic(), msg.measured["B"]
        with lock:
            recent.append((now, f))
            while recent and recent[0][0] < now - SHOW_S:
                recent.pop(0)
            if rec["on"]:
                rows.append((now - rec["t0"], msg.t_ms, f))

    board.add_listener(on_msg)

    win = tk.Tk()
    win.title("Tower B force")
    value = tk.Label(win, text="--", font=("Helvetica", 56), width=9)
    value.pack(padx=20, pady=(20, 0))
    kg = tk.Label(win, text="", font=("Helvetica", 18))
    kg.pack()
    status = tk.Label(win, text="not recording", font=("Helvetica", 14))
    status.pack(pady=10)
    bar = tk.Frame(win)
    bar.pack(pady=(0, 20))

    def start() -> None:
        if rows and not messagebox.askyesno("Start", f"Discard the unsaved {len(rows)} samples?"):
            return
        with lock:
            rows.clear()
            rec.update(on=True, t0=time.monotonic())
        b_start.config(state="disabled"); b_stop.config(state="normal"); b_save.config(state="disabled")

    def stop() -> None:
        with lock:
            rec["on"] = False
        b_start.config(state="normal"); b_stop.config(state="disabled"); b_save.config(state="normal")

    def save() -> None:
        name = f"towerB_force_{datetime.now():%Y-%m-%d_%H%M%S}.csv"
        path = filedialog.asksaveasfilename(initialfile=name, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with lock:
            data = list(rows)
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["t_s", "board_ms", "force_N"])
            w.writerows((f"{t:.4f}", ms, f"{f:.2f}") for t, ms, f in data)
        rows.clear()
        b_save.config(state="disabled")
        status.config(text=f"saved {len(data)} samples to {Path(path).name}")

    b_start = tk.Button(bar, text="Start", width=8, command=start)
    b_stop = tk.Button(bar, text="Stop", width=8, command=stop, state="disabled")
    b_save = tk.Button(bar, text="Save CSV", width=8, command=save, state="disabled")
    for b in (b_start, b_stop, b_save):
        b.pack(side="left", padx=5)

    def refresh() -> None:
        with lock:
            vals = [f for _, f in recent]
            fresh = bool(recent) and time.monotonic() - recent[-1][0] < STALE_S
            n, on, t0 = len(rows), rec["on"], rec["t0"]
        if fresh:
            mean = sum(vals) / len(vals)
            value.config(text=f"{mean:7.1f} N", fg="black")
            kg.config(text=f"{mean / 9.81:.2f} kg")
        else:
            value.config(text="no data", fg="red")
            kg.config(text="USB dropped or Teensy reset? Close, replug, restart")
        if on:
            status.config(text=f"RECORDING  {time.monotonic() - t0:6.1f} s   {n} samples")
        win.after(100, refresh)

    def close() -> None:
        if rows and not messagebox.askyesno("Quit", f"Quit without saving {len(rows)} samples?"):
            return
        board.close()
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", close)
    refresh()
    win.mainloop()


if __name__ == "__main__":
    main()
