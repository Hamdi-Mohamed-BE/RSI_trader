"""Build the per-ORB trade-count funnel from the audit EA's ORBDIAG journal lines (5y runs)."""
from __future__ import annotations

import gzip
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
LINE = re.compile(r"ORBDIAG day=(\d+) dow=(-?\d+) range=(\S+) ratio=([\d.]+) orvol=([\d.]+) break=(\d) last=(\S+) traded=(\d)")
REASON_TEXT = {
    "ratio_high": "opening range too WIDE vs ATR (InpMaxRangeATR)",
    "ratio_low": "opening range too NARROW vs ATR (InpMinRangeATR)",
    "orvol_low": "opening volume below its 20-day median threshold",
    "no_bars": "no/too few M1 bars in the range window (holiday, closed market)",
    "pending": "session never reached the end of the range (no ticks)",
    "atr": "ATR not available", "median": "no volume history", "profile": "profile filter",
    "none": "range OK but price never CLOSED beyond it in the trade window",
    "body": "breakout candle body < InpBreakoutBodyMinimum",
    "bar_relvol": "breakout candle volume below InpMinBreakoutRelativeVolume",
    "buffer_or_colour": "close beyond range but within the ATR buffer or wrong candle colour",
    "direction_trend_profile": "direction/EMA-trend/profile filter",
    "vwap": "VWAP side filter", "retest_expired": "retest not seen in time",
    "risk_gt_max": "stop distance > InpMaximumStopATR x ATR (entry too far from the range)",
    "dts_session": "research session filter (InpResearchSession) blocked the entry hour",
    "spread_or_state": "spread > InpMaxSpreadRangePercent of range",
    "stops_level": "stop inside broker stops level", "lots": "lot size", "order_failed": "order rejected",
    "safe_regime": "safe regime filter", "position_open": "position already open",
}

out = ["# ORB trade-count funnel (5 years, 2021-09-05 → 2026-09-05, Model 1)", "",
       "Each weekday is classified once by the audit EA (identical trading logic to production + logging).", ""]
summary = {}
for v, spec in CONFIG["variants"].items():
    j = ROOT / "native" / f"orbaudit-{v}-{CONFIG['audit_period']}" / "journal.txt.gz"
    if not j.exists():
        out += [f"## {spec['label']}", "", "(not run yet)", ""]
        continue
    days = {}
    for m in LINE.finditer(gzip.decompress(j.read_bytes()).decode("utf-8", errors="replace")):
        day, dow, rng, ratio, orvol, brk, last, traded = m.groups()
        if int(dow) in (0, 6):
            continue
        days[day] = dict(range=rng, ratio=float(ratio), orvol=float(orvol), brk=int(brk), last=last, traded=int(traded))
    n = len(days)
    ok = [d for d in days.values() if d["range"] == "ok"]
    brk = [d for d in ok if d["brk"]]
    traded = [d for d in ok if d["traded"]]
    range_fail = Counter(d["range"] for d in days.values() if d["range"] != "ok")
    blocked = Counter(d["last"] for d in ok if not d["traded"] and d["brk"])
    ratios = sorted(d["ratio"] for d in days.values() if d["ratio"] > 0)
    med_ratio = ratios[len(ratios) // 2] if ratios else 0.0
    summary[v] = dict(weekdays=n, range_ok=len(ok), break_days=len(brk), traded=len(traded), median_range_atr=med_ratio)
    pct = lambda x: f"{x / n * 100:.1f}%" if n else "-"
    out += [f"## {spec['label']}", "",
            f"| Step | Days | % of weekdays |", "|---|---:|---:|",
            f"| Weekdays evaluated | {n} | 100% |",
            f"| Opening range accepted | {len(ok)} | {pct(len(ok))} |",
            f"| Price closed beyond the range in the trade window | {len(brk)} | {pct(len(brk))} |",
            f"| **Traded** | **{len(traded)}** | **{pct(len(traded))}** |", "",
            f"Median opening-range size = {med_ratio:.2f} × ATR (filter band {spec.get('band', 'see SET')}).", "",
            "Why the range was rejected:", ""]
    out += [f"- {REASON_TEXT.get(k, k)}: **{c}** days ({pct(c)})" for k, c in range_fail.most_common()]
    out += ["", "Why a real breakout day was not traded (last rule that blocked it):", ""]
    out += [f"- {REASON_TEXT.get(k, k)}: **{c}** days ({pct(c)})" for k, c in blocked.most_common()]
    out.append("")
(ROOT / "FUNNEL.md").write_text("\n".join(out) + "\n", encoding="utf-8")
(ROOT / "FUNNEL.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print("\n".join(out))
