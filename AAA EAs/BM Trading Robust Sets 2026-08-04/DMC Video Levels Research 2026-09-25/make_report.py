"""Build side-by-side tables (BASE vs VIDEO per DMC config / symbol / period, plus 5y ablation) from native/*/run.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
PERIODS = list(CONFIG["periods"])
runs = {}
for f in (ROOT / "native").glob("dmcv-*/run.json"):
    m = json.loads(f.read_text(encoding="utf-8"))
    if m.get("ok"):
        runs[(m["config"], m["symbol"], m["variant"], m["period"])] = m


def cell(m: dict | None) -> str:
    if not m:
        return "— | — | — | — | —"
    x = m["metrics"]
    return f"{x['return_pct']:+.2f}% | {x['profit_factor']:.2f} | {x['trades']} | {x['win_rate_pct']:.1f}% | {x['max_drawdown_pct']:.2f}%"


def symbols_for(cfg: dict) -> list[str]:
    return [cfg["native_symbol"]] + [s for s in CONFIG["symbols"] if s != cfg["native_symbol"]]


lines = ["# DMC video-levels study — side-by-side results", "",
         "Native MT5 (isolated tester, Exness-MT5Trial16), $10,000, 1% risk, H1, Model 4 (real ticks from 2026-01, "
         "bars-generated before), 150 ms delay. Windows end 2026-09-01 (same as the website).",
         "BASE = current production rules. VIDEO = first test of the level only + take profit at the first untested "
         "level in the trade direction (capped at the SET R, skip if < 0.25R). DD = max equity drawdown.",
         "Off-native symbols for CUR/FRX use a 1.5×H1-ATR stop instead of the fixed XAU dollar stop.", ""]
lines.insert(-2, "UNTESTED = first test of the level only (added after the 5y ablation; see REPORT.md on selection bias).")


def short(m: dict | None) -> str:
    if not m:
        return "—"
    x = m["metrics"]
    return (f"{x['return_pct']:+.2f}% · PF {x['profit_factor']:.2f} · n {x['trades']} · "
            f"win {x['win_rate_pct']:.0f}% · DD {x['max_drawdown_pct']:.2f}%")


score = {"VIDEO": [0, 0], "UNTESTED": [0, 0]}
for key, cfg in CONFIG["configs"].items():
    lines += [f"## {key} — {cfg['label']}", ""]
    for sym in symbols_for(cfg):
        tag = " (native SET)" if sym == cfg["native_symbol"] else " (portable)"
        lines += [f"### {sym}{tag}", "",
                  "| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |",
                  "|---|---|---|---|---:|---:|"]
        for p in PERIODS:
            b = runs.get((key, sym, "BASE", p))
            deltas = []
            for var in ("VIDEO", "UNTESTED"):
                v = runs.get((key, sym, var, p))
                if b and v:
                    d = v["metrics"]["return_pct"] - b["metrics"]["return_pct"]
                    score[var][0] += d > 0
                    score[var][1] += 1
                    deltas.append(f"{d:+.2f} pp")
                else:
                    deltas.append("")
            lines.append(f"| {p} | {short(b)} | {short(runs.get((key, sym, 'VIDEO', p)))} | "
                         f"{short(runs.get((key, sym, 'UNTESTED', p)))} | {deltas[0]} | {deltas[1]} |")
        lines.append("")
lines += [f"Return beat BASE: VIDEO {score['VIDEO'][0]}/{score['VIDEO'][1]} cells, "
          f"UNTESTED {score['UNTESTED'][0]}/{score['UNTESTED'][1]} cells.", "",
          "## 5-year ablation (each video rule alone)", "",
          "| Config | Symbol | BASE | UNTESTED | TARGET | VIDEO |", "|---|---|---|---|---|---|"]
for key, cfg in CONFIG["configs"].items():
    for sym in symbols_for(cfg):
        row = []
        for var in ("BASE", "UNTESTED", "TARGET", "VIDEO"):
            m = runs.get((key, sym, var, "5y"))
            row.append(f"{m['metrics']['return_pct']:+.1f}% PF {m['metrics']['profit_factor']:.2f} n={m['metrics']['trades']} DD {m['metrics']['max_drawdown_pct']:.1f}%" if m else "—")
        lines.append(f"| {key} | {sym} | " + " | ".join(row) + " |")
(ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
