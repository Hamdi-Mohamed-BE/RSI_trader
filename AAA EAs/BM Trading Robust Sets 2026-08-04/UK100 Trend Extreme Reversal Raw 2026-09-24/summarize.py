"""Summarise the UK 100 trend + extreme reversal raw runs.

Each combination has ONE native MT5 5y run (2021-09-19 -> 2026-09-19 exclusive). The 5y row is the native report.
6m / 1y / 3y rows are slices of that native ledger, recompounded from $10,000 using each trade's return on the
balance before it (net / (balance_after - net)). They are native trades, not separate native runs per window.
Writes RESULTS.json and prints a ranked table.
"""
import json
from pathlib import Path
from parse_native import parse

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))


def window(trades, start):
    sel = [t for t in trades if t["entry"][:10] >= start.replace("-", ".")]
    bal = peak = 10000.0
    dd = gp = gl = 0.0
    wins = w = l = bw = bl = 0
    for t in sel:
        pnl = bal * t["net"] / (t["bal_after"] - t["net"])
        bal += pnl
        peak = max(peak, bal)
        dd = max(dd, (peak - bal) / peak * 100)
        if pnl > 0:
            gp += pnl; wins += 1; w += 1; l = 0
        else:
            gl -= pnl; l += 1; w = 0
        bw = max(bw, w); bl = max(bl, l)
    n = len(sel)
    return dict(trades=n, win_pct=round(100 * wins / n, 1) if n else None, pf=round(gp / gl, 2) if gl else None,
                return_pct=round((bal / 10000 - 1) * 100, 1), balance_dd_pct=round(dd, 1),
                best_win_streak=bw, worst_loss_streak=bl)


def main():
    out = {}
    for run in sorted((ROOT / "native").glob("ter-*-5y-m4-d150/run.json")):
        meta = json.loads(run.read_text(encoding="utf-8"))
        s, tr = parse(run.parent / Path(meta["report"]).name)
        row = dict(tf=meta["tf"], trend=meta["trend"], extreme=meta["extreme"], exit=meta["exit"],
                   journal_flags=meta["journal_flags"], ea_summary=meta["ea_summary"],
                   native_5y=dict(trades=s["trades"], win_pct=s["win_rate_pct"], pf=s["profit_factor"],
                                  return_pct=s["return_pct"], equity_dd=s["equity_dd_rel"], balance_dd=s["balance_dd_rel"],
                                  best_win_streak=s["max_win_streak"], worst_loss_streak=s["max_loss_streak"],
                                  commission=s["commission"], swap=s["swap"], quality=s["quality"]),
                   windows={k: window(tr, v) for k, v in CFG["website_windows"].items() if k != "5y"})
        out[meta["name"]] = row
    (ROOT / "RESULTS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    ranked = sorted(out.items(), key=lambda kv: -(kv[1]["native_5y"]["pf"] or 0))
    print(f"{len(out)} combinations")
    for k, r in ranked:
        n = r["native_5y"]; w = r["windows"]
        print(f"{k:<34} 5y n{n['trades']:>4} win {n['win_pct']:>5}% PF {n['pf']:>5} ret {n['return_pct']:>7}% eqDD {n['equity_dd']:<18} "
              f"| 3y PF {w['3y']['pf']} {w['3y']['return_pct']}% | 1y PF {w['1y']['pf']} {w['1y']['return_pct']}% n{w['1y']['trades']} "
              f"| 6m PF {w['6m']['pf']} {w['6m']['return_pct']}% | W{n['best_win_streak']}/L{n['worst_loss_streak']}")


if __name__ == "__main__":
    main()
