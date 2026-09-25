"""Summarise the Gold Overnight IVB website-window runs (6m/1y/3y/5y) and compare with the website's
Gold Overnight Value Area cache. Research only; writes WEBSITE_PERIOD_RESULTS.json."""
import json
from collections import defaultdict
from pathlib import Path
from parse_native import parse

ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parents[1] / "EA store" / "data" / "evidence-cache" / "v1" / "products" / "gold-overnight-value-area" / "standard"
out = {}
for key in ("6m", "1y", "3y", "5y"):
    run = ROOT / "native" / f"onvt-XAUUSD-anytime-target1r-{key}-m4-d150"
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    s, tr = parse(run / Path(meta["report"]).name)
    years = defaultdict(float)
    for t in tr:
        years[t["exit"][:4]] += t["net"]
    va = json.loads((CACHE / f"{key}.json").read_text(encoding="utf-8"))
    out[key] = dict(period=f"{meta['start']} to {meta['end_exclusive']} (end exclusive)", ivb=s,
                    ivb_yearly_net_usd={y: round(v, 2) for y, v in sorted(years.items())},
                    ea_summary=meta["ea_summary"], journal_flags=meta["journal_flags"],
                    gold_value_area_website=dict(period=va["period"], **{k: va["stats"].get(k) for k in (
                        "trades", "win_rate_pct", "profit_factor", "return_pct", "max_drawdown_pct",
                        "max_win_streak", "max_loss_streak")}))
(ROOT / "WEBSITE_PERIOD_RESULTS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for key, r in out.items():
    s, v = r["ivb"], r["gold_value_area_website"]
    print(f"{key}: IVB trades {s['trades']} win {s['win_rate_pct']}% PF {s['profit_factor']} ret {s['return_pct']}% "
          f"eqDD {s['equity_dd_rel']} balDD {s['balance_dd_rel']} W{s['max_win_streak']}/L{s['max_loss_streak']} "
          f"comm {s['commission']} swap {s['swap']} q {s['quality']} years {r['ivb_yearly_net_usd']}")
    print(f"     VA  trades {v['trades']} win {round(v['win_rate_pct'],1)}% PF {round(v['profit_factor'],2)} ret {v['return_pct']}% DD {v['max_drawdown_pct']} W{v['max_win_streak']}/L{v['max_loss_streak']}")
