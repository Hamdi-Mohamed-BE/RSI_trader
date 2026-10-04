"""User-approved ADX/DI release and honest historical-evidence labelling."""
import json
import hashlib
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'BM Trading Robust Sets 2026-08-04'
ROOT=BASE/'ADX DI Final Selection 2026-10-03'
VERSION='ADXDI-FINAL-20261003'
FILTERS={
    'usdjpy-london-open-momentum':'ADX(14) >=20 + DI direction agreement on completed M15',
}
RESTORED={'ema3','asia-breakout','xau-trend-progression'}
MANAGED_SLUGS=set(FILTERS)|RESTORED
HISTORICAL_NOTE='Final selection on 3 October 2026: USDJPY keeps ADX >=20 + DI; EMA3, Asia Gold and Trend have no added ADX/DI filter. This is an archived configuration, not a result for the final selection. Current standalone evidence is available for 1y, 3y and 5y; 6m and combined portfolio/FTMO pass and payout forecasts have not been revalidated.'

def apply_product_release(product):
    if product.slug not in MANAGED_SLUGS:return product
    rule=FILTERS.get(product.slug)
    notice=' Final user selection: '+(rule+'. Only completed bars are used; this gate blocks new entries, never protective exits.' if rule else 'Added ADX/DI filter removed; exact native-tested baseline restored. Existing unrelated filters, risk and exits retained.')+' Retrospective evidence, not independent validation.'
    path=ROOT/'WEBSITE_SUMMARY.json'
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    row=data.get('results',{}).get(product.slug)
    evidence=product.evidence
    if row:
        from .catalog import Evidence
        evidence=Evidence(**row)
    from .catalog import LogicStep
    return product.model_copy(update=dict(
        admission_filter=rule, admission_provisional=False,
        description=product.description+notice,risk_note=product.risk_note+notice,
        logic_audit_note='Final user-selected configuration reuses the exact native-tested binary and inputs. USDJPY alone keeps the added ADX/DI filter; current standalone 1y/3y/5y evidence follows the chosen period, not independent forward validation. Historical source note: '+product.logic_audit_note,
        logic=[LogicStep(title='Completed-bar ADX / DI admission',detail=rule+'. Missing/invalid indicator values block entry; all existing exit and risk rules remain active.'),*product.logic] if rule else product.logic,
        limitations=[*product.limitations,notice.strip()],evidence=evidence,one_year_evidence=evidence,
        one_year_return_pct=evidence.return_pct if evidence else None,
        standard_mode_label=rule or 'Baseline — no added ADX/DI',one_year_note='2025-10-02 to 2026-10-02 exclusive; standalone 1% risk target, not guarded FTMO results.'
    ))

def label_product_payload(slug, mode, payload):
    if payload is None or slug not in MANAGED_SLUGS:return payload
    payload=dict(payload)
    if payload.get('configuration_release')!=VERSION:
        payload.update(evidence_status='Archived configuration',evidence_label='Archived previous configuration — '+str(payload.get('evidence_label') or payload.get('period','')),is_current_configuration=False)
        payload['notice']=HISTORICAL_NOTE+' '+str(payload.get('notice') or '')
    else:payload['is_current_configuration']=True
    return payload

def label_portfolio_payload(payload):
    if payload is None:return None
    payload=dict(payload)
    if payload.get('configuration_release')!=VERSION:
        payload['notice']=HISTORICAL_NOTE+' '+str(payload.get('notice') or '')
        payload.update(label='Archived pre-ADX/DI portfolio',evidence_status='Archived portfolio configuration',is_current_configuration=False)
    return payload


def verified_payload(product, mode, period, start, end):
    """Reuse audited release evidence; never regenerate it through a legacy path."""
    from .catalog import PACKAGE_ROOT
    from .evidence_cache import product_cache_path, product_trades_path, CACHE_ROOT
    path=product_cache_path(product.slug,mode,period)
    if not path.is_file():raise RuntimeError('No audited ADX/DI evidence for this window')
    p=json.loads(path.read_text(encoding='utf-8-sig'))
    if p.get('configuration_release')!=VERSION or mode!='standard':
        raise RuntimeError('Archived pre-ADX/DI configuration; use the frozen admission runner for current evidence')
    if p['available_from']!=str(start) or str(end) not in {p['end_exclusive'],p['available_to']}:
        raise RuntimeError('ADX/DI release evidence uses fixed windows; use its audited native runner for new dates')
    sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
    f=p['source_fingerprint']
    if sha(PACKAGE_ROOT/product.expert_source)!=f['expert_sha256'] or sha(PACKAGE_ROOT/product.set_source)!=f['settings_sha256']:
        raise RuntimeError('ADX/DI binary or settings changed after evidence publication')
    ledger=product_trades_path(product.slug,mode,period)
    if sha(ledger)!=f['cached_trades_sha256']:
        raise RuntimeError('ADX/DI cached trade ledger identity mismatch')
    report=CACHE_ROOT/'source-runs'/product.slug/mode/(period+'.htm')
    if sha(report)!=f['production_native_report_sha256']:
        raise RuntimeError('ADX/DI native report identity mismatch')
    rows=json.loads(ledger.read_text(encoding='utf-8-sig'))
    if len(rows)!=p['stats']['trades'] or abs(sum(r['net_profit'] for r in rows)-p['stats']['net_profit'])>.02:
        raise RuntimeError('ADX/DI native totals do not match the cached ledger')
    return p,rows
