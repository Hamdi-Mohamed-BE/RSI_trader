"""Combine every configuration evaluated on ALL THREE windows (dev / validation / OOS) by the three 2026-10-20 FTMO studies.

Owner lowered the target to 65% AFTER the searches ran; this summary therefore ranks descriptively over all history and
labels it as a post-hoc, all-history (in-sample) ranking. No new simulation is run.
python consolidate.py -> SUMMARY.json + SUMMARY.md
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
FAST, RISK, LLN = B / 'FTMO Fastest Funded Search 2026-10-20', B / 'FTMO Risk Approach Search 2026-10-20', B / 'FTMO Law Of Large Numbers Test 2026-10-20'
WIN = ['dev', 'val', 'oos']; COSTS = ['recorded_exness', 'fixed_cost_stress']


def rd(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def entries():
    out = {}
    # Fastest Funded Search: finalists in dev/val/oos (standard guard)
    for w, f in (('dev', 'DEV.json'), ('val', 'VAL.json'), ('oos', 'OOS.json')):
        for r in rd(FAST / f)['results']:
            key = f"{r['basket']} · ${r['cap']} · standard guard"
            for c in COSTS:
                d = r['detail'][c]
                out.setdefault(key, dict(source='Fastest Funded Search', eas=r['eas'])).setdefault(w, {})[c] = dict(
                    starts=d['starts'], pass180=d['pass_share'], funded90=None, median_funded=d['median_days_funded'], breaches=d['breaches'],
                    eqdd=d['eqdd_max'], day=d['day_max'], tpm=d['median_trades_per_month'], tpw=d['median_trades_per_weekday'])
    # Risk Approach Search: finalists
    for w, f in (('dev', 'DEV.json'), ('val', 'VAL.json'), ('oos', 'OOS.json')):
        for r in rd(RISK / f)['results']:
            c0 = r['cfg']
            key = f"{c0['basket']} · ${c0['cap1']:g} / ${c0['cap2']:g} · latch ${c0['latch']} · buffer ${c0['buffer']}"
            for c in COSTS:
                d = r['detail'][c]
                out.setdefault(key, dict(source='Risk Approach Search', eas=None)).setdefault(w, {})[c] = dict(
                    starts=d['starts'], pass180=d['pass_share'], funded90=d['funded_90'], median_funded=d['median_days_funded'], breaches=d['breaches'],
                    eqdd=d['eqdd_max'], day=d['day_max'], tpm=d['median_trades_per_month'], tpw=d['median_trades_per_weekday'])
    # Law of Large Numbers test: every configuration
    lln = rd(LLN / 'RESULTS.json')
    for r in lln['results']:
        key = f"{r['basket']} · ${r['cap']} · standard guard"
        out.setdefault(key, dict(source='LLN test', eas=len(lln['baskets'][r['basket']]))).setdefault(r['window'], {})[r['cost']] = dict(
            starts=r['starts'], pass180=r['pass_share'], funded90=r['funded_90'], median_funded=r['median_days_funded'], breaches=r['breaches'],
            eqdd=r['eqdd_max'], day=r['day_max'], tpm=r['median_trades_per_month'], tpw=r['median_trades_per_weekday'])
    return {k: v for k, v in out.items() if all(w in v and all(c in v[w] for c in COSTS) for w in WIN)}


def summarize(v):
    win = {}
    tot_n = 0; acc = dict(pass180=0, funded90=0, mf=0); mf_w = 0; f90_ok = True
    for w in WIN:
        a = v[w]
        p = sum(a[c]['pass180'] for c in COSTS) / 2
        f = None if any(a[c]['funded90'] is None for c in COSTS) else sum(a[c]['funded90'] for c in COSTS) / 2
        m = [a[c]['median_funded'] for c in COSTS if a[c]['median_funded'] is not None]
        win[w] = dict(pass180=round(p, 4), funded90=None if f is None else round(f, 4), median_funded=round(sum(m) / len(m), 1) if m else None,
                      starts=a['recorded_exness']['starts'])
        n = a['recorded_exness']['starts']; tot_n += n
        acc['pass180'] += p * n
        if f is None: f90_ok = False
        else: acc['funded90'] += f * n
        if m: acc['mf'] += (sum(m) / len(m)) * n; mf_w += n
    allh = dict(pass180=round(acc['pass180'] / tot_n, 4), funded90=round(acc['funded90'] / tot_n, 4) if f90_ok else None,
                median_funded_approx=round(acc['mf'] / mf_w, 1) if mf_w else None, starts=tot_n)
    worst = dict(breaches=sum(v[w][c]['breaches'] for w in WIN for c in COSTS), eqdd=max(v[w][c]['eqdd'] for w in WIN for c in COSTS),
                 day=max(v[w][c]['day'] for w in WIN for c in COSTS), tpm=v['oos']['recorded_exness']['tpm'], tpw=v['oos']['recorded_exness']['tpw'])
    return win, allh, worst


def main():
    rows = []
    for k, v in entries().items():
        win, allh, worst = summarize(v)
        rows.append(dict(config=k, source=v['source'], eas=v['eas'], windows=win, all_history=allh, worst=worst,
                         meets_65_all_history=allh['pass180'] >= .65, min_window_pass=min(win[w]['pass180'] for w in WIN)))
    rows.sort(key=lambda r: (-r['all_history']['pass180'], r['all_history']['median_funded_approx'] or 1e9))
    (R / 'SUMMARY.json').write_text(json.dumps(dict(note='post-hoc all-history ranking at the owner-lowered 65% target; in-sample', rows=rows), indent=1), encoding='utf-8')
    pct = lambda x: '—' if x is None else f'{100 * x:.0f}%'  # noqa: E731
    md = ['| # | Configuration | Source | Pass ≤180 d: dev / val / OOS | **All-history pass ≤180 d** | Funded ≤90 d (all history) | Median days to funded (approx) | Breaches | Worst eq DD $ | Worst day $ | Trades /month (/weekday) |',
          '|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|']
    for i, r in enumerate(rows, 1):
        w = r['windows']; a = r['all_history']; x = r['worst']
        md.append(f"| {i} | {r['config']} | {r['source']} | {pct(w['dev']['pass180'])} / {pct(w['val']['pass180'])} / {pct(w['oos']['pass180'])} | **{pct(a['pass180'])}** | "
                  f"{pct(a['funded90'])} | {a['median_funded_approx']} | {x['breaches']} | {x['eqdd']:,.0f} | {x['day']:,.0f} | {x['tpm']} ({x['tpw']}) |")
    (R / 'SUMMARY.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md))
    print('starts per window:', {w: rows[0]['windows'][w]['starts'] for w in WIN}, 'all:', rows[0]['all_history']['starts'])


if __name__ == '__main__':
    main()
