"""Item 1: best-day / best-trade dependence for every catalogue EA from its cached native evidence (recommended mode).

uv run python ".../_Ops Monitor/dependence_audit.py"   ->  output/DEPENDENCE_AUDIT.json + .md
"""
from common import OUT, dependence, evidence_trades, now_utc, products, roster, save

PERIODS = ('5y', '3y', '1y')


def main():
    phases = roster(); rows = []
    for slug, p in products().items():
        for period in PERIODS:
            trades, meta, mode = evidence_trades(slug, period)
            dep = dependence(trades, 'net_profit', 'close_time')
            rows.append(dict(slug=slug, label=p.label, phase=phases.get(slug, '-'), period=period, mode=mode,
                             evidence=(meta or {}).get('period'), source=(meta or {}).get('source'), **dep))
    save('DEPENDENCE_AUDIT.json', dict(generated_utc=now_utc().isoformat(), periods=PERIODS, rows=rows))
    order = {'live': 0, 'paused': 1, 'review': 2}
    md = ['# Best-day dependence audit (all catalogue EAs)', '',
          f'Generated {now_utc():%Y-%m-%d %H:%M} UTC from the website evidence cache (native MT5, recommended mode, $10k, '
          '1% risk). Rule: a positive total FAILS if removing the single best day or the single best trade leaves <= 0. '
          '"Without top 5 days" and "without worst day" are diagnostics only.', '',
          '| Phase | EA | Window | Trades | Total $ | Best day $ | w/o best day $ | w/o best trade $ | w/o top-5 days $ | Best-day share | Verdict |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in sorted(rows, key=lambda r: (order.get(r['phase'], 3), r['label'], PERIODS.index(r['period']))):
        if r['verdict'] == 'NO_TRADES':
            md.append(f"| {r['phase']} | {r['label']} | {r['period']} | 0 | — | — | — | — | — | — | NO EVIDENCE |"); continue
        share = '—' if r.get('best_day_share_of_total') is None else f"{100 * r['best_day_share_of_total']:.0f}%"
        verdict = {'NOT_APPLICABLE_NON_POSITIVE_TOTAL': 'n/a (total ≤ 0)'}.get(r['verdict'], r['verdict'])
        md.append(f"| {r['phase']} | {r['label']} | {r['period']} | {r['trades']} | {r['total']:+,.0f} | {r['best_day']['value']:+,.0f} | "
                  f"{r['without_best_day']:+,.0f} | {r['without_best_trade']:+,.0f} | {r['without_top5_days']:+,.0f} | {share} | **{verdict}** |")
    fails = [r for r in rows if r['verdict'] == 'FAIL']
    top5 = [r for r in rows if r.get('top5_days_sign_flip')]
    md += ['', f"**{len(fails)} EA-window results FAIL** the best-day / best-trade test:"]
    md += [f"- {r['label']} ({r['phase']}) {r['period']}: total {r['total']:+,.0f} $, without best day {r['without_best_day']:+,.0f} $, "
           f"without best trade {r['without_best_trade']:+,.0f} $." for r in fails] or ['- none']
    md += ['', f"Diagnostic: {len(top5)} positive EA-window results turn non-positive without their 5 best days:"]
    md += [f"- {r['label']} ({r['phase']}) {r['period']}: {r['total']:+,.0f} $ → {r['without_top5_days']:+,.0f} $" for r in top5] or ['- none']
    (OUT / 'DEPENDENCE_AUDIT.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'{len(rows)} rows; FAIL {len(fails)}; top-5 flips {len(top5)}')
    for r in fails + top5:
        print(' ', r['label'], r['phase'], r['period'], r['total'], r['without_best_day'], r['without_best_trade'], r['without_top5_days'], r['verdict'])


if __name__ == '__main__':
    main()
