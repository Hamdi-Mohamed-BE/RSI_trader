"""Side-by-side: current claude_eas Nasdaq 5M vs QUANT_LAB-style management (USTEC, 6m/1y/3y/5y to 2026-09-25)."""
from __future__ import annotations

import gzip
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
runs = {}
for f in (ROOT / "native").glob("n5ql-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if m.get("ok"):
        m["trades"] = sorted(json.loads(gzip.decompress((f.parent / "trades.json.gz").read_bytes()).decode("utf-8")),
                             key=lambda t: t["close_time"])
        runs[(m["variant"], m["period"])] = m


def stats(m: dict) -> dict:
    t = m["trades"]
    streaks, cur, n = [], None, 0
    for x in t:
        r = "W" if x["net_profit"] > 0 else "L" if x["net_profit"] < 0 else None
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
    hold = [(datetime.fromisoformat(x["close_time"]) - datetime.fromisoformat(x["open_time"])).total_seconds() / 3600 for x in t]
    losses = [-x["net_profit"] for x in t if x["net_profit"] < 0]
    typical_loss = sorted(losses)[len(losses) // 2] if losses else 0.0
    best = max((x["net_profit"] for x in t), default=0.0)
    return dict(avg_w=sum(w) / len(w) if w else 0, avg_l=sum(lo) / len(lo) if lo else 0, max_w=max(w, default=0),
                max_l=max(lo, default=0), hold=sum(hold) / len(hold) if hold else 0, max_hold=max(hold, default=0),
                overnight=sum(h > 8 for h in hold) / len(hold) * 100 if hold else 0, swap=sum(x["swap"] for x in t),
                best_r=best / typical_loss if typical_loss else 0)


lines = ["# Nasdaq 5M — current claude_eas vs QUANT_LAB-style management", "",
         "USTEC, isolated MT5 tester (Exness-MT5Trial16), $10,000, 1% risk, M5, Model 4 (real ticks from 2026-01), 150 ms delay. "
         "Windows end 2026-09-25 (includes the video week). Same entry rule in every variant; only stop/target/trail/holding differ.", "",
         "| Variant | " + " | ".join(f"{k}: {v['label']}" for k, v in CONFIG["variants"].items()) + " |", ""]
for p in CONFIG["periods"]:
    lines += [f"## {p} ({CONFIG['periods'][p]} → {CONFIG['end_date']})", "",
              "| Variant | Trades | Return | PF | Win | Max DD | Avg W/L streak (max) | Avg hold h (max) | Held >8h | Swap | Best trade (× median loss) |",
              "|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|"]
    for v in CONFIG["variants"]:
        m = runs.get((v, p))
        if not m:
            lines.append(f"| {v} | — |")
            continue
        x, s = m["metrics"], stats(m)
        lines.append(f"| {v} | {x['trades']} | {x['return_pct']:+.2f}% | {x['profit_factor']:.2f} | {x['win_rate_pct']:.1f}% | "
                     f"{x['max_drawdown_pct']:.2f}% | {s['avg_w']:.1f}/{s['avg_l']:.1f} ({s['max_w']}/{s['max_l']}) | "
                     f"{s['hold']:.1f} ({s['max_hold']:.0f}) | {s['overnight']:.0f}% | {s['swap']:+.0f} | {s['best_r']:.1f}× |")
    lines.append("")
par = ROOT / "native" / "PARITY.json"
if par.exists():
    lines += ["## Parity", "", "```", par.read_text(encoding="utf-8"), "```"]
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
