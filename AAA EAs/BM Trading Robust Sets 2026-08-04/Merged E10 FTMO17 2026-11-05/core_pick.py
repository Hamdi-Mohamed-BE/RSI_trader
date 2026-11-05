"""Owner 2026-11-05: which EAs to keep in a new profile. Rule: over 2019-2026 (native ledgers), profitable in development, validation and OOS, with PF >= 1.15. 3 Way Gold is scored per module. The resulting list is run through the same all-years tests. Selected on the same history, so in-sample. -> CORE_PICK.json"""
import json
from pathlib import Path
H = Path(__file__).resolve().parent
src = (H / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
ns = dict(__file__=str(H / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns)
ALL, PORT, W, rb, replay = ns['ALL'], ns['PORT'], ns['WINDOWS'], ns['rb'], ns['replay']; Y = [str(y) for y in range(2019, 2027)]
items = {k: v for k, v in ALL.items() if k != '3-way-gold'}
for tag, name in (('3WG MOM', '3 Way Gold momentum'), ('3WG BRK', '3 Way Gold breakout'), ('3WG TOM', '3 Way Gold turn of month')): items[name] = [r for r in ALL['3-way-gold'] if r['comment'].startswith(tag)]


def seg(rows, w): return round(sum(r['R'] for r in rows if W[w][0] <= r['c'].date().isoformat() < W[w][1]), 1)


def score(rows):
    R = [r['R'] for r in rows]; gl = -sum(x for x in R if x < 0)
    return dict(n=len(R), total=round(sum(R), 1), pf=round(sum(x for x in R if x > 0) / gl, 2) if gl else None, dev=seg(rows, 'dev'), val=seg(rows, 'val'), oos=seg(rows, 'oos'), last_year=round(sum(r['R'] for r in rows if '2025-11-01' <= r['c'].date().isoformat() < '2026-11-01'), 1), dd=round(rb.max_drawdown([r['R'] for r in sorted(rows, key=lambda r: r['c'])]), 1))


table = sorted(((k, score(v)) for k, v in items.items()), key=lambda kv: -kv[1]['total'])
for k, s in table:
    s['pass'] = s['dev'] > 0 and s['val'] > 0 and s['oos'] > 0 and (s['pf'] or 0) >= 1.15; print(('KEEP ' if s['pass'] else '     ') + k.ljust(38), s, flush=True)
core = [k for k, s in table if s['pass']]; print('CORE', len(core), core, flush=True)
ports = {'CORE': [r for k in core for r in items[k]], 'CORE9': [r for k in core + ['xau-rsi-vwap'] for r in items[k]], 'E10': PORT['E10'], 'FTMO17': PORT['FTMO17'], 'M22': PORT['M22']}; out = dict(table=dict(table), core=core, ports={})
for n, rows in ports.items():
    seq = sorted(rows, key=lambda r: (r['c'], r['key'])); R = [r['R'] for r in seq]; mc, one = rb.three_monte_carlo(R), rb.three_monte_carlo(R, horizon=round(len(R) / 7.83)); gl = -sum(x for x in R if x < 0)
    T = [dict(close_time=r['c'].strftime('%Y-%m-%dT%H:%M:%S'), r=r['R']) for r in seq]; b = rb.day_block_bootstrap(T, 261, value='r', paths=10000, block_days=5, seed=20261105)
    x = dict(trades=len(R), per_month=round(len(R) / 94, 1), total=round(sum(R), 1), mean=round(sum(R) / len(R), 3), pf=round(sum(v for v in R if v > 0) / gl, 3), win=round(100 * sum(v > 0 for v in R) / len(R), 1), real_dd=round(mc['real']['max_drawdown'], 1), ret_dd=round(sum(R) / mc['real']['max_drawdown'], 2), shuffle_p95=round(mc['reshuffle']['max_drawdown']['p95'], 1), worse=mc['reshuffle']['real_drawdown_worse_than_pct'],
             resample=(mc['resample']['red_pct'], one['resample']['red_pct']), randomize=(mc['randomize']['both']['red_pct'], one['randomize']['both']['red_pct']), block12=(b['total']['p05'], b['total']['p50'], b['max_drawdown']['p95']), years={y: seg(seq, y) for y in Y}, dev=seg(seq, 'dev'), val=seg(seq, 'val'), oos=seg(seq, 'oos'), last_year=round(sum(r['R'] for r in seq if '2025-11-01' <= r['c'].date().isoformat() < '2026-11-01'), 1),
             touches05={y: bool(replay(rows, y, 'NONE', 0.005)['touch_2step']) for y in Y}, dd05=[replay(rows, y, 'NONE', 0.005)['closed_dd'] for y in Y], ret05=[replay(rows, y, 'NONE', 0.005)['ret'] for y in Y])
    out['ports'][n] = x; print(n, {k: v for k, v in x.items() if k != 'touches05'}, 'touch years', sum(x['touches05'].values()), flush=True)
(H / 'CORE_PICK.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
