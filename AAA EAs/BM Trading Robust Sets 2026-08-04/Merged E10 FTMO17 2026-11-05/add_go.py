"""Owner 2026-11-05: does adding Gold Overnight Value Area to E10 help? Same native ledgers and replay as analyze.py, no guard; three-way Monte Carlo and 12-month block bootstrap; fixed R. -> ADD_GO.json"""
import json
from collections import defaultdict
from pathlib import Path
H = Path(__file__).resolve().parent
src = (H / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
ns = dict(__file__=str(H / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns)
PORT, ALL, rb, replay, WINDOWS, PLAN = ns['PORT'], ns['ALL'], ns['rb'], ns['replay'], ns['WINDOWS'], ns['PLAN']
sets = {'E10': PORT['E10'], 'E10+GoldOvernight': PORT['E10'] + ALL['gold-overnight-value-area']}
Y = list(PLAN['years']); out = {}
for n, rows in sets.items():
    seq = sorted(rows, key=lambda r: (r['c'], r['key'])); R = [r['R'] for r in seq]; T = [dict(close_time=r['c'].strftime('%Y-%m-%dT%H:%M:%S'), r=r['R']) for r in seq]
    gl = -sum(x for x in R if x < 0); mc = rb.three_monte_carlo(R); yr = rb.three_monte_carlo(R, horizon=round(len(R) / 7.83)); b = rb.day_block_bootstrap(T, 261, value='r', paths=10000, block_days=5, seed=20261105)
    days = defaultdict(float)
    for r in seq: days[r['c'].date().isoformat()] += r['R']
    def seg(w): return round(sum(r['R'] for r in seq if WINDOWS[w][0] <= r['c'].date().isoformat() < WINDOWS[w][1]), 1)
    out[n] = dict(trades=len(R), per_month=round(len(R) / 94, 1), total_r=round(sum(R), 1), mean_r=round(sum(R) / len(R), 4), pf=round(sum(x for x in R if x > 0) / gl, 3), win=round(100 * sum(x > 0 for x in R) / len(R), 1), real_dd=round(mc['real']['max_drawdown'], 1), ret_dd=round(sum(R) / mc['real']['max_drawdown'], 2),
                  shuffle_p95=mc['reshuffle']['max_drawdown']['p95'], worse_than=mc['reshuffle']['real_drawdown_worse_than_pct'], worst_day_r=round(min(days.values()), 2), resample=(mc['resample']['red_pct'], yr['resample']['red_pct']), randomize=(mc['randomize']['both']['red_pct'], yr['randomize']['both']['red_pct']), block12=(b['total']['p05'], b['total']['p50'], b['max_drawdown']['p95']),
                  years={y: seg(y) for y in Y}, dev=seg('dev'), val=seg('val'), oos=seg('oos'), touches={f'{m}': {y: bool(replay(rows, y, 'NONE', m)['touch_2step']) for y in Y} for m in (0.005,)}, closed_dd_05={y: replay(rows, y, 'NONE', 0.005)['closed_dd'] for y in Y})
    x = out[n]; print(n, {k: v for k, v in x.items() if k not in ('touches',)}, flush=True)
go = ALL['gold-overnight-value-area']; mg = [r['R'] for r in sorted(go, key=lambda r: r['c'])]
(H / 'ADD_GO.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
