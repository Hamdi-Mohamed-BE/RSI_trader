"""Best 1-Step (Core 9 + P4, 11 EAs) full breakdown (owner 2026-11-11): every EA and the portfolio, from existing native Model-4 ledgers only (no new tester run).

All years: each EA's own standalone native run at 1% ($10k), R = net / 1% of the balance before the trade (Portfolio P7 2026-11-10/p7.py native_rows method):
  Core 9 members (USDJPY, 3 Way Gold breakout = comment '3WG BRK', Sell Nasdaq, EMA3, ORB VP VC, XAU Squeeze, Selective V3, RSI VWAP) = Merged E10 FTMO17 2026-11-05 native
  (2019-01-01 -> 2026-11-01 excl.); Overnight Bias ORB, Gold Band Wave, Nasdaq 5M REPLACE DI OFF = their raw / carry-fix native runs (to 2026-11-10).
Last month: trades OPENED 2026-10-10 -> 2026-11-11 excl. from the 13 native r2m runs (Merge 1Step 60d Search 2026-11-10/native-recent, 100% real ticks), recent2m.ledger.
Portfolio = sum of R (equal risk per trade, no guard, no margin, closed trades) = LEDGER OVERLAY, not a shared-account native run. % = R x 0.5% (non-compounding).
Run: uv run --with numpy python breakdown.py -> BREAKDOWN.json / BREAKDOWN.md"""
import gzip, importlib.util, json, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
sys.path.insert(0, str(B.parent / 'Calyx Research Pipeline'))
import data_split, robustness  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


R2M = load('recent2m', B / 'Merge 1Step 60d Search 2026-11-10/recent2m.py')
LABEL = {'nasdaq-5m-candle-momentum': 'Nasdaq 5M (REPLACE, DI OFF)', 'usdjpy-london-open-momentum': 'USDJPY London', '3-way-gold': '3 Way Gold (breakout)', 'sell-nasdaq-15min': 'Sell Nasdaq 15min',
         'ema3': 'EMA3', 'orb-volume-profile-volume-confirmed': 'ORB VP Volume Confirmed', 'xau-squeeze-momentum-standard': 'XAU Squeeze', 'us100-selective-orb-v3': 'US100 Selective ORB V3',
         'xau-rsi-vwap': 'XAU RSI VWAP', 'overnight-bias-orb': 'Overnight Bias ORB', 'gold-band-wave': 'Gold Band Wave'}
EAS = list(LABEL)
LAST_A, LAST_B = '2026-10-10', '2026-11-11'


def from_trades(path, risk=0.01):
    T = sorted(json.loads(gzip.open(path).read()), key=lambda t: t['close_time']); bal = 1e4; out = []
    for t in T:
        out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (risk * bal))); bal += t['net_profit']
    return out


def all_years():
    M = B / 'Merged E10 FTMO17 2026-11-05'; src = (M / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
    ns = dict(__file__=str(M / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns); ALL = ns['ALL']
    iso = lambda v: v.isoformat() if hasattr(v, 'isoformat') else str(v)  # noqa: E731
    out = {}
    for k in EAS[1:9]:
        rows = ALL[k] if k != '3-way-gold' else [r for r in ALL[k] if r['comment'].startswith('3WG BRK')]
        out[k] = [dict(o=iso(r['o']), c=iso(r['c']), r=r['R']) for r in rows]
    out['nasdaq-5m-candle-momentum'] = from_trades(B / 'Nasdaq 5M Carry Fix 2026-11-09/native/nw-USTEC-REPLACE-all/trades.json.gz')
    out['overnight-bias-orb'] = from_trades(B / 'Video ORB VWAP Ideas Raw 2026-11-09/native/nw-USTEC-ONB-all/trades.json.gz')
    out['gold-band-wave'] = from_trades(B / 'Gold Band Wave Raw 2026-11-10/native/nw-XAUUSD-GBW-all/trades.json.gz')
    return out


def stats(x, a, b):
    x = sorted((r for r in x if a <= r['o'][:10] < b), key=lambda r: r['c']); gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
    eq = pk = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375; tot = sum(r['r'] for r in x)
    return dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / (months * 21), 2), total_r=round(tot, 1), pf=round(gw / gl, 2) if gl else None,
                win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), avg_r=round(tot / len(x), 3) if x else None, closed_dd_r=round(dd, 1),
                worst_day_r=round(min(days.values()), 2) if days else None, best_day_r=round(max(days.values()), 2) if days else None)


