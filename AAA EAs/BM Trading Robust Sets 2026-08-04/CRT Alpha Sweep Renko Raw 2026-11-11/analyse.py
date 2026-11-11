"""CRT Alpha raw study analysis: per run, R = net / 1% of the balance before the trade, counted only while the balance is >= $2,000 (below that the
broker minimum lot (0.05) oversizes the 1% risk). -> RESULTS.json / RESULTS.md"""
import gzip, json
from datetime import datetime
from pathlib import Path
H = Path(__file__).resolve().parent; N = H / 'native'
cfg = json.loads((H / 'run-config.json').read_text(encoding='utf-8')); END = '2026-11-11'
out = {}
for d in sorted(N.glob('nw-USTEC-*')):
    if d.name.endswith('smoke') or not (d / 'trades.json.gz').exists(): continue
    T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); run = json.loads((d / 'run.json').read_text(encoding='utf-8'))
    bal = 1e4; rs = []; wipe = None; costs = 0.0
    for t in T:
        if bal < 2000: wipe = wipe or t['close_time'][:10]; break
        rs.append(t['net_profit'] / (0.01 * bal)); costs += t['commission'] + t['swap']; bal += t['net_profit']
    start = run['start'].replace('.', '-'); last = T[len(rs) - 1]['close_time'][:10] if rs else start
    months = max(0.5, (datetime.fromisoformat(last) - datetime.fromisoformat(start)).days / 30.4375)
    gw = sum(r for r in rs if r > 0); gl = -sum(r for r in rs if r < 0); m = run['metrics'] if isinstance(run['metrics'], dict) else eval(run['metrics'])
    out[d.name] = dict(window=f"{start}..{END}", native_return=m['return_pct'], native_pf=m['profit_factor'], native_trades=m['trades'], native_dd=m['max_drawdown_pct'], quality=m.get('history_quality'),
                       counted_trades=len(rs), counted_until=last, balance_below_2k=wipe, per_month=round(len(rs) / months, 1), per_day=round(len(rs) / months / 21, 2),
                       win=round(100 * sum(r > 0 for r in rs) / max(1, len(rs)), 1), pf_r=round(gw / gl, 3) if gl else None, avg_r=round(sum(rs) / max(1, len(rs)), 3), total_r=round(sum(rs), 1),
                       costs_usd=round(costs, 2))
(H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
L = ['| Run | Native return | PF | Trades | Equity DD | Trades counted (balance >= $2k) | Until | /month | /day | Win % | PF (R) | Avg R | Total R |', '|' + '---|' * 13]
for k, v in out.items():
    L.append(f"| {k[9:]} | {v['native_return']}% | {v['native_pf']} | {v['native_trades']} | {v['native_dd']}% | {v['counted_trades']} | {v['counted_until']} | {v['per_month']} | {v['per_day']} | {v['win']} | {v['pf_r']} | {v['avg_r']} | {v['total_r']} |")
(H / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
