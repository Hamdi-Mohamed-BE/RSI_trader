"""ATR Touch report: per edge/symbol signal vs control on the gate windows, streaks, breadth, ADVANCE.json."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
runs: dict[tuple, dict] = {}
for f in (ROOT / "native").glob("at-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if not m.get("ok"):
        continue
    trades = sorted(json.loads(gzip.decompress((f.parent / "trades.json.gz").read_bytes()).decode("utf-8")),
                    key=lambda t: t["close_time"])
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
    runs[(m["model"], m["symbol"], m["variant"], m["period"])] = m


def cell(m: dict | None, streak: bool = True) -> str:
    if not m:
        return "—"
    x, s = m["metrics"], m["streaks"]
    from datetime import datetime as _dt, timedelta as _td
    a, b = _dt.strptime(m["start"], "%Y.%m.%d").date(), _dt.strptime(m["end_exclusive"], "%Y.%m.%d").date()
    wd = sum(1 for i in range((b - a).days) if (a + _td(days=i)).weekday() < 5)
    out = f"{x['trades']} ({x['trades'] / ((b - a).days / 30.4375):.1f}/mo, {x['trades'] / max(wd, 1):.2f}/day) · {x['return_pct']:+.1f}% · PF {x['profit_factor']:.2f} · win {x['win_rate_pct']:.0f}% · DD {x['max_drawdown_pct']:.1f}%"
    return out + (f" · {s['avg_w']:.1f}/{s['avg_l']:.1f} ({s['max_w']}/{s['max_l']})" if streak else "")


def gate(model: int, sym: str, edge: str) -> list[str]:
    reasons = []
    for p, min_trades in (("3y", 20), ("5y", 30)):
        a, c = runs.get((model, sym, edge, p)), runs.get((model, sym, edge + "c", p))
        if not a or not c:
            return [f"{p} missing"]
        x = a["metrics"]
        if x["return_pct"] <= 0:
            reasons.append(f"{p} not positive")
        if x["profit_factor"] < 1.15:
            reasons.append(f"{p} PF {x['profit_factor']:.2f}")
        if x["trades"] < min_trades:
            reasons.append(f"{p} {x['trades']} trades")
        if x["return_pct"] <= c["metrics"]["return_pct"]:
            reasons.append(f"{p} not above control")
    return reasons


lines = ["# ATR Touch — results", "",
         "Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk to a catastrophe stop (lots rounded up), long only. "
         "Screen = Model 1 (1-minute OHLC); windows 3y (2023-09-01) and 5y (2021-09-01) to 2026-09-01. No optimization.",
         "Cell = trades (per month, per trading day) · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).", ""]
advance = []
for key, edge in CONFIG["edges"].items():
    lines += [f"## {key} — {edge['label']}", f"Evidence: {edge['evidence']}. Control: {edge['control_label']}.", "",
              "| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |", "|---|---|---|---|---|---|"]
    positive_5y = 0
    for sym in edge["symbols"]:
        why = gate(1, sym, key)
        if not why:
            advance.append({"edge": key, "symbol": sym})
        s5 = runs.get((1, sym, key, "5y"))
        positive_5y += bool(s5 and s5["metrics"]["return_pct"] > 0)
        lines.append(f"| {sym} | {cell(runs.get((1, sym, key, '3y')))} | {cell(runs.get((1, sym, key + 'c', '3y')), False)} | "
                     f"{cell(s5)} | {cell(runs.get((1, sym, key + 'c', '5y')), False)} | "
                     f"{'PASS' if not why else 'FAIL: ' + '; '.join(why)} |")
    lines += ["", f"Breadth: {positive_5y}/{len(edge['symbols'])} symbols positive over 5y.", ""]
lines += ["## Advancing to the Model 4 real-tick test", "",
          ", ".join(f"{a['edge']} {a['symbol']}" for a in advance) if advance else "None.", ""]

confirm = sorted({(s, v) for (mdl, s, v, p) in runs if mdl == 4})
if confirm:
    lines += ["## Model 4 real-tick confirmation (all periods)", "",
              "| Edge | Symbol | 6m | 1y | 3y | 5y | Control 3y | Control 5y |", "|---|---|---|---|---|---|---|---|"]
    for s, v in confirm:
        if v.endswith("c"):
            continue
        lines.append(f"| {v} | {s} | " + " | ".join(cell(runs.get((4, s, v, p))) for p in CONFIG["periods"]) + " | "
                     + " | ".join(cell(runs.get((4, s, v + "c", p)), False) for p in ("3y", "5y")) + " |")
(ROOT / "native" / "ADVANCE.json").write_text(json.dumps(advance, indent=1), encoding="utf-8")
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
