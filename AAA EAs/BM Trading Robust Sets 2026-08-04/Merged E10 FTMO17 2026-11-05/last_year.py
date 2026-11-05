"""Owner 2026-11-05: best EAs of E10 and FTMO17 over the last year (trades closed 2025-11-01 -> 2026-11-01), ordered. Native Model 4 ledgers of native.py, 1R = 1% risk, net of costs. Most of this window has real ticks (from 2026-01-01). -> LAST_YEAR.json, LAST_YEAR.md"""
import json
from pathlib import Path
H = Path(__file__).resolve().parent
src = (H / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
ns = dict(__file__=str(H / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns)
ALL, E10_KEYS, EXTRA, rb, wd = ns['ALL'], ns['E10_KEYS'], ns['EXTRA'], ns['rb'], ns['weekdays']; A, B = '2025-11-01', '2026-11-01'
rows = {k: v for k, v in ALL.items()}; rows['3-way-gold breakout module'] = [r for r in ALL['3-way-gold'] if r['comment'].startswith('3WG BRK')]
out = []
for k, v in rows.items():
    T = sorted([r for r in v if A <= r['c'].date().isoformat() < B], key=lambda r: r['c']); R = [r['R'] for r in T]
    if not R: out.append(dict(ea=k, n=0, total=0.0)); continue
    w = [x for x in R if x > 0]; l = [x for x in R if x < 0]; gl = -sum(l); m = 12.0; d = wd(A, B); avw = sum(w) / len(w) if w else 0; avl = -sum(l) / len(l) if l else 0
    days = {}
    for r in T: days[r['c'].date()] = days.get(r['c'].date(), 0) + r['R']
    out.append(dict(ea=k, n=len(R), pm=round(len(R) / m, 1), pd=round(len(R) / d, 2), total=round(sum(R), 1), mean=round(sum(R) / len(R), 3), pf=round(sum(w) / gl, 2) if gl else None, win=round(100 * len(w) / len(R), 1), need=round(100 * avl / (avw + avl), 1) if avw + avl else None, dd=round(rb.max_drawdown(R), 1), best_day=round(max(days.values()), 1),
                    without_best_day=round(sum(R) - max(days.values()), 1), ftmo17=k in ALL and k not in EXTRA, e10=k in E10_KEYS or k.startswith('3-way-gold b')))
out.sort(key=lambda x: -x['total'])
(H / 'LAST_YEAR.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
L = ['| # | EA | In | Total R | PF | Win % | Trades (/month, /day) | Avg R | Max DD R | Without best day |', '|---:|---|---|---:|---:|---:|---|---:|---:|---:|']
for i, x in enumerate(out, 1):
    tag = 'Both' if x.get('ftmo17') and x.get('e10') else 'FTMO17' if x.get('ftmo17') else 'E10'
    L.append(f"| {i} | {x['ea']} | {tag} | {x['total']:+.1f} | {x.get('pf')} | {x.get('win')} | {x['n']} ({x.get('pm')}, {x.get('pd')}) | {x.get('mean')} | {x.get('dd')} | {x.get('without_best_day')} |")
(H / 'LAST_YEAR.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
