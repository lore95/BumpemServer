"""Delay report from one recording (docs/API.md "Recording" → Delay report, DECISIONS D51). Plain csv: no pandas.

Per pulse (CMD row + the board's PSTART): command_ms = board start − server send − requested delay (USB + firmware);
rise_ms = board start → rope force leaves its baseline (mean of the 300 ms before + max(2 SD, 2 N), 3 samples in a row:
the lab's start definition, perturbation_definitions.md); lag_ms = measured force reaches half the amplitude after the
target does; ratio = plateau measured / target amplitude (pull strength). Study pulls (PERT): timing_error_ms = rope force
start − intended start (touch-down on the PC clock − Vicon latency + phase) → recommended System delay =
the one used + median timing error.
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any

MIN_RISE_N = 2.0           # rope force above baseline counts as started at this or 2 SD, whichever is larger
BASE_MS = 300              # baseline window before the board's start


def _f(x: str) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _load(events: Path, force: Path, vicon: Path | None):
    with events.open(newline="") as f:
        ev = list(csv.DictReader(f))
    with force.open(newline="") as f:
        fr = [r for r in csv.DictReader(f)]
    t = [int(r["time_ms"]) for r in fr]
    lat = []
    if vicon and vicon.is_file():
        with vicon.open(newline="") as f:
            for r in csv.DictReader(f):
                v = _f(r.get("latency_ms", ""))
                if v is not None:
                    lat.append(v)
    return ev, fr, t, (statistics.median(lat) if lat else None)


def _pulses(ev: list[dict]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for r in ev:
        kind, args, pc = r["kind"], r["args"], _f(r.get("pc_s", ""))
        if kind == "CMD":
            d = json.loads(args)
            pid = d.get("pulse_id")
            if pid is None:
                continue
            amps = d.get("amps") or ({d["test_pull"]: d["force_n"]} if "test_pull" in d else {})
            out.setdefault(pid, {}).update(pid=pid, amps=amps, delay_ms=float(d.get("delay_ms", 0) or 0),
                                           phase1_ms=float(d.get("phase1_ms", d.get("rise_ms", 50)) or 0),
                                           dur_ms=float(d.get("dur_ms", 0) or 0),
                                           phase2_ms=float(d.get("phase2_ms", d.get("fall_ms", 50)) or 0),
                                           sent_pc=d.get("sent_pc"), cmd_pc=pc)
        elif kind == "PSTART":
            pid = int(args.split()[0])
            out.setdefault(pid, {}).update(start_ms=int(r["time_ms"]), start_pc=pc)
        elif kind == "PERT":
            d = json.loads(args)
            out.setdefault(d["pulse_id"], {}).update(pert=d)
    return out


def _measure(p: dict, fr: list[dict], t: list[int]) -> dict[str, Any]:
    """Rise, lag and ratio on the main module of one pulse (board clock: 10 ms per telemetry sample)."""
    if "start_ms" not in p or not p.get("amps"):
        return {}
    m, amp = max(p["amps"].items(), key=lambda kv: kv[1])
    s0 = p["start_ms"]
    base = [float(r[f"measured_{m}"]) for r, ti in zip(fr, t) if s0 - BASE_MS <= ti < s0]
    tbase = [float(r[f"target_{m}"]) for r, ti in zip(fr, t) if s0 - BASE_MS <= ti < s0]
    if len(base) < 5:
        return {"module": m, "amp_n": amp}
    mu, sd, tmu = statistics.fmean(base), statistics.pstdev(base), statistics.fmean(tbase)
    thr = max(2 * sd, MIN_RISE_N)
    after = [(ti, float(r[f"measured_{m}"]), float(r[f"target_{m}"]), _f(r.get("pc_s", "")))
             for r, ti in zip(fr, t) if s0 <= ti <= s0 + p.get("dur_ms", 0) + 500]
    onset = onset_pc = None
    for k in range(len(after) - 2):
        if all(after[k + j][1] - mu > thr for j in range(3)):
            onset, onset_pc = after[k][0], after[k][3]
            break
    half_t = next((ti for ti, _, tg, _ in after if tg - tmu >= amp / 2), None)
    half_m = next((ti for ti, ms, _, _ in after if ms - mu >= amp / 2), None)
    lo, hi = s0 + p.get("phase1_ms", 0) + 50, s0 + p.get("dur_ms", 0) - p.get("phase2_ms", 0)
    plateau = [ms - mu for ti, ms, _, _ in after if lo <= ti <= hi]
    return {"module": m, "amp_n": round(amp, 1), "base_n": round(mu, 2), "noise_sd_n": round(sd, 2),
            "rise_ms": None if onset is None else onset - s0, "onset_pc": onset_pc,
            "lag_ms": None if half_t is None or half_m is None else half_m - half_t,
            "ratio": round(statistics.fmean(plateau) / amp, 2) if plateau and amp > 0 else None}


def analyze(events: Path, force: Path, vicon: Path | None = None) -> dict[str, Any]:
    ev, fr, t, vlat = _load(Path(events), Path(force), Path(vicon) if vicon else None)
    rows, errors, used_latency = [], [], None
    for pid, p in sorted(_pulses(ev).items()):
        r: dict[str, Any] = {"pulse_id": pid, "delay_ms": p.get("delay_ms")}
        if "start_ms" not in p:                   # STOP / Release before it began, or the recording ended first
            r["note"] = "not started in this recording"
        sent = p.get("sent_pc") if p.get("sent_pc") is not None else p.get("cmd_pc")
        if sent is not None and p.get("start_pc") is not None:
            r["command_ms"] = round((p["start_pc"] - sent) * 1000 - (p.get("delay_ms") or 0), 1)
        r.update(_measure(p, fr, t))
        d = p.get("pert")
        if d and d.get("td_pc") is not None and r.get("onset_pc") is not None:
            intended = d["td_pc"] - (vlat or 0) / 1000 + d["phase_ms"] / 1000
            r["timing_error_ms"] = round((r["onset_pc"] - intended) * 1000, 1)
            errors.append(r["timing_error_ms"])
            used_latency = d.get("latency_ms") or 0
        r.pop("onset_pc", None)
        rows.append(r)
    rec = round(used_latency + statistics.median(errors), 1) if errors else None
    return {"pulses": rows, "vicon_latency_ms": vlat, "recommended_latency_ms": rec, "text": _text(rows, vlat, rec, events)}


def _text(rows: list[dict], vlat: float | None, rec: float | None, events: Path) -> str:
    def col(k):
        v = [r[k] for r in rows if r.get(k) is not None]
        return f"median {statistics.median(v):.1f}, min {min(v):.1f}, max {max(v):.1f} (n {len(v)})" if v else "–"
    out = [f"Delay report: {Path(events).name}", "",
           f"{'pulse':>5} {'tower':>5} {'amp N':>6} {'command ms':>10} {'rise ms':>7} {'lag ms':>6} {'ratio':>5} {'timing err ms':>13}"]
    for r in rows:
        f = lambda k, fmt="{:.1f}": "–" if r.get(k) is None else fmt.format(r[k])   # noqa: E731
        out.append(f"{r['pulse_id']:>5} {r.get('module', '–'):>5} {f('amp_n'):>6} {f('command_ms'):>10} {f('rise_ms', '{:.0f}'):>7} "
                   f"{f('lag_ms', '{:.0f}'):>6} {f('ratio', '{:.2f}'):>5} {f('timing_error_ms'):>13}"
                   + (f"   {r['note']}" if r.get("note") else ""))
    out += ["", f"command (server → board start, minus the requested delay): {col('command_ms')} ms",
            f"rise (board start → rope force leaves its baseline):        {col('rise_ms')} ms",
            f"lag (measured reaches half the amplitude after the target): {col('lag_ms')} ms",
            f"ratio (plateau measured / target amplitude):                {col('ratio')}",
            f"Vicon latency (its own estimate, median):                   {'–' if vlat is None else f'{vlat:.1f} ms'}"]
    if rec is not None:
        out += [f"study timing error (rope force start − intended):          {col('timing_error_ms')} ms",
                f"→ recommended System delay: {rec:.0f} ms (enter it next to Start on BumpemActivation; "
                "positive = pulls come late)"]
    else:
        out.append("No study pulls with touch-down times: run a block on BumpemActivation to get the System delay.")
    out += ["", "Times on the board clock (10 ms per sample) and the station-PC clock (pc_s). Bring this file to Claude."]
    return "\n".join(out) + "\n"
