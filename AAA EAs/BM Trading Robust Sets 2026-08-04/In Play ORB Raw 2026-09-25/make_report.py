"""In-play ORB report: screen (Model 1, 3y/5y) vs random-selection controls, gate, ADVANCE.json, confirmation tables,
trades per symbol, trades per month / per trading day, streaks."""
from __future__ import annotations

import gzip
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
GATE = CONFIG["gate"]
runs: dict[tuple, dict] = {}
for f in (ROOT / "native").glob("ip-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if not m.get("ok"):
        continue
    m["trades"] = sorted(json.loads(gzip.decompress((f.parent / "trades.json.gz").read_bytes()).decode("utf-8")),
                         key=lambda t: t["close_time"])
    runs[(m["model"], m["variant"], m["period"])] = m


def extra(m: dict) -> dict:
    a = datetime.strptime(m["start"], "%Y.%m.%d").date()
    b = datetime.strptime(m["end_exclusive"], "%Y.%m.%d").date()
    wd = sum(1 for i in range((b - a).days) if (a + timedelta(days=i)).weekday() < 5)
    n = m["metrics"]["trades"]
    st, cur, k = [], None, 0
    for x in m["trades"]:
        r = "W" if x["net_profit"] > 0 else "L" if x["net_profit"] < 0 else None
        if r is None:
            continue
        if r == cur:
            k += 1
        else:
            if cur:
                st.append((cur, k))
            cur, k = r, 1
    if cur:
        st.append((cur, k))
    w = [q for s, q in st if s == "W"]
    lo = [q for s, q in st if s == "L"]
    return dict(pm=n / ((b - a).days / 30.4375), pd=n / max(wd, 1), aw=sum(w) / len(w) if w else 0,
                al=sum(lo) / len(lo) if lo else 0, mw=max(w, default=0), ml=max(lo, default=0),
                by_symbol=Counter(x["symbol"] for x in m["trades"]))


def cell(m: dict | None) -> str:
    if not m:
        return "—"
    x, e = m["metrics"], extra(m)
    return (f"{x['trades']} ({e['pm']:.1f}/mo, {e['pd']:.2f}/day) · {x['return_pct']:+.1f}% · PF {x['profit_factor']:.2f} · "
            f"win {x['win_rate_pct']:.0f}% · DD {x['max_drawdown_pct']:.1f}% · {e['aw']:.1f}/{e['al']:.1f} ({e['mw']}/{e['ml']})")


def control_of(v: str) -> str:
    return next(k for k, c in CONFIG["controls"].items() if c["of"] == v)


lines = ["# In-play ORB — raw native results", "",
         "Isolated MT5 tester (Exness-MT5Trial16), $10,000, 1% risk per trade, M5, 150 ms delay; windows end 2026-09-25. "
         "Screen = Model 1 (1-minute OHLC) on 3y/5y; confirmation = Model 4 (real ticks from 2026-01).",
         "Cell = trades (per month, per trading day Mon-Fri) · return · PF · win · max equity DD · avg win/loss streak (max).", "",
         "## Screen (Model 1)", "", "| Variant | 3y | 3y control (random symbols) | 5y | 5y control | Gate |", "|---|---|---|---|---|---|"]
advance = []
for v, spec in CONFIG["variants"].items():
    c = control_of(v)
    reasons = []
    for p in ("3y", "5y"):
        a, b = runs.get((1, v, p)), runs.get((1, c, p))
        if not a or not b:
            reasons.append(f"{p} missing")
            continue
        x = a["metrics"]
        if x["return_pct"] <= 0:
            reasons.append(f"{p} not positive")
        if x["profit_factor"] < GATE["min_profit_factor_3y_5y"]:
            reasons.append(f"{p} PF {x['profit_factor']:.2f}")
        if x["trades"] < GATE["min_trades_per_window"]:
            reasons.append(f"{p} {x['trades']} trades")
        if x["return_pct"] <= b["metrics"]["return_pct"]:
            reasons.append(f"{p} not above control")
    if not reasons:
        advance.append(v)
    lines.append(f"| {v}: {spec['label']} | {cell(runs.get((1, v, '3y')))} | {cell(runs.get((1, c, '3y')))} | "
                 f"{cell(runs.get((1, v, '5y')))} | {cell(runs.get((1, c, '5y')))} | {'PASS' if not reasons else 'FAIL: ' + '; '.join(reasons)} |")
lines += ["", f"Advancing to Model 4: {', '.join(advance) if advance else 'none'}", ""]
(ROOT / "native" / "ADVANCE.json").write_text(json.dumps(advance), encoding="utf-8")

conf = sorted({v for (mdl, v, p) in runs if mdl == 4 and v in CONFIG["variants"]})
if conf:
    lines += ["## Model 4 real-tick confirmation", "", "| Variant | 6m | 1y | 3y | 5y | Control 3y | Control 5y |", "|---|---|---|---|---|---|---|"]
    for v in conf:
        c = control_of(v)
        lines.append(f"| {v} | " + " | ".join(cell(runs.get((4, v, p))) for p in CONFIG["periods"]) + " | "
                     + " | ".join(cell(runs.get((4, c, p))) for p in ("3y", "5y")) + " |")
    lines += ["", "Trades per symbol (Model 4, 5y):", ""]
    for v in conf:
        m = runs.get((4, v, "5y"))
        if m:
            lines.append(f"- {v}: " + ", ".join(f"{s} {n}" for s, n in extra(m)["by_symbol"].most_common()))
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
