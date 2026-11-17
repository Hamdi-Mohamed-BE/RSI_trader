"""All-years comparison of TS1 / TS0 / QL (one DI setting): window stats, data_split dev/val/OOS, years in R, three-way MC. uv run --with numpy python full.py DIOFF"""
import gzip, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
H = Path(__file__).resolve().parent; PIPE = H.parent.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import data_split, robustness  # noqa: E402
s = importlib.util.spec_from_file_location('st', H / 'study.py'); st = importlib.util.module_from_spec(s); s.loader.exec_module(st)
DI = sys.argv[1] if len(sys.argv) > 1 else 'DIOFF'; START = '2019-07-16'; END = st.END
sp = data_split.research_split(START, END); W = {'dev': (sp['development']['start'], sp['development']['end_exclusive']), 'val': (sp['validation']['start'], sp['validation']['end_exclusive']), 'oos': (sp['oos']['start'], sp['oos']['end_exclusive'])}
out = dict(windows=W)
for v in st.VAR:
    key = f'{v}_{DI}'; T = sorted(json.loads(gzip.open(H / 'native' / f'nw-USTEC-{key}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time'])
    bal = 1e4; rows = []
    for t in T: rows.append((t['open_time'][:10], t['net_profit'] / (0.01 * bal))); bal += t['net_profit']
    R = [r for _, r in rows]
    def seg(a, b):
        x = [r for d, r in rows if a <= d < b]; w = sum(r for r in x if r > 0); l = -sum(r for r in x if r < 0); eq = pk = dd = 0
        for r in x: eq += r; pk = max(pk, eq); dd = max(dd, pk - eq)
        return dict(n=len(x), r=round(sum(x), 1), pf=round(w / l, 2) if l else None, dd_r=round(dd, 1))
    years = defaultdict(float)
    for d, r in rows: years[d[:4]] += r
    mc = robustness.three_monte_carlo(R, runs=1000, seed=20261104)
    out[v] = dict(all=st.stats(key, 'all'), split={k: seg(*w) for k, w in W.items()}, years={y: round(r, 1) for y, r in sorted(years.items())},
                  mc=dict(resample_red=mc['resample']['red_pct'], randomize_red=mc['randomize']['both']['red_pct'], clumped=mc['reshuffle']['real_drawdown_worse_than_pct']))
(H / f'FULL_{DI}.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))
