"""Item 1b: add (or refresh) a "Best-day dependence" section in a study REPORT.md built with the run_nw.py harness.

Reads native/nw-*/trades.json.gz (closed-deal ledgers, net_profit $). Writes DEPENDENCE.json next to the report and
replaces the section between the markers in REPORT.md (and REPORT.template.md if present, so regeneration keeps it).

uv run python ".../_Ops Monitor/report_dependence.py" --study "<study folder>"
"""
import argparse, gzip, json, re
from pathlib import Path

from common import dependence

START, END = '<!-- best-day-dependence:start -->', '<!-- best-day-dependence:end -->'


def section(study: Path) -> tuple[str, list]:
    rows = []
    for run in sorted(study.glob('native/nw-*')):
        if not (run / 'trades.json.gz').exists() or 'smoke' in run.name:
            continue
        trades = json.loads(gzip.decompress((run / 'trades.json.gz').read_bytes()))
        rows.append(dict(case=run.name[3:], **dependence(trades, 'net_profit', 'close_time')))
    md = [START, '## Best-day dependence (added 2026-10-20)', '',
          'Rule (PIPELINE.md stage 4, 2026-10-20): a positive total FAILS if it turns ≤ 0 without its single best day or single best trade. '
          'The 5-best-days and worst-day columns are diagnostics.', '',
          '| Run | Trades | Total $ | Best day | w/o best day $ | w/o best trade $ | w/o 5 best days $ | w/o worst day $ | Verdict |',
          '|---|---:|---:|---|---:|---:|---:|---:|---|']
    for r in rows:
        if r['verdict'] == 'NO_TRADES':
            md.append(f"| {r['case']} | 0 | — | — | — | — | — | — | no trades |"); continue
        v = {'NOT_APPLICABLE_NON_POSITIVE_TOTAL': 'n/a (already ≤ 0)'}.get(r['verdict'], r['verdict'])
        md.append(f"| {r['case']} | {r['trades']} | {r['total']:+,.0f} | {r['best_day']['date']} {r['best_day']['value']:+,.0f} | {r['without_best_day']:+,.0f} | "
                  f"{r['without_best_trade']:+,.0f} | {r['without_top5_days']:+,.0f} | {r['without_worst_day']:+,.0f} | **{v}** |")
    md.append(END)
    return '\n'.join(md), rows


def apply(path: Path, block: str):
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    if START in text:
        text = re.sub(re.escape(START) + '.*?' + re.escape(END), block.replace('\\', '\\\\'), text, flags=re.S)
    else:
        anchor = text.find('\n## Limitations')
        text = (text[:anchor] + '\n' + block + '\n' + text[anchor:]) if anchor >= 0 else text.rstrip() + '\n\n' + block + '\n'
    path.write_text(text, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--study', required=True)
    study = Path(ap.parse_args().study)
    block, rows = section(study)
    (study / 'DEPENDENCE.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
    for name in ('REPORT.md', 'REPORT.template.md'):
        apply(study / name, block)
    for r in rows:
        print(f"{r['case']:40} {r['verdict']:36} total {r.get('total')} w/o best day {r.get('without_best_day')}")


if __name__ == '__main__':
    main()
