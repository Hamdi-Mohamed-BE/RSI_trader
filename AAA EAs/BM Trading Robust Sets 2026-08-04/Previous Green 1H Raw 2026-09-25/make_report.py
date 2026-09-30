"""Side-by-side tables + streaks + pre-registered gate for the Previous-Green 1H raw study."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
GATE = CONFIG["gate"]
runs: dict[tuple, dict] = {}
for f in (ROOT / "native").glob("pg1h-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if not m.get("ok"):
        continue
    trades = sorted(json.loads(gzip.decompress((f.parent / "trades.json.gz").read_bytes()).decode("utf-8")), key=lambda t: t["close_time"])
    streaks, cur, n = [], None, 0
    for t in trades:
        r = "W" if t["net_profit"] > 0 else "L" if t["net_profit"] < 0 else None
        if r is None:
            continue
        if r == cur:
            n += 1
        else:
            if cur:
                streaks.append((cur, n))
            cur, n = r, 1
    if cur:
        streaks.append((cur, n))
    w = [k for s, k in streaks if s == "W"]
    lo = [k for s, k in streaks if s == "L"]
    m["streaks"] = dict(avg_w=sum(w) / len(w) if w else 0.0, avg_l=sum(lo) / len(lo) if lo else 0.0,
                        max_w=max(w, default=0), max_l=max(lo, default=0))
    runs[(m["symbol"], m["variant"], m["period"])] = m


def cell(m: dict | None) -> str:
    if not m:
        return "—"
    x, s = m["metrics"], m["streaks"]
    return (f"{x['trades']} · {x['return_pct']:+.1f}% · PF {x['profit_factor']:.2f} · win {x['win_rate_pct']:.0f}% · "
            f"DD {x['max_drawdown_pct']:.1f}% · {s['avg_w']:.1f}/{s['avg_l']:.1f} ({s['max_w']}/{s['max_l']})")


lines = ["# Previous-Green 1H — raw native results", "",
         "Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up), H1, Model 4 (real ticks from 2026-01, "
         "bars-generated before), 150 ms delay; windows end 2026-09-01. No optimization.",
         "Cell = trades · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).", ""]
for sym in CONFIG["symbols"]:
    lines += [f"## {sym}", "", "| Period | " + " | ".join(f"{k} — {v['label']}" for k, v in CONFIG["variants"].items()) + " |",
              "|---|" + "---|" * len(CONFIG["variants"])]
    for p in CONFIG["periods"]:
        lines.append(f"| {p} | " + " | ".join(cell(runs.get((sym, v, p))) for v in CONFIG["variants"]) + " |")
    lines += ["", f"Colour-blind controls ({', '.join(CONFIG['control_periods'])}):", "",
              "| Period | " + " | ".join(f"{k} (control for {c['of']})" for k, c in CONFIG["controls"].items()) + " |",
              "|---|" + "---|" * len(CONFIG["controls"])]
    for p in CONFIG["control_periods"]:
        lines.append(f"| {p} | " + " | ".join(cell(runs.get((sym, c, p))) for c in CONFIG["controls"]) + " |")
    lines.append("")

lines += ["## Pre-registered gate (step 4)", "",
          f"Pass = positive on 3y and 5y, PF ≥ {GATE['min_profit_factor_3y_5y']} on 3y and 5y, ≥ {GATE['min_trades_per_window']} "
          "trades per window, and higher return than its colour-blind control on 3y and 5y.", "",
          "| Symbol | Variant | 3y | 5y | Control 3y | Control 5y | Result |", "|---|---|---|---|---|---|---|"]
passed = []
for sym in CONFIG["symbols"]:
    for v in CONFIG["variants"]:
        ctrl = next(k for k, c in CONFIG["controls"].items() if c["of"] == v)
        a, b = runs.get((sym, v, "3y")), runs.get((sym, v, "5y"))
        ca, cb = runs.get((sym, ctrl, "3y")), runs.get((sym, ctrl, "5y"))
        if not (a and b and ca and cb):
            lines.append(f"| {sym} | {v} | incomplete | | | | — |")
            continue
        reasons = []
        for tag, r, c in (("3y", a, ca), ("5y", b, cb)):
            x = r["metrics"]
            if x["return_pct"] <= 0:
                reasons.append(f"{tag} not positive")
            if x["profit_factor"] < GATE["min_profit_factor_3y_5y"]:
                reasons.append(f"{tag} PF {x['profit_factor']:.2f}")
            if x["return_pct"] <= c["metrics"]["return_pct"]:
                reasons.append(f"{tag} not above control")
        for p in CONFIG["periods"]:
            r = runs.get((sym, v, p))
            if r and r["metrics"]["trades"] < GATE["min_trades_per_window"]:
                reasons.append(f"{p} only {r['metrics']['trades']} trades")
        ok = not reasons
        if ok:
            passed.append(f"{sym} {v}")
        f = lambda r: f"{r['metrics']['return_pct']:+.1f}% PF {r['metrics']['profit_factor']:.2f}"
        lines.append(f"| {sym} | {v} | {f(a)} | {f(b)} | {f(ca)} | {f(cb)} | {'PASS' if ok else 'FAIL: ' + '; '.join(reasons)} |")
lines += ["", f"Passed: {', '.join(passed) if passed else 'none'}"]
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
