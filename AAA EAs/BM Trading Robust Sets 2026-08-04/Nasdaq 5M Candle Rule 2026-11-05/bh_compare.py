"""Each Nasdaq 5M version vs buy and hold USTEC, net of spread, commission and swap on both sides, same windows, $10k. Strategy at 1% risk compounding. DD = MT5 equity drawdown relative. -> BH_COMPARE.md"""
import gzip, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline')); import buy_hold  # noqa: E402
V = ['EMA_ATR6_DION', 'EMA_ATR6_DIOFF', 'EMA_P60_DION', 'EMA_P60_DIOFF', 'EMA_FIXED_DION', 'EMA_FIXED_DIOFF', 'EMA_DYN_DIOFF', 'CANDLE_ATR6_DION', 'CANDLE_ATR6_DIOFF', 'CANDLE_P60_DION', 'CANDLE_P60_DIOFF', 'CANDLE_FIXED_DION', 'CANDLE_FIXED_DIOFF', 'CONTROL_ATR6_DIOFF']
out = {}
for w in ('all', 'dev', 'val', 'oos'):
    h = buy_hold.load(H, 'USTEC', w); out[w] = dict(hold=h, rows={})
    for v in V:
        d = H / f'native/nw-USTEC-{v}-{w}'
        if not (d / 'run.json').exists() or not json.loads((d / 'run.json').read_text(encoding='utf-8')).get('ok'): continue
        T = json.loads(gzip.open(d / 'trades.json.gz').read()); net = sum(t['net_profit'] for t in T); costs = sum(t['commission'] + t['swap'] for t in T)
        s = dict(return_pct=round(net / 100, 2), max_dd_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz')); c = buy_hold.compare(s, h); out[w]['rows'][v] = dict(c, trades=len(T), commission_swap_pct=round(costs / 100, 1))
    print(w, 'HOLD', h['return_pct'], 'price', h['price_return_pct'], 'swap', h['swap_pct'], 'dd', h['max_dd_pct'], 'r/dd', round(h['return_pct'] / h['max_dd_pct'], 2))
    for v, c in out[w]['rows'].items(): print('  ', v.ljust(20), c['strategy_return_pct'], 'dd', c['strategy_dd_pct'], 'r/dd', c['strategy_return_dd'], 'n', c['trades'], 'cost', c['commission_swap_pct'], '|', c['verdict'])
(H / 'BH_COMPARE.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
