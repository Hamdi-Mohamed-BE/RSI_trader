"""Side-by-side: Nasdaq 5M momentum on USTEC vs US500 vs US30, DI on/off, 6m/1y/3y/5y to 2026-09-25."""
from __future__ import annotations

import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
runs = {}
for f in (ROOT / "native").glob("n5idx-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if m.get("ok"):
        m["trades"] = sorted(json.loads(gzip.decompress((f.parent / "trades.json.gz").read_bytes()).decode("utf-8")),
                             key=lambda t: t["close_time"])
        runs[(m["symbol"], m["variant"], m["period"])] = m


def extra(m: dict) -> dict:
    a = datetime.strptime(m["start"], "%Y.%m.%d").date()
    b = datetime.strptime(m["end_exclusive"], "%Y.%m.%d").date()
    weekdays = sum(1 for i in range((b - a).days) if (a + timedelta(days=i)).weekday() < 5)
    n = m["metrics"]["trades"]
    streaks, cur, k = [], None, 0
    for x in m["trades"]:
        r = "W" if x["net_profit"] > 0 else "L" if x["net_profit"] < 0 else None
        if r is None:
            continue
        if r == cur:
            k += 1
        else:
            if cur:
                streaks.append((cur, k))
            cur, k = r, 1
    if cur:
        streaks.append((cur, k))
    w = [q for s, q in streaks if s == "W"]
    lo = [q for s, q in streaks if s == "L"]
    return dict(pm=n / ((b - a).days / 30.4375), pd=n / max(weekdays, 1), aw=sum(w) / len(w) if w else 0,
                al=sum(lo) / len(lo) if lo else 0, mw=max(w, default=0), ml=max(lo, default=0),
                cost=sum(x["total_costs"] for x in m["trades"]))


lines = ["# Nasdaq 5M candle momentum — USTEC vs US500 vs US30", "",
         "Isolated MT5 tester (Exness-MT5Trial16), $10,000, 1% risk, M5, Model 4 (real ticks from 2026-01), 150 ms delay; "
         "unchanged production DI EX5 + claude_eas SET; windows end 2026-09-25. Per day = per trading day (Mon-Fri).", ""]
for p in CONFIG["periods"]:
    lines += [f"## {p} ({CONFIG['periods'][p]} → {CONFIG['end_date']})", "",
              "| Symbol | Version | Trades | /month | /day | Return | PF | Win | Max DD | Avg W/L streak (max) | Costs |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    for sym in CONFIG["symbols"]:
        for v in CONFIG["variants"]:
            m = runs.get((sym, v, p))
            if not m:
                lines.append(f"| {sym} | {v} | — |")
                continue
            x, e = m["metrics"], extra(m)
            lines.append(f"| {sym} | {v} | {x['trades']} | {e['pm']:.1f} | {e['pd']:.2f} | {x['return_pct']:+.1f}% | "
                         f"{x['profit_factor']:.2f} | {x['win_rate_pct']:.0f}% | {x['max_drawdown_pct']:.1f}% | "
                         f"{e['aw']:.1f}/{e['al']:.1f} ({e['mw']}/{e['ml']}) | {e['cost']:+.0f} |")
    lines.append("")
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
