"""Side-by-side summary of the cross-asset Nasdaq 5M Candle Momentum runs (native MT5, last year)."""
import json
from datetime import datetime
from pathlib import Path
from parse_native import parse

ROOT = Path(__file__).resolve().parent
out = {}
for run in sorted((ROOT / "native").glob("n5x-*/run.json")):
    meta = json.loads(run.read_text(encoding="utf-8"))
    s, tr = parse(run.parent / Path(meta["report"]).name)
    overnight = [t for t in tr if t["exit"][:10] != t["entry"][:10]]
    same_day = [t["net"] for t in tr if t["exit"][:10] == t["entry"][:10]]
    gp = sum(v for v in same_day if v > 0); gl = -sum(v for v in same_day if v < 0)
    hold = max(((datetime.strptime(t["exit"], "%Y.%m.%d %H:%M:%S") - datetime.strptime(t["entry"], "%Y.%m.%d %H:%M:%S")).total_seconds() / 3600 for t in tr), default=0)
    s.update(symbol=meta["symbol"], journal_flags=meta["journal_flags"], overnight_trades=len(overnight),
             overnight_net=round(sum(t["net"] for t in overnight), 2), same_day_pf=round(gp / gl, 2) if gl else None,
             max_hold_hours=round(hold, 1))
    out[meta["symbol"]] = s
(ROOT / "RESULTS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
order = ["USTEC", "XAUUSD", "BTCUSD", "UK100", "XAGUSD"]
for k in order:
    s = out[k]
    print(f"{k:<7} n {s['trades']:>3} win {s['win_rate_pct']:>5}% PF {s['profit_factor']} ret {s['return_pct']:>7}% net {s['net_profit']} "
          f"eqDD {s['equity_dd_rel']} balDD {s['balance_dd_rel']} W{s['max_win_streak']}/L{s['max_loss_streak']} avgW {s['avg_win']} avgL {s['avg_loss']} "
          f"long {s['long_trades']} short {s['short_trades']} comm {s['commission']} swap {s['swap']} exits {s['exits']} "
          f"overnight {s['overnight_trades']} (${s['overnight_net']}) sameDayPF {s['same_day_pf']} maxHold {s['max_hold_hours']}h q {s['quality']}")
