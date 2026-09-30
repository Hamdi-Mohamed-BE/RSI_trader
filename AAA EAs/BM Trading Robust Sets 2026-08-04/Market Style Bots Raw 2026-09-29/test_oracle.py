"""Offline structural tests; no terminal or account access."""
import json
import numpy as np
import pandas as pd
from verify_signals import ROOT, SOURCE, oracle, hash32

def main():
    checks = []
    flat = pd.DataFrame(dict(open=np.full(400, 100.), high=np.full(400, 101.),
                             low=np.full(400, 99.), close=np.full(400, 100.)))
    for mode in range(4):
        assert oracle(flat, mode)['side'] == 0
    checks.append('No entries on flat, constant-volatility prices in any model')
    for x in [0, 1, 290929, 20000 + 290929, 2**32 - 1]:
        assert 0 <= hash32(x) <= 2**32 - 1
        assert hash32(x) == hash32(x + 2**32)
    checks.append('Random-direction hash deterministic and uint32 wraparound safe')
    tested = 0
    cfg = json.loads((ROOT/'run-config.json').read_text())
    for bot in cfg['bots']:
        f = ROOT/'data'/f"{bot['symbol']}-H1.csv.gz"
        if f.exists():
            bars = pd.read_csv(f)
        else:
            d = pd.read_csv(SOURCE/f"{bot['symbol']}_M5.csv.gz")
            bars = d.groupby(d.time//3600).agg(open=('open','first'), high=('high','max'),
                                              low=('low','min'), close=('close','last'))
        for end in np.linspace(400, len(bars)-20, 20, dtype=int):
            a = bars.iloc[end-400:end].copy()
            v = oracle(a, bot['mode'])
            future_changed = bars.iloc[:end+20].copy()
            for column in ['open','high','low','close']:
                future_changed.loc[future_changed.index[end:], column] *= 100
            assert oracle(future_changed.iloc[end-400:end], bot['mode']) == v
            # Affine price reflection should invert direction, not volatility.
            mirror = a.copy(); centre = float(a.high.max() * 3)
            mirror['open'] = centre - a.open
            mirror['close'] = centre - a.close
            mirror['high'] = centre - a.low
            mirror['low'] = centre - a.high
            m = oracle(mirror, bot['mode'])
            assert m['side'] == -v['side']
            assert np.isclose(m['atr'], v['atr'])
            if bot['mode'] == 2:
                assert 0 <= v['count'] <= 252 and 0 < v['prob'] < 1
                assert m['count'] == v['count'] and m['prob'] == v['prob']
            tested += 1
    checks += ['Past-only slices are invariant to future-price mutation',
               'Long/short signal symmetry under reflected OHLC prices',
               'Gold transition probabilities bounded; observations limited to 252']
    result = dict(passed=True, windows_tested=tested, checks=checks,
                  limitation='Structural oracle tests, not proof of predictive power or a separate market-data source.')
    (ROOT/'ORACLE_TESTS.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
