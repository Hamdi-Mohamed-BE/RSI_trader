"""Score the Gold Overnight IVB revision candidates on the development and holdout windows.

Each candidate has ONE native 5y run (2021-09-19 -> 2026-09-19). Window metrics are derived from that native
ledger by recompounding each trade's return on the balance before it (net / (balance_after - net)), starting
at $10,000. This is a slice of native trades, not a separate native run per window.
Writes REVISION_RESULTS.json.
"""
import json
from pathlib import Path
from parse_native import parse

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))["revision"]


def window(trades, start, end):
    sel = [t for t in trades if start.replace("-", ".") <= t["entry"][:10] < end.replace("-", ".")]
    bal = peak = 10000.0
    dd = gp = gl = 0.0
    wins = streak = best_w = 0
    lstreak = worst_l = 0
    for t in sel:
        r = t["net"] / (t["bal_after"] - t["net"])
        pnl = bal * r
        bal += pnl
        peak = max(peak, bal)
        dd = max(dd, (peak - bal) / peak * 100)
        if pnl > 0:
            gp += pnl; wins += 1; streak += 1; lstreak = 0
        else:
            gl -= pnl; lstreak += 1; streak = 0
        best_w = max(best_w, streak); worst_l = max(worst_l, lstreak)
    n = len(sel)
    return dict(trades=n, win_pct=round(100 * wins / n, 1) if n else 0, pf=round(gp / gl, 2) if gl else None,
                return_pct=round((bal / 10000 - 1) * 100, 1), balance_dd_pct=round(dd, 1),
                best_win_streak=best_w, worst_loss_streak=worst_l)


out = {}
ledgers = {}
for name in CFG["candidates"]:
    run = ROOT / "native" / f"onvt-IVB-{name}-5y-m4-d150"
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    s, tr = parse(run / Path(meta["report"]).name)
    ledgers[name] = tr
    out[name] = dict(native_5y=dict(trades=s["trades"], win_pct=s["win_rate_pct"], pf=s["profit_factor"],
                                    return_pct=s["return_pct"], equity_dd=s["equity_dd_rel"], balance_dd=s["balance_dd_rel"]),
                     development=window(tr, *CFG["development"]), holdout=window(tr, *CFG["holdout"]),
                     ea_summary=meta["ea_summary"])
old = ROOT / "native" / "onvt-XAUUSD-anytime-target1r-5y-m4-d150"
_, ref = parse(old / json.loads((old / "run.json").read_text(encoding="utf-8"))["report"].split("\\")[-1])
par = ledgers["R0-parity"]
out["parity_vs_v110"] = dict(v110_trades=len(ref), v120_trades=len(par), identical=len(ref) == len(par) and all(
    (a["entry"], a["exit"], round(a["net"], 2)) == (b["entry"], b["exit"], round(b["net"], 2)) for a, b in zip(ref, par)))
base_dev = out["R0-parity"]["development"]["trades"]
eligible = [(k, v) for k, v in out.items() if k.startswith("R") and k != "R0-parity"
            and v["development"]["trades"] >= 0.4 * base_dev and v["development"]["pf"] is not None]
eligible.sort(key=lambda kv: (-kv[1]["development"]["pf"], kv[1]["development"]["balance_dd_pct"]))
out["selection"] = dict(rule=CFG["selection_rule"], unfiltered_dev_trades=base_dev,
                        eligible=[k for k, _ in eligible], selected=eligible[0][0] if eligible else None)
(ROOT / "REVISION_RESULTS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("parity", out["parity_vs_v110"])
for k, v in out.items():
    if not k.startswith("R"):
        continue
    d, h, n = v["development"], v["holdout"], v["native_5y"]
    print(f"{k:<16} DEV n{d['trades']:>4} win {d['win_pct']:>4}% PF {d['pf']} ret {d['return_pct']:>6}% dd {d['balance_dd_pct']:>5}% W{d['best_win_streak']}/L{d['worst_loss_streak']} | "
          f"HOLD n{h['trades']:>3} win {h['win_pct']:>4}% PF {h['pf']} ret {h['return_pct']:>6}% dd {h['balance_dd_pct']:>5}% W{h['best_win_streak']}/L{h['worst_loss_streak']} | "
          f"5y native PF {n['pf']} ret {n['return_pct']}% eqDD {n['equity_dd']}")
print("selection", out["selection"])
