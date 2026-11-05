"""Gold Overnight Value Area, win rate and detail per data period, from its native 2019-2026 ledger (net of costs), and E10 with and without it. By the close date. -> GO_PERIODS.md"""
from pathlib import Path
H = Path(__file__).resolve().parent
src = (H / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
ns = dict(__file__=str(H / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns)
PORT, ALL, W, wd = ns['PORT'], ns['ALL'], ns['WINDOWS'], ns['weekdays']; GO = ALL['gold-overnight-value-area']
ORDER = [('Development', 'dev'), ('Validation', 'val'), ('OOS', 'oos'), ('All', 'all')] + [(y, y) for y in map(str, range(2019, 2027))]


def row(rows, w):
    a, b = W[w]; R = [r['R'] for r in rows if a <= r['c'].date().isoformat() < b]; v = [x for x in R if x > 0]; l = [x for x in R if x < 0]; gl = -sum(l); d = wd(a, b)
    avw, avl = sum(v) / len(v), -sum(l) / len(l); be = 100 * avl / (avw + avl)
    return dict(n=len(R), pm=len(R) / (d / 21.75), pd=len(R) / d, win=100 * len(v) / len(R), be=be, avw=avw, avl=avl, pf=sum(v) / gl, tot=sum(R))


L = ['| Period | Dates | Trades | /month | /day | Win rate | Win rate needed to break even | Avg win | Avg loss | PF | Total R |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for name, w in ORDER:
    x = row(GO, w); L.append(f"| {name} | {W[w][0]} to {W[w][1]} | {x['n']} | {x['pm']:.1f} | {x['pd']:.2f} | {x['win']:.1f}% | {x['be']:.1f}% | +{x['avw']:.2f}R | -{x['avl']:.2f}R | {x['pf']:.2f} | {x['tot']:+.1f} |")
L += ['', '| Period | E10 win rate | E10 + Gold Overnight win rate | E10 total R | With Gold Overnight total R |', '|---|---:|---:|---:|---:|']
for name, w in ORDER:
    a, b = row(PORT['E10'], w), row(PORT['E10'] + GO, w); L.append(f"| {name} | {a['win']:.1f}% | {b['win']:.1f}% | {a['tot']:+.1f} | {b['tot']:+.1f} |")
(H / 'GO_PERIODS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
