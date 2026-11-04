"""Owner 2026-11-04: compare the picked FTMO17 with a 5-EA portfolio: EMA3, Nasdaq 5M (best version = deployed ATR6 stop, DI ON),
Gold Overnight Value Area, XAU RSI VWAP, 3 Way Gold. G5 = the FTMO17 stream (Prop Portfolio Selection 2026-11-03/INPUTS-FTMO17.json)
filtered to those five EAs, so every trade, source and the 3 Way Gold market-entry variant are identical to FTMO17's; only the roster
changes. Same frozen engines, weekday starts, MC pools and seeds, Prop Ready guard at the chosen risk:
  build                 -> INPUTS-G5.json
  challenge <risk>      FTMO 2-step $100k (prop_select.challenge)          -> CH-G5-<risk>.json
  funded <risk>         FTMO funded income, 36 m MC (prop_select.funded)    -> FU-G5-<risk>.json
  f1 <risk>             FTMO 1-Step with the built ftmo 1_step guard (f1_profile.main) -> F1P-G5-<risk>.json
  mc3                   three-way Monte Carlo (robustness.three_monte_carlo) for G5 and FTMO17 -> MC3.json
Run from EA store: uv run --with pandas --with numpy python "<this>" challenge 0.50"""
import importlib.util, json, statistics, sys
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'
FIVE = {'ema3', 'nasdaq-5m-candle-momentum', 'gold-overnight-value-area', 'xau-rsi-vwap'}
keep = lambda ea: ea in FIVE or ea.startswith('3-way-gold#')  # noqa: E731


def build():
    d = json.loads((SEL / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))
    d['candidates'] = [c for c in d['candidates'] if keep(c['ea'])]
    (H / 'INPUTS-G5.json').write_text(json.dumps(d, separators=(',', ':')), encoding='utf-8')
    print('G5 trades', len(d['candidates']), sorted({c['ea'] for c in d['candidates']}))


def engines():
    spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py')
    F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
    S = F1.S
    S.R = H; F1.R = H                                   # read INPUTS-G5 and write results here; engine code untouched
    S.CANDIDATES['G5'] = dict(label='5 EAs: EMA3, Nasdaq 5M ATR6 DI ON, Gold Overnight VA, XAU RSI VWAP, 3 Way Gold', guard=True,
                              risks=('0.50', '0.75', '1.00'), members='FTMO17 stream filtered')
    return S, F1


def mc3():
    sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline'))
    from robustness import three_monte_carlo
    out = {}
    for name, path in (('FTMO17', SEL / 'INPUTS-FTMO17.json'), ('G5', H / 'INPUTS-G5.json')):
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
        {'challenge': lambda: S.challenge('G5', a[1]), 'funded': lambda: S.funded('G5', a[1]), 'f1': lambda: F1.main('G5', a[1])}[a[0]]()