def main():
    split = data_split.research_split('2019-01-01', '2026-11-10')
    W = {k: (split[n]['start'], split[n]['end_exclusive']) for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}
    W.update(all=('2019-01-01', '2026-11-10'), last_year=('2025-11-10', '2026-11-10'))
    R = all_years(); port = [r for k in EAS for r in R[k]]
    out = dict(windows=W, last_month=(LAST_A, LAST_B), portfolio={}, eas={}, notes=__doc__)
    out['portfolio']['all'] = {w: stats(port, *v) for w, v in W.items()}
    out['portfolio']['years'] = {str(y): stats(port, f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else '2026-11-10') for y in range(2019, 2027)}
    seq = [r['r'] for r in sorted(port, key=lambda r: r['c'])]; tw = robustness.three_monte_carlo(seq, runs=1000, seed=20261104)
    out['portfolio']['mc'] = dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct'], real_dd_worse_than_pct=tw['reshuffle']['real_drawdown_worse_than_pct'])
    last = {k: [dict(o=x['o'], c=x['c'], r=x['r']) for x in R2M.ledger('3-way-gold#930930101' if k == '3-way-gold' else k) if LAST_A <= x['o'][:10] < LAST_B] for k in EAS}
    lp = [r for k in EAS for r in last[k]]
    out['portfolio']['last_month'] = stats(lp, LAST_A, LAST_B)
    wk = defaultdict(float)
    for r in lp: wk[datetime.fromisoformat(r['c'][:10]).strftime('%G-W%V')] += r['r']
    out['portfolio']['last_month_weeks'] = {k: round(v, 2) for k, v in sorted(wk.items())}
    for k in EAS:
        out['eas'][k] = dict(label=LABEL[k], windows={w: stats(R[k], *v) for w, v in W.items()},
                             years={str(y): stats(R[k], f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else '2026-11-10')['total_r'] for y in range(2019, 2027)},
                             first=min(r['o'] for r in R[k])[:10], last=max(r['o'] for r in R[k])[:10], last_month=stats(last[k], LAST_A, LAST_B))
    (H / 'BREAKDOWN.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    P = out['portfolio']; L = []
    L.append('# Best 1-Step full breakdown (ledger overlay, equal risk per trade, no guard)\n')
    L.append('| Window | Trades | /month | /day | Total R | at 0.5% | PF | Win % | Avg R | Closed DD R | Worst day R |\n|---|---|---|---|---|---|---|---|---|---|---|')
    for w, s in list(P['all'].items()) + [('last month', P['last_month'])]:
        L.append(f"| {w} | {s['trades']} | {s['per_month']} | {s['per_day']} | {s['total_r']} | {s['total_r'] * 0.5:.1f}% | {s['pf']} | {s['win']} | {s['avg_r']} | {s['closed_dd_r']} | {s['worst_day_r']} |")
    L.append('\nYears (R): ' + ', '.join(f"{y} {s['total_r']}" for y, s in P['years'].items()))
    L.append(f"\nMC: resample red {P['mc']['resample_red']}%, randomize red {P['mc']['randomize_red']}%, real DD worse than {P['mc']['real_dd_worse_than_pct']}% of shuffles")
    L.append('\nLast month by week (R): ' + ', '.join(f'{k} {v}' for k, v in P['last_month_weeks'].items()))
    L.append('\n## EAs\n\n| EA | Trades | /month | All R | PF | Win % | DD R | Dev R | Val R | OOS R | Last 12 m R | Last month n | Last month R |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k, e in out['eas'].items():
        a = e['windows']
        L.append(f"| {e['label']} | {a['all']['trades']} | {a['all']['per_month']} | {a['all']['total_r']} | {a['all']['pf']} | {a['all']['win']} | {a['all']['closed_dd_r']} | {a['dev']['total_r']} | {a['val']['total_r']} | {a['oos']['total_r']} | {a['last_year']['total_r']} | {e['last_month']['trades']} | {e['last_month']['total_r']} |")
    L.append('\n## EA years (R)\n\n| EA | ' + ' | '.join(str(y) for y in range(2019, 2027)) + ' |\n|---|' + '---|' * 8)
    for k, e in out['eas'].items(): L.append(f"| {e['label']} | " + ' | '.join(str(round(v, 1)) for v in e['years'].values()) + ' |')
    (H / 'BREAKDOWN.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    main()
