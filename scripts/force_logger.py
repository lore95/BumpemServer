"""One load cell only, in a small window: live force + plot, Calibrate / Zero, Start / Stop recording, Save as CSV.
For using a sensor on its own (e.g. on the harness straps). The board stays DISARMED: no motor current.

  ~/miniconda3/bin/python scripts/force_logger.py                     # tower D (default)
  ~/miniconda3/bin/python scripts/force_logger.py --tower B
  ~/miniconda3/bin/python scripts/force_logger.py --sim               # try it without hardware

Needs: Teensy on USB, that tower's 24 V (IAA100) on, its brown wire in the Teensy (A 14, B 15, C 16, D 17).
48 V can stay off. The server must be stopped (only one program can open the port).
Calibration lives here, not in the firmware (so any sensor/amplifier pair works, beyond the firmware's 0.5-3 gain range):
the board is set to gain 1 / offset 0 (raw = ADC / 1023 * 200 N), and force_N = (raw - zero) * k.
Calibrate = 2 s unloaded + 2 s with a known weight; Zero = tare (keeps k). Saved per tower in force_logger_cal.json
(BumpemServer/, not in git). Recalibrate after moving the sensor to another amplifier.
CSV columns: t_s (seconds since Start), board_ms (Teensy clock), force_N, raw_N.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import threading
import time
from collections import deque
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bumpem import protocol as P  # noqa: E402
from bumpem.device import Board  # noqa: E402

CAL_FILE = ROOT / "force_logger_cal.json"
G = 9.81
SHOW_S = 0.2        # displayed value = average of the last 0.2 s (~20 samples), so it doesn't flicker
STALE_S = 1.0       # no data for this long -> "no data" (USB dropped / Teensy reset)
PLOT_S = 10.0       # live plot window
MEAS_S = 2.0        # averaging time for each calibration step
SETTLE_S = 1.0      # wait after the weight is hung before averaging
MIN_RISE = 5.0      # raw N: smaller change with the weight on = something is wrong (no 24 V, wrong wire)
PLOT_W, PLOT_H, PAD = 900, 340, 48


def load_cal() -> dict:
    return json.loads(CAL_FILE.read_text()) if CAL_FILE.is_file() else {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="/dev/cu.usbmodem169222501")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--tower", default="D", choices=list("ABCD"))
    a = ap.parse_args()
    T = a.tower

    if a.sim:
        from bumpem.sim import SimLink
        board = Board(SimLink())
    else:
        from bumpem.device import SerialLink
        board = Board(SerialLink(a.port))
    board.set(f"gain_{T}", 1)
    board.set(f"offset_{T}", 0)
    print(f"board: {board.info()}  |  tower {T}: firmware gain 1, offset 0 (calibration applied here)")

    lock = threading.Lock()
    cal = load_cal().get(T, {"k": 1.0, "zero": 0.0, "date": None})
    recent: list[tuple[float, float]] = []        # (host time, N) for the live display
    hist: deque[tuple[float, float]] = deque()     # (host time, N), last PLOT_S, for the plot
    raw_hist: deque[tuple[float, float]] = deque() # (host time, raw N), last PLOT_S, for calibration
    rows: list[tuple[float, int, float, float]] = []   # recording
    rec = {"on": False, "t0": 0.0}

    def on_msg(msg: P.Message) -> None:
        if not isinstance(msg, P.Telemetry) or T not in msg.measured:
            return
        now, raw = time.monotonic(), msg.measured[T]
        with lock:
            f = (raw - cal["zero"]) * cal["k"]
            recent.append((now, f))
            while recent and recent[0][0] < now - SHOW_S:
                recent.pop(0)
            for q, v in ((hist, f), (raw_hist, raw)):
                q.append((now, v))
                while q and q[0][0] < now - PLOT_S:
                    q.popleft()
            if rec["on"]:
                rows.append((now - rec["t0"], msg.t_ms, f, raw))

    board.add_listener(on_msg)

    win = tk.Tk()
    win.title(f"Tower {T} force")
    value = tk.Label(win, text="--", font=("Helvetica", 56), width=9)
    value.pack(padx=20, pady=(20, 0))
    kg = tk.Label(win, text="", font=("Helvetica", 18))
    kg.pack()
    cal_label = tk.Label(win, text="", font=("Helvetica", 13))
    cal_label.pack(pady=(6, 0))
    status = tk.Label(win, text="not recording", font=("Helvetica", 14))
    status.pack(pady=10)
    plot = tk.Canvas(win, width=PLOT_W, height=PLOT_H, bg="white", highlightthickness=0)
    plot.pack(padx=20)
    thr_row = tk.Frame(win)
    thr_row.pack(pady=(10, 0))
    tk.Label(thr_row, text="Threshold line (N, empty = none):").pack(side="left")
    thr_var = tk.StringVar()
    thr_entry = tk.Entry(thr_row, textvariable=thr_var, width=8)
    thr_entry.pack(side="left", padx=5)
    bar = tk.Frame(win)
    bar.pack(pady=20)

    # ---------- calibration
    def show_cal() -> None:
        if cal["date"]:
            cal_label.config(text=f"calibrated {cal['date']}: k {cal['k']:.3f}, zero {cal['zero']:.1f} raw N", fg="black")
        else:
            cal_label.config(text="NOT CALIBRATED: press Calibrate (values are raw firmware N)", fg="red")

    def store(**kw) -> None:
        with lock:
            cal.update(kw)
            if "k" in kw:                     # only a full calibration sets the date; Zero alone does not
                cal["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        allc = load_cal()
        allc[T] = dict(cal)
        CAL_FILE.write_text(json.dumps(allc, indent=1))
        show_cal()

    def raw_mean(since: float) -> float | None:
        with lock:
            v = [r for t, r in raw_hist if t >= since]
        return sum(v) / len(v) if len(v) >= 10 else None

    def busy(on: bool, text: str = "") -> None:
        for b in (b_cal, b_zero, b_start):
            b.config(state="disabled" if on else "normal")
        if text:
            status.config(text=text)

    def calibrate() -> None:
        if not messagebox.askokcancel("Calibrate 1/2", "Remove ALL load: let the sensor hang free.\nPress OK, then don't touch it for 2 s."):
            return
        busy(True, "measuring zero (2 s)...")
        t1 = time.monotonic()
        win.after(int(MEAS_S * 1000) + 200, lambda: cal_step2(t1))

    def cal_step2(t1: float) -> None:
        z = raw_mean(t1)
        if z is None:
            busy(False, "no data from the board: calibration cancelled"); return
        mass = simpledialog.askfloat("Calibrate 2/2", "Hang the known weight and let it stop swinging.\nIts mass in kg:",
                                     initialvalue=12.0, minvalue=0.1, parent=win)
        if mass is None:
            busy(False, "calibration cancelled"); return
        busy(True, "measuring the weight (3 s)...")
        t2 = time.monotonic() + SETTLE_S
        win.after(int((SETTLE_S + MEAS_S) * 1000) + 200, lambda: cal_step3(z, mass, t2))

    def cal_step3(z: float, mass: float, t2: float) -> None:
        w = raw_mean(t2)
        busy(False)
        if w is None:
            status.config(text="no data from the board: calibration cancelled"); return
        if w - z < MIN_RISE:
            status.config(text=f"reading changed only {w - z:.1f} raw N: weight on? 24 V on? right wire? Not saved.")
            return
        store(k=mass * G / (w - z), zero=z)
        status.config(text=f"calibrated with {mass:g} kg ({mass * G:.1f} N), saved")

    def zero() -> None:
        z = raw_mean(time.monotonic() - 1.0)
        if z is None:
            status.config(text="no data from the board"); return
        store(zero=z)
        status.config(text="zeroed (k kept)")

    # ---------- recording
    def start() -> None:
        if rows and not messagebox.askyesno("Start", f"Discard the unsaved {len(rows)} samples?"):
            return
        with lock:
            rows.clear()
            rec.update(on=True, t0=time.monotonic())
        b_start.config(state="disabled"); b_stop.config(state="normal"); b_save.config(state="disabled")
        b_cal.config(state="disabled"); b_zero.config(state="disabled")

    def stop() -> None:
        with lock:
            rec["on"] = False
        b_start.config(state="normal"); b_stop.config(state="disabled"); b_save.config(state="normal")
        b_cal.config(state="normal"); b_zero.config(state="normal")

    def save() -> None:
        name = f"tower{T}_force_{datetime.now():%Y-%m-%d_%H%M%S}.csv"
        path = filedialog.asksaveasfilename(initialfile=name, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with lock:
            data = list(rows)
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["t_s", "board_ms", "force_N", "raw_N"])
            w.writerows((f"{t:.4f}", ms, f"{f:.2f}", f"{r:.2f}") for t, ms, f, r in data)
        rows.clear()
        b_save.config(state="disabled")
        status.config(text=f"saved {len(data)} samples to {Path(path).name}")

    b_cal = tk.Button(bar, text="Calibrate", width=8, command=calibrate)
    b_zero = tk.Button(bar, text="Zero", width=8, command=zero)
    b_start = tk.Button(bar, text="Start", width=8, command=start)
    b_stop = tk.Button(bar, text="Stop", width=8, command=stop, state="disabled")
    b_save = tk.Button(bar, text="Save CSV", width=8, command=save, state="disabled")
    for b in (b_cal, b_zero, b_start, b_stop, b_save):
        b.pack(side="left", padx=5)

    # ---------- display
    def threshold() -> float | None:
        try:
            v = float(thr_var.get().replace(",", "."))
        except ValueError:
            v = None
        thr_entry.config(bg="white" if v is not None or not thr_var.get().strip() else "#ffd0d0")
        return v

    def draw(pts: list[tuple[float, float]]) -> None:
        plot.delete("all")
        now = time.monotonic()
        thr = threshold()
        top = max(20.0, max((f for _, f in pts), default=0) * 1.15, (thr or 0) * 1.15)
        bot = min(0.0, min((f for _, f in pts), default=0) * 1.15, (thr or 0) * 1.15)
        x = lambda t: PAD + (PLOT_W - PAD - 10) * (1 - (now - t) / PLOT_S)
        y = lambda f: PLOT_H - 24 - (PLOT_H - 34) * (f - bot) / (top - bot)
        for i in range(6):
            f = bot + (top - bot) * i / 5
            plot.create_line(PAD, y(f), PLOT_W - 10, y(f), fill="#e4e4e4")
            plot.create_text(PAD - 6, y(f), text=f"{f:.0f}", anchor="e", font=("Helvetica", 11))
        for s in range(0, int(PLOT_S) + 1, 2):
            plot.create_text(x(now - s), PLOT_H - 10, text="now" if s == 0 else f"-{s} s", font=("Helvetica", 11))
        plot.create_text(6, 8, text="N", anchor="w", font=("Helvetica", 11))
        if thr is not None:
            plot.create_line(PAD, y(thr), PLOT_W - 10, y(thr), fill="#d62728", width=2, dash=(6, 4))
            plot.create_text(PLOT_W - 12, y(thr) - 9, text=f"{thr:g} N", anchor="e", fill="#d62728", font=("Helvetica", 11))
        if len(pts) > 1:
            plot.create_line(*[c for t, f in pts for c in (x(t), y(f))], fill="#1f6fd1", width=2)

    def refresh() -> None:
        with lock:
            pts = list(hist)
            vals = [f for _, f in recent]
            fresh = bool(recent) and time.monotonic() - recent[-1][0] < STALE_S
            n, on, t0 = len(rows), rec["on"], rec["t0"]
        if fresh:
            mean = sum(vals) / len(vals)
            value.config(text=f"{mean:7.1f} N", fg="black")
            kg.config(text=f"{mean / G:.2f} kg")
        else:
            value.config(text="no data", fg="red")
            kg.config(text="USB dropped or Teensy reset? Close, replug, restart")
        draw(pts)
        if on:
            status.config(text=f"RECORDING  {time.monotonic() - t0:6.1f} s   {n} samples")
        win.after(100, refresh)

    def close() -> None:
        if rows and not messagebox.askyesno("Quit", f"Quit without saving {len(rows)} samples?"):
            return
        board.close()
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", close)
    show_cal()
    refresh()
    win.mainloop()


if __name__ == "__main__":
    main()
