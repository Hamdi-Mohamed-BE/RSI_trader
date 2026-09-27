"""Offline packaging/publication of the user-selected QL_ATR preset; never opens MT5."""
from pathlib import Path
import gzip, hashlib, json, os, shutil, sys
from datetime import date, datetime, timezone

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
STORE = BASE.parent / 'EA store'
RESEARCH = BASE / 'Nasdaq 5M QuantLab Style Research 2026-09-25'
NAME = 'Nasdaq 5M DI Wide ATR EA'
SET = BASE / 'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2), encoding='utf-8')
def backup(p):
    dest = ROOT / 'before' / p.relative_to(BASE.parent)
    if p.is_dir():
        if not dest.exists(): shutil.copytree(p, dest)
    elif p.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
def prepare():
    for p in [BASE/'_Auto Deploy/Install-BMTradingPortfolio.ps1',
              BASE/'FTMO Thirteen EA Deployment 2026-09-27', STORE/'app/catalog.py',
              STORE/'data/evidence-cache/v1/products/nasdaq-5m-candle-momentum',
              STORE/'data/evidence-cache/v1/source-runs/nasdaq-5m-candle-momentum',
              STORE/'data/evidence-cache/v1/portfolio', STORE/'data/evidence-cache/v1/manifest.json',
              STORE/'data/evidence-cache/v1/consistency-audit.json', *BASE.glob('*.bat')]: backup(p)
    ea = ROOT/'EA'; ea.mkdir(exist_ok=True)
    src = RESEARCH/'EA/Nasdaq 5M QuantLab Style Research EA.mq5'
    build = json.loads((RESEARCH/'native/build.json').read_text())
    assert sha(src) == build['source_sha256'] and sha(src.with_suffix('.ex5')) == build['ex5_sha256']
    for suffix in ('.mq5', '.ex5'):
        shutil.copy2(src.with_suffix(suffix), ea/(NAME+suffix))
    for p in (RESEARCH/'EA').glob('*.mqh'): shutil.copy2(p, ea/p.name)
    setting = RESEARCH/'native/n5ql-USTEC-QL_ATR-1y/n5ql-USTEC-QL_ATR-1y.set'
    shutil.copy2(setting, SET)
    inputs = dict(l.split('=',1) for l in SET.read_text().splitlines() if '=' in l)
    assert inputs['InpRequireDIAgreement']=='true' and inputs['InpStopMode']=='2'
    assert inputs['InpUseATRTrailing']=='true' and inputs['InpUseFixedTarget']=='false'
    manifest = dict(version='DI-WIDE-ATR-20260928', expert=str((ea/(NAME+'.ex5')).relative_to(BASE)),
                    expert_sha=sha(ea/(NAME+'.ex5')), settings=str(SET.relative_to(BASE)), settings_sha=sha(SET), inputs=inputs,
                    byte_identical_to_tested_binary=True, source_sha=sha(src), live_terminal_changed=False,
                    pipeline_approved=False, selection='Explicit user choice; retrospective research, not FTMO validation')
    write(ROOT/'SELECTION.json', manifest)
    print('PREPARED identical tested binary and SET; rollback snapshot retained', flush=True)
def publish():
    assert os.getenv('EA_STORE_DISABLE_MT5') == '1'
    sys.path[:0] = [str(STORE), str(STORE/'tools')]
    import precompute_evidence_cache as P
    from app.mt5_evidence_jobs import _report_inputs, _same_setting
    product = next(p for p in P.get_sellable_catalog() if p.slug=='nasdaq-5m-candle-momentum')
    selected = json.loads((ROOT/'SELECTION.json').read_text())
    assert sha(BASE/product.dynamic_expert_source) == selected['expert_sha']
    checks=[]
    for period, months in P.PERIOD_MONTHS.items():
        end=date(2026,9,25); start=P.subtract_months(end,months)
        folder=RESEARCH/f'native/n5ql-USTEC-QL_ATR-{period}'
        meta=json.loads((folder/'run.json').read_text())
        report, metadata=P.source_paths(product,'dynamic',period)
        report.parent.mkdir(parents=True, exist_ok=True)
        raw=gzip.decompress(next(folder.glob('*.htm.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==meta['report_sha256']
        assert meta['ok'] and meta['start']==start.strftime('%Y.%m.%d') and meta['end_exclusive']==end.strftime('%Y.%m.%d')
        assert sha(next(folder.glob('*.set')))==selected['settings_sha']
        report.write_bytes(raw)
        actual=_report_inputs(report)
        assert all(k in actual and _same_setting(v,actual[k]) for k,v in selected['inputs'].items())
        fingerprint=P.source_fingerprint(product,'dynamic',start,end)
        fingerprint.update(source_report_sha256=meta['report_sha256'],
                           original_expert_name=meta['expert'], binary_identity='Exact copy of tested QL_ATR EX5')
        P.write_json(metadata,fingerprint)
        payload,trades=P.product_payload(product,'dynamic',period,start,end,report)
        assert payload['stats']['trades']==len(trades)==meta['metrics']['trades']
        assert abs(payload['stats']['net_profit']-meta['metrics']['net_profit'])<0.011
        payload['notice']='User-selected DI + wide 0.60% price stop + ATR6 trail from +1R; no TP, overnight/weekend holding. Native Model 4, 150 ms delay, recorded costs. Real ticks begin January 2026; earlier ticks are generated. Retrospective selection, not a clean holdout or FTMO pass forecast.'
        payload['source_fingerprint']=fingerprint
        P.write_json(P.product_cache_path(product.slug,'dynamic',period),payload)
        P.write_json(P.product_trades_path(product.slug,'dynamic',period),trades)
        checks.append(dict(period=period,stats=payload['stats'],report_sha256=meta['report_sha256']))
        print('PUBLISHED',period,len(trades),payload['stats']['return_pct'],flush=True)
    write(ROOT/'WEBSITE_PUBLICATION.json',dict(checked=checks,live_deployment_verified=False))
if __name__=='__main__':
    {'prepare':prepare,'publish':publish}[sys.argv[1]]()
