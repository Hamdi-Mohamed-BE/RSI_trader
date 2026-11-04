"""Owner 2026-11-04: "scan all the bots we have and tell what you think is real edge not just luck". One scorecard for every bot with a
5-year native trade stream (Prop Portfolio Selection 2026-11-03: INPUTS-FULL.json = Full EA presets, INPUTS-FTMO17.json = the 0.5R ORBs and
the 3 Way Gold market variant). Native Model 4 long-history runs 2021-10-07 -> 2026-10-06, recorded Exness costs.
R = (gross + commission + swap) / initial stop risk. Trades still open at the end are dropped. 3 Way Gold modules are scored separately.
Rules (declared before computing; all on this history, which was used to choose most settings, so this is in-sample):
  1 n >= 100 trades;  2 sum R > 0 in dev 2021-10-07 -> 2023-10-06, val -> 2024-10-06 AND oos -> 2026-10-06;
  3 PF >= 1.15;  4 best-day / best-trade check PASS (robustness.dependence);
  5 three-way MC full sample: resample red <= 5% and randomize (drop 10% + 0.05R) red <= 10%;
  6 break-even extra cost (mean R) >= 0.10R.
  REAL EDGE (likely) = all 6 | MAYBE = exactly one fails | NOT PROVEN = two or more fail. -> SCAN.json, SCAN.md"""
import json, statistics, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'
sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline')); import robustness as rb  # noqa: E402
SEG = {'dev': ('2021-10-07', '2023-10-06'), 'val': ('2023-10-06', '2024-10-06'), 'oos': ('2024-10-06', '2026-10-06')}
YEARS = 4.997


def load(f):
    d = json.loads((SEL / f).read_text(encoding='utf-8'))
    out = defaultdict(list)
    for t in d['candidates']:
        if t['cl'] is None: continue
        day = datetime.fromtimestamp(t['cl'], timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        out[t['ea']].append(dict(close_time=day, r=(t['unit_gross'] + t['unit_commission'] + t['unit_swap']) / t['unit_risk']))
    return out


full, ftmo = load('INPUTS-FULL.json'), load('INPUTS-FTMO17.json')
bots = {k: v for k, v in full.items()}
for k in ('xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30', 'us100-orb-new-york-m30', 'us100-h1-orb-13utc', 'us100-selective-orb-v3'):
    bots[k + ' (0.5R)'] = ftmo[k]
for k in ('3-way-gold#930930100', '3-way-gold#930930101', '3-way-gold#930930102'):
    bots[k + ' (market)'] = ftmo[k]
rows = []
for name, T in sorted(bots.items()):
    T.sort(key=lambda t: t['close_time']); R = [t['r'] for t in T]
    seg = {s: round(sum(t['r'] for t in T if a <= t['close_time'][:10] < b), 2) for s, (a, b) in SEG.items()}
    gl = -sum(v for v in R if v < 0); pf = sum(v for v in R if v > 0) / gl if gl else float('inf')
    dep = rb.dependence(T, value='r', time='close_time'); mc = rb.three_monte_carlo(R)
    checks = {'n>=100': len(R) >= 100, 'all 3 parts positive': all(v > 0 for v in seg.values()), 'PF>=1.15': pf >= 1.15,
              'best-day PASS': dep['verdict'] == 'PASS', 'MC resample<=5% & randomize<=10%': mc['resample']['red_pct'] <= 5 and mc['randomize']['both']['red_pct'] <= 10,
              'break-even cost>=0.10R': statistics.fmean(R) >= 0.10}
    fails = [k for k, ok in checks.items() if not ok]
    verdict = 'REAL EDGE (likely)' if not fails else 'MAYBE' if len(fails) == 1 else 'NOT PROVEN'
    rows.append(dict(bot=name, trades=len(R), per_month=round(len(R) / (YEARS * 12), 1), win_pct=round(100 * sum(v > 0 for v in R) / len(R), 1),
                     pf=round(pf, 2), mean_r=round(statistics.fmean(R), 3), total_r=round(sum(R), 1), seg=seg, dd_r=round(rb.max_drawdown(R), 1),
                     shuffle_dd_p95=mc['reshuffle']['max_drawdown']['p95'], resample_red=mc['resample']['red_pct'],
                     randomize_red=mc['randomize']['both']['red_pct'], dependence=dep['verdict'], fails=fails, verdict=verdict))
order = {'REAL EDGE (likely)': 0, 'MAYBE': 1, 'NOT PROVEN': 2}
rows.sort(key=lambda r: (order[r['verdict']], -r['mean_r']))
(H / 'SCAN.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
L = ['| Verdict | Bot | Trades (/month) | Win % | PF | Mean R | Dev / Val / OOS R | DD R (shuffle p95) | Resample / randomize red | Best day | Fails |',
     '|---|---|---|---:|---:|---:|---|---|---|---|---|']
for r in rows:
    s = r['seg']
    L.append(f"| {r['verdict']} | {r['bot']} | {r['trades']} ({r['per_month']}) | {r['win_pct']} | {r['pf']} | {r['mean_r']:+.3f} | {s['dev']:+.1f} / {s['val']:+.1f} / {s['oos']:+.1f} | "
             f"{r['dd_r']} ({r['shuffle_dd_p95']:.1f}) | {r['resample_red']}% / {r['randomize_red']}% | {r['dependence']} | {', '.join(r['fails']) or '—'} |")
(H / 'SCAN.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
