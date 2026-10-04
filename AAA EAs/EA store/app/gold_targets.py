"""Verified target-only evidence; never substitute historical 3R/6R reports."""
import hashlib
import json
from pathlib import Path

STORE = Path(__file__).resolve().parents[1]
BASE = STORE.parent / 'BM Trading Robust Sets 2026-08-04'
ROOT = BASE / 'Gold Targets Deployment 2026-10-02'
SLUGS = {'xau-trend-progression', 'xau-slow-trend'}

def evidence(slug, mode='standard', period='1y'):
    path=STORE/f'data/evidence-cache/v1/products/{slug}/{mode}/{period}.json'
    if not path.is_file(): return None
    p=json.loads(path.read_text(encoding='utf-8-sig')); s=p['stats']
    if p.get('source')!='native-mt5-target-sensitivity': return None
    return dict(label=p['evidence_label'],period=p['period'],return_pct=s['return_pct'],
        profit_factor=s['profit_factor'],drawdown_pct=s['max_drawdown_pct'],win_rate_pct=s['win_rate_pct'],
        trades=s['trades'],sharpe_annualized=s.get('sharpe_annualized'),max_win_streak=s['max_win_streak'],
        max_loss_streak=s['max_loss_streak'],history_quality=p['history_quality'],source_note=p['notice'],
        status='Research evidence',caution='User-selected retrospective target; strict cross-window PF screen failed. Not an FTMO pass forecast.')

def verified_payload(product, mode, period, start, end, *, archived=False):
    folder=STORE/f'data/evidence-cache/v1/products/{product.slug}/{mode}'
    p=json.loads((folder/f'{period}.json').read_text(encoding='utf-8-sig'))
    if p.get('source')!='native-mt5-target-sensitivity' and archived:
        # Explicit historical audit only. The ordinary cache builder must NOT
        # overwrite the current ADX/DI record with the old target-only result.
        folder=BASE/'ADX DI Deployment 2026-10-03/before/data/evidence-cache/v1/products'/product.slug/mode
        p=json.loads((folder/f'{period}.json').read_text(encoding='utf-8-sig'))
    if p.get('source')!='native-mt5-target-sensitivity': raise RuntimeError('Stale Gold target evidence')
    if p['available_from']!=str(start) or p['end_exclusive']!=str(end):
        raise RuntimeError('Gold target evidence has independent fixed windows; use its audited runner for new dates')
    selected=json.loads((ROOT/'SELECTION.json').read_text())['profiles'][product.slug]
    profile=selected['ftmo' if mode=='dynamic' else 'normal']
    sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
    if sha(BASE/selected['expert'])!=selected['expert_sha'] or sha(BASE/profile['settings'])!=profile['settings_sha']:
        raise RuntimeError('Gold target binary/SET changed since publication')
    f=p['source_fingerprint']
    if f['production_selection_sha']!=sha(ROOT/'SELECTION.json'):
        raise RuntimeError('Gold target release changed since evidence publication')
    ledger=(BASE/f['research_ledger']).resolve()
    if not ledger.is_relative_to(BASE.resolve()) or sha(ledger)!=f['ledger_sha256']:
        raise RuntimeError('Gold target native position ledger identity mismatch')
    if sha(folder/f'{period}.trades.json')!=f['cached_trades_sha256']:
        raise RuntimeError('Gold target cached trade ledger changed')
    return p,json.loads((folder/f'{period}.trades.json').read_text(encoding='utf-8-sig'))
