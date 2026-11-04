"""Owner 2026-11-04: build the Edge Scan 2026-11-04 list + Nasdaq 5M + XAU RSI VWAP and compare it with FTMO17 on FTMO 2-step and 1-Step.
E10 = Prop Portfolio Selection 2026-11-03 INPUTS-FULL.json members USDJPY London, EMA3, ORB VP Volume Confirmed, ORB VP, Sell Nasdaq 15min,
XAU Regime Switch, XAU Elliott Wave 1-2-3, Nasdaq 5M (ATR6, DI ON), XAU RSI VWAP + the 3 Way Gold breakout module 930930101 market variant
from INPUTS-FTMO17.json (the guard admits no pending orders). Same frozen engines, weekday starts, MC pools and seeds, Prop Ready guard at
the chosen risk, $100k:
  build                 -> INPUTS-E10.json
  challenge <risk>      FTMO 2-step (prop_select.challenge)                       -> CH-E10-<risk>.json
  funded <risk>         FTMO funded income, 36 m MC (prop_select.funded)          -> FU-E10-<risk>.json
  f1 <risk>             FTMO 1-Step with the built ftmo 1_step guard (f1_profile)  -> F1P-E10-<risk>.json
  mc3                   three-way Monte Carlo (robustness.three_monte_carlo)       -> MC3.json
Run from EA store: uv run --with pandas --with numpy python "<this>" challenge 0.50"""
import collections, importlib.util, json, statistics, sys
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'
WANT = {'usdjpy-london-open-momentum', 'ema3', 'orb-volume-profile-volume-confirmed', 'orb-volume-profile', 'sell-nasdaq-15min',
        'xau-regime-switch', 'xau-elliott-wave-1-2-3', 'nasdaq-5m-candle-momentum', 'xau-rsi-vwap'}
THREEWAY_B = '3-way-gold#930930101'


def build():
    full = json.loads((SEL / 'INPUTS-FULL.json').read_text(encoding='utf-8')); ftmo = json.loads((SEL / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))
    assert all(full[k] == ftmo[k] for k in ('year_begin_epoch', 'year_end_exclusive_epoch', 'window'))
    c = [x for x in full['candidates'] if x['ea'] in WANT] + [x for x in ftmo['candidates'] if x['ea'] == THREEWAY_B]
    assert len({x['id'] for x in c}) == len(c) and {x['ea'] for x in c} == WANT | {THREEWAY_B}
    full['candidates'] = c; (H / 'INPUTS-E10.json').write_text(json.dumps(full, separators=(',', ':')), encoding='utf-8')
    print('E10 trades', len(c), dict(collections.Counter(x['ea'] for x in c)))


def engines():
    spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py')
    F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
    S = F1.S
    S.R = H; F1.R = H                                   # read INPUTS-E10 and write results here; engine code untouched
    S.CANDIDATES['E10'] = dict(label='Edge 10 (Edge Scan list + Nasdaq 5M + RSI VWAP)', guard=True, risks=('0.50', '0.75', '1.00'),
                               members=sorted(WANT | {THREEWAY_B}))
    return S, F1


def mc3():
    sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline'))
    from robustness import three_monte_carlo
    out = {}
    for name, path in (('FTMO17', SEL / 'INPUTS-FTMO17.json'), ('E10', H / 'INPUTS-E10.json')):
        d = json.loads(path.read_text(encoding='utf-8'))
        rows = sorted((t for t in d['candidates'] if t['cl'] is not None), key=lambda t: (t['cl'], t['id']))
        R = [(t['unit_gross'] + t['unit_commission'] + t['unit_swap']) / t['unit_risk'] for t in rows]
        yrs = (d['year_end_exclusive_epoch'] - d['year_begin_epoch']) / (365.25 * 86400); per_year = round(len(R) / yrs)
        out[name] = dict(trades=len(R), trades_per_month=round(len(R) / (yrs * 12), 1), mean_r=round(statistics.fmean(R), 4),
                         pf=round(sum(v for v in R if v > 0) / -sum(v for v in R if v < 0), 3), win_pct=round(100 * sum(v > 0 for v in R) / len(R), 2),
                         full=three_monte_carlo(R), one_year=three_monte_carlo(R, horizon=per_year),
                         one_year_cost_010=three_monte_carlo(R, horizon=per_year, extra_cost=0.10)['randomize'])
        print(name, len(R), flush=True)
    (H / 'MC3.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'build': build()
    elif a[0] == 'mc3': mc3()
    else:
        S, F1 = engines()
        {'challenge': lambda: S.challenge('E10', a[1]), 'funded': lambda: S.funded('E10', a[1]), 'f1': lambda: F1.main('E10', a[1])}[a[0]]()
