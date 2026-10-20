"""Preserve earlier benchmarks while labelling the new DI-OFF client build.

This never runs MT5, changes inputs on an account, or replaces historical
statistics with a new binary's name. Current package and historical evidence
have separate receipts. Original public presentation is recoverably archived.
"""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parent
CLIENT=ROOT.parent.parent/'top 5'
ARCHIVE=ROOT/'historical-preservation-20261017'
SLUG='nasdaq-5m-candle-momentum'
EDITION='CLIENT-DI-OFF-20261017'
NOTICE=('CURRENT CLIENT BUILD: Nasdaq 5M DI agreement is OFF by default; EMA12, the 0.60%-of-price stop, '+
        'ATR x6 trailing from +1R and no fixed TP are unchanged. The delivered sizing policy uses the broker '+
        'minimum lot when selected risk is too small and CAN EXCEED your selected risk. '+
        'Every performance chart, table, custom estimate and historical screen on this page retains the '+
        '20 EARLIER-BUILD benchmarks: Nasdaq DI ON and skip-below-minimum sizing. '+
        'They are NOT backtests of the currently delivered DI-OFF/minimum-lot-override binaries. '+
        'Current build fingerprints and packaged inputs are shown separately. Demo validation is required.')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def value_hash(value):return hashlib.sha256(canonical(value)).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def historical_fields(payload):
    return {k:payload[k] for k in ('datasets','evidence','bots','built')}


def embedded_data(text):
    start=text.index('const DATA=')+len('const DATA=')
    payload,_=json.JSONDecoder().raw_decode(text[start:])
    return payload


def capture():
    """First call only; never overwrite a prior recoverable presentation."""
    receipt=ARCHIVE/'BEFORE.json'
    if receipt.exists():return read(receipt)
    payload=read(ROOT/'report-data.json')
    public=embedded_data((CLIENT/'Performance and Setup.html').read_text(encoding='utf-8-sig'))
    assert historical_fields(payload)==historical_fields(public),'Public/cached historical evidence already differs'
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    files={}
    for path in (CLIENT/'Performance and Setup.html',ROOT/'report-data.json',ROOT/'report.template.html',ROOT/'ea-details-cache.json'):
        destination=ARCHIVE/path.name
        assert not destination.exists(),'Refusing to overwrite archived evidence'
        shutil.copy2(path,destination)
        files[path.name]=digest(destination)
    before=dict(created_utc=datetime.now(timezone.utc).isoformat(),archived_files=files,
        historical_fields={k:value_hash(v) for k,v in historical_fields(payload).items()},
        datasets_sha256=value_hash(payload['datasets']),evidence_sha256=value_hash(payload['evidence']),
        old_nasdaq_di=payload['ea_details']['entries'][SLUG]['inputs']['InpRequireDIAgreement'])
    assert before['old_nasdaq_di']=='true','Expected historical DI-ON cache'
    save(receipt,before)
    return before


def transform(payload,manifest,manifest_sha):
    out=deepcopy(payload)
    assert out['licence']==manifest['licence'],'Licence changed; requires explicit renewal handling'
    rows={row['slug']:row for row in manifest['entries']}
    assert set(rows)=={b['slug'] for b in out['bots']}
    assert rows[SLUG]['inputs']['InpRequireDIAgreement']=='false','Current package is not DI OFF'
    assert 'MINIMUM LOT' in manifest['risk_policy'] and 'EXCEED' in manifest['risk_policy']
    old=historical_fields(out)
    out['riskPolicyRevision']=True
    out['strategyPolicyRevision']=True
    out['licenceEditionNote']=NOTICE
    out['benchmarkMetadata']=dict(status='HISTORICAL PRIOR-BUILD EVIDENCE',native_cases=20,
        nasdaq_di_agreement='ON',sizing='Round down; skip if below broker minimum',
        benchmark_end_exclusive='2026-09-30',current_binary_backtest=False,
        datasets_sha256=value_hash(out['datasets']),evidence_sha256=value_hash(out['evidence']))
    out['current_package']=dict(revision=EDITION,nasdaq_di_default='OFF',
        risk_policy=manifest['risk_policy'],manifest_sha256=manifest_sha,
        licence=deepcopy(manifest['licence']),
        bots=[{k:r[k] for k in ('slug','label','symbol','period','expert','ex5_sha256')} for r in manifest['entries']],
        ea_details={SLUG:dict(
            tagline='Opening momentum with EMA12; DI agreement is OFF by default in this client build.',
            current_rule='After the closed 09:30–09:35 New York M5 candle, direction uses the unchanged candle/EMA12 logic without the optional DI gate. The 0.60%-of-price stop, no fixed TP and ATR x6 trailing from +1R are unchanged. DI can be enabled explicitly in EA inputs; this package defaults it OFF.',
            historical_rule='The Nasdaq charts and statistics on this page used DI ON. Cached website descriptions below also describe the DI-ON reference, not this client default.')})
    out['ea_details']['inputs_basis']='CURRENT CLIENT PACKAGE INPUTS, not historical benchmark inputs'
    for slug,row in rows.items():
        out['ea_details']['entries'][slug]['inputs']=deepcopy(row['inputs'])
    assert historical_fields(out)==old,'Historical data/evidence/bot metadata must remain unchanged'
    return out


def render_cached(payload,template):
    safe=(json.dumps(payload,separators=(',',':'),ensure_ascii=False,allow_nan=False)
          .replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
          .replace('\u2028','\\u2028').replace('\u2029','\\u2029'))
    assert template.count('__DATA__')==1,'Unexpected report template'
    return template.replace('__DATA__',safe)


def main():
    before=capture()
    payload=read(ROOT/'report-data.json');manifest=read(ROOT/'manifest.json')
    for row in manifest['entries']:
        assert digest(CLIENT/row['expert'])==row['ex5_sha256'],'Current public binary/manifest mismatch'
    for key,value in historical_fields(payload).items():
        assert value_hash(value)==before['historical_fields'][key],('Earlier evidence changed',key)
    out=transform(payload,manifest,digest(ROOT/'manifest.json'))
    cache=deepcopy(out['ea_details'])
    save(ROOT/'ea-details-cache.json',cache)
    save(ROOT/'report-data.json',out)
    html=render_cached(out,(ROOT/'report.template.html').read_text(encoding='utf-8'))
    (CLIENT/'Performance and Setup.html').write_text(html,encoding='utf-8')
    embedded=embedded_data(html)
    assert historical_fields(embedded)==historical_fields(payload)
    result=dict(status='PASS',revision=EDITION,historical_fields_unchanged=True,
        historical_fields_before=before['historical_fields'],
        historical_fields_after={k:value_hash(v) for k,v in historical_fields(out).items()},
        current_manifest_sha256=digest(ROOT/'manifest.json'),
        current_nasdaq_ex5_sha256=next(r['ex5_sha256'] for r in manifest['entries'] if r['slug']==SLUG),
        current_nasdaq_di='false',historical_nasdaq_di='true',
        public_html_sha256=digest(CLIENT/'Performance and Setup.html'),
        native_cases=20,new_backtests_claimed=False)
    save(ROOT/'DI_REPORT_VERIFICATION.json',result)
    print('Preserved all 20 historical datasets/evidence exactly; current DI-OFF package metadata rendered separately.')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='capture':
        print(json.dumps(capture(),indent=2))
    else:main()
