"""Publish the owner's reviewed roster and retained evidence; never runs MT5."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.catalog import PACKAGE_ROOT, get_website_catalog

EXTRA = {
    'dmc-current-xau', 'dmc-fresh-reaction-xau', 'dmc-fresh-reaction-us100',
    'news-pulse-xau', 'news-pulse-xag', 'news-pulse-btc', 'news-pulse-eurusd',
    'gold-news-v9-direction', 'gold-overnight-value-area', 'xau-trend-progression',
    'us30-hourly-profiles', 'us100-hourly-profiles',
}
DI = {'nasdaq-5m-candle-momentum': 'InpRequireDIAgreement', 'usdjpy-london-open-momentum': 'InpRequireDIAgreement'}

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def main():
    review = PACKAGE_ROOT / 'Active EA Recent Review 2026-10-05' / 'review.json'
    rows = json.loads(review.read_text(encoding='utf-8'))
    products = {p.slug: p for p in get_website_catalog()}
    assert len(rows) == 37 and {r['slug'] for r in rows} == set(products)
    selection = json.loads((PACKAGE_ROOT / 'Trend Progression Optimization 2026-10-05' / 'SELECTION.json').read_text())
    inputs = selection['candidate']['validation']['inputs']
    assert inputs['InpRewardRisk'] == '1.5' and inputs['InpSwingLookback'] == '3'
    assert inputs['InpUseBreakEven'] == inputs['InpUseATRTrailing'] == 'false'
    overrides = {k: str(v) for k,v in inputs.items() if k not in ('InpAuditTag','InpResearchADXMin','InpResearchDI','InpRiskPercent')}
    comparisons = json.loads((PACKAGE_ROOT / 'Trend Progression Optimization 2026-10-05' / 'COMPARISON.json').read_text())
    chosen = {r['period']: r for r in comparisons if r['variant'] == 'CANDIDATE'}
    entries, public = [], []
    for r in rows:
        slug = r['slug']; p = products[slug]
        original = r.get('original_recommendation', r['recommendation'])
        phase = 'live' if original == 'keep' or slug in EXTRA else ('paused' if original == 'pause' else 'review')
        decision = 'Owner-selected for the reviewed live-trading phase; not a statistical validation pass or proof of installation.' if phase == 'live' else r['brief']
        entry = dict(slug=slug, installer_label=p.installer_label, phase=phase, decision=decision)
        if slug in DI:
            entry.update(di_input=DI[slug], di_default='ON')
        if slug == 'xau-trend-progression':
            entry['input_overrides'] = overrides
            entry['variant'] = '1.5R, 3-bar swing, no BE/trailing, ADX/DI off'
        entries.append(entry)
        row = {k:r.get(k) for k in ('slug','label','canonical','mode','year','recent','reason','next_review','limitations','provenance','history_quality')}
        row.update(phase=phase, decision=decision, original_recommendation=original, variant=entry.get('variant','Unchanged preferred normal preset'))
        if slug == 'xau-trend-progression':
            for key, period in [('year','1Y'),('recent','3M')]:
                c=chosen[period]; m=c['metrics']
                row[key]={k:m.get(k) for k in ('trades','return_pct','pf','win_rate','win_streak','loss_streak','avg_win','avg_loss')}
                row[key].update(start=c['window'][0].replace('.','-'), end_exclusive=c['window'][1].replace('.','-'), equity_dd_pct=c['native']['equity_dd_pct'])
            row['mode']='Reviewed 1.5R candidate — not the normal 0.6R preset'
            row['reason']='Owner chose the 1.5R candidate. Latest quarter lost; 26 annual trades; winning/losing runs 3/3; robustness screen failed and older stress lost 8.78%. Previous shorter-OOS study, not validated under the new two-year policy.'
            row['next_review']='Observe forward execution. User deployment approval is separate from research qualification; no new backtest was run for this package.'
        if slug in DI:
            row['di_default']='ON'
            row['di_note']='DI OFF is a custom unvalidated selection; published DI-ON results do not describe it.'
        if slug in ('us30-hourly-profiles','us100-hourly-profiles'):
            row['variant']='Unchanged hours; selected risk against frozen historical loss; no SL'
            row['reason']='Owner approved the unchanged hourly EA for this profile. '+(r.get('reason') or '')
            row['next_review']='Retained results are the original fixed-one-lot benchmark, not the history-sized reviewed profile. No stop-loss: a future trade can lose more than the selected risk scenario. '+(r.get('next_review') or '')
        public.append(row)
    counts=Counter(e['phase'] for e in entries)
    assert counts == dict(live=25, paused=6, review=6), counts
    manifest=dict(version='2026-10-06', title='reviwed_Eas', phase_label='Passed to live trading phase',
                  approval_kind='Owner deployment decision, not statistical certification',
                  expected_counts=dict(counts), entries=entries)
    target=PACKAGE_ROOT/'Reviewed EA Deployment 2026-10-06'/'selection.json'
    write(target,manifest)
    public.sort(key=lambda r: (['live','paused','review'].index(r['phase']),r['label']))
    write(ROOT/'data'/'ea-review.json', dict(version='2026-10-06', selection_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source_review='Active EA Recent Review 2026-10-05', scope='Retained standalone evidence, not a shared portfolio or new backtest. Per-row dates and variant apply.', rows=public))
    print(json.dumps(dict(total=len(entries),counts=counts,di_prompts=list(DI),backtests_run=0)))

if __name__ == '__main__': main()
