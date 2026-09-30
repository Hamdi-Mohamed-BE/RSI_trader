"""3 Way Volume Profile — standard raw-test report: full metric table per way/asset, balance graph, survivor list.

Metrics (per symbol x way, last year):
  Return %, PF, win rate, trades, trades/month and /trading day (Mon-Fri), max balance DD % and max equity DD %
  (native MT5 report), consistency = profitable calendar months / months in the window, avg (max) win and loss streak,
  Sharpe = annualised daily Sharpe of closed-trade P/L (daily return = day P/L / balance at start of day,
  all calendar days incl. zero days, x sqrt(365)).
"""
from __future__ import annotations

import csv
import gzip
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
RULE = dict(min_pf=1.15, min_trades=30, min_consistency=50.0, max_equity_dd=20.0)
runs: dict[tuple, dict] = {}
for f in (ROOT / "native").glob("3wvp-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if m.get("ok"):
        m["trades"] = sorted(json.loads(gzip.decompress((f.parent / "trades.json.gz").read_bytes()).decode("utf-8")),
                             key=lambda t: t["close_time"])
        runs[(m["symbol"], m["variant"])] = m


def metrics(m: dict) -> dict:
    x = m["metrics"]
    a = datetime.strptime(m["start"], "%Y.%m.%d").date()
    b = datetime.strptime(m["end_exclusive"], "%Y.%m.%d").date()
    days = (b - a).days
    weekdays = sum(1 for i in range(days) if (a + timedelta(days=i)).weekday() < 5)
    t = m["trades"]
    # streaks
    st, cur, k = [], None, 0
    for z in t:
        r = "W" if z["net_profit"] > 0 else "L" if z["net_profit"] < 0 else None
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
    # consistency: profitable calendar months over months in the window
    month_pl = defaultdict(float)
    for z in t:
        month_pl[z["close_time"][:7]] += z["net_profit"]
    months = []
    d = date(a.year, a.month, 1)
    while d < b:
        months.append(d.strftime("%Y-%m"))
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    profitable = sum(1 for mo in months if month_pl.get(mo, 0.0) > 0)
    # daily Sharpe from closed P/L
    day_pl = defaultdict(float)
    for z in t:
        day_pl[z["close_time"][:10]] += z["net_profit"]
    bal, rets = float(x["initial_balance"]), []
    for i in range(days):
        key = (a + timedelta(days=i)).isoformat()
        pl = day_pl.get(key, 0.0)
        rets.append(pl / bal if bal > 0 else 0.0)
        bal += pl
    mean = sum(rets) / len(rets) if rets else 0.0
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    sharpe = mean / sd * math.sqrt(365) if sd > 0 else 0.0
    return dict(trades=x["trades"], per_month=x["trades"] / (days / 30.4375), per_day=x["trades"] / max(weekdays, 1),
                ret=x["return_pct"], pf=x["profit_factor"], win=x["win_rate_pct"],
                consistency=profitable / len(months) * 100 if months else 0.0, months=f"{profitable}/{len(months)}",
                aw=sum(w) / len(w) if w else 0.0, al=sum(lo) / len(lo) if lo else 0.0, mw=max(w, default=0), ml=max(lo, default=0),
                sharpe=sharpe, bal_dd=x.get("balance_dd_pct", 0.0), eq_dd=x["max_drawdown_pct"])


def verdict(s: dict) -> str:
    fails = []
    if s["ret"] <= 0:
        fails.append("return ≤ 0")
    if s["pf"] < RULE["min_pf"]:
        fails.append(f"PF {s['pf']:.2f}")
    if s["trades"] < RULE["min_trades"]:
        fails.append(f"{s['trades']} trades")
    if s["consistency"] < RULE["min_consistency"]:
        fails.append(f"consistency {s['consistency']:.0f}%")
    if s["eq_dd"] > RULE["max_equity_dd"]:
        fails.append(f"equity DD {s['eq_dd']:.1f}%")
    if not fails:
        return "SURVIVES"
    if s["ret"] > 0 and s["pf"] >= 1.05:
        return "near miss: " + "; ".join(fails)
    return "fail: " + "; ".join(fails)


rows, lines = [], ["# 3 Way Volume Profile — raw results (M15, last year)", "",
                   f"Window {CONFIG['periods']['1y']} → {CONFIG['end_date']} (end exclusive). Isolated MT5 tester, Exness-MT5Trial16, "
                   "$10,000, 1% risk, Model 4 (real ticks from 2026-01; bars-generated before), 150 ms delay. Raw rules, no tuning.",
                   "Consistency = profitable months / months in window. Sharpe = annualised daily Sharpe of closed P/L. "
                   "Streaks = average (max). Balance DD and equity DD from the native MT5 report.", "",
                   f"Survivor rule (fixed before testing): return > 0, PF ≥ {RULE['min_pf']}, ≥ {RULE['min_trades']} trades, "
                   f"consistency ≥ {RULE['min_consistency']:.0f}%, equity DD ≤ {RULE['max_equity_dd']:.0f}%.", ""]
for v, spec in CONFIG["variants"].items():
    lines += [f"## {spec['label']}", "",
              "| Asset | Trades | /month | /day | Return | PF | Win | Consistency | Avg win/loss streak (max) | Sharpe | Max balance DD | Max equity DD | Verdict |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|"]
    for sym in CONFIG["symbols"]:
        m = runs.get((sym, v))
        if not m:
            lines.append(f"| {sym} | — |")
            continue
        s = metrics(m)
        vd = verdict(s)
        rows.append({"way": v, "asset": sym, **{k: (round(val, 3) if isinstance(val, float) else val) for k, val in s.items()}, "verdict": vd})
        lines.append(f"| {sym} | {s['trades']} | {s['per_month']:.1f} | {s['per_day']:.2f} | {s['ret']:+.1f}% | {s['pf']:.2f} | "
                     f"{s['win']:.0f}% | {s['consistency']:.0f}% ({s['months']}) | {s['aw']:.1f}/{s['al']:.1f} ({s['mw']}/{s['ml']}) | "
                     f"{s['sharpe']:.2f} | {s['bal_dd']:.1f}% | {s['eq_dd']:.1f}% | {vd} |")
    lines.append("")
surv = [r for r in rows if r["verdict"] == "SURVIVES"]
near = [r for r in rows if r["verdict"].startswith("near")]
lines += ["## Survivors for the optimization stage", "",
          ", ".join(f"{r['asset']} {r['way']}" for r in surv) if surv else "None.", "",
          "Near misses: " + (", ".join(f"{r['asset']} {r['way']} ({r['verdict'][11:]})" for r in near) if near else "none"), "",
          "Balance graph: `balance_curves.png` (closed-trade balance per asset, all four ways)."]
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
if rows:
    with (ROOT / "RESULTS.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

# ---- balance graph: small multiples, one panel per asset, 4 series (validated palette slots 1-4) ----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

SERIES = [("ALL", "3 Way combined", "#2a78d6", 2.4), ("POC", "POC bounce", "#eb6834", 1.6),
          ("REV", "VA reversal", "#1baf7a", 1.6), ("BRK", "VA breakout", "#eda100", 1.6)]
SURFACE, TEXT, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
fig, axes = plt.subplots(2, 4, figsize=(20, 9), sharex=True)
fig.patch.set_facecolor(SURFACE)
start = datetime.strptime(CONFIG["periods"]["1y"], "%Y.%m.%d")
for ax, sym in zip(axes.flat, CONFIG["symbols"]):
    ax.set_facecolor(SURFACE)
    ax.axhline(10000, color=MUTED, lw=0.8, ls=(0, (4, 3)), zorder=1)
    for key, label, color, lw in SERIES:
        m = runs.get((sym, key))
        if not m:
            continue
        xs, ys, bal = [start], [10000.0], 10000.0
        for z in m["trades"]:
            bal += z["net_profit"]
            xs.append(datetime.fromisoformat(z["close_time"]))
            ys.append(bal)
        ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=3 if key == "ALL" else 2)
        ax.annotate(f"{(ys[-1] / 10000 - 1) * 100:+.0f}%", xy=(xs[-1], ys[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=TEXT)
    ax.set_title(sym, fontsize=12, color=TEXT, loc="left", fontweight="bold")
    ax.grid(axis="y", color=GRID, lw=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v / 1000:.1f}k"))
    ax.margins(x=0.12)
handles = [plt.Line2D([0], [0], color=c, lw=w) for _, _, c, w in SERIES]
fig.legend(handles, [lab for _, lab, _, _ in SERIES], loc="upper center", ncol=4, frameon=False, fontsize=11,
           labelcolor=TEXT, bbox_to_anchor=(0.5, 0.955))
fig.suptitle("3 Way Volume Profile — closed-trade balance, M15, last year ($10,000 start, 1% risk)", fontsize=15,
             color=TEXT, x=0.012, ha="left", y=0.995)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(ROOT / "balance_curves.png", dpi=110, facecolor=SURFACE)
print("\n".join(lines))
