"""Frozen current-preset comparison, isolated tester only; no live or store writes."""
import os, sys, json, importlib.util, shutil, hashlib, gzip, re, inspect
from pathlib import Path
os.environ['EA_STORE_DISABLE_MT5']='1'
ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
spec=importlib.util.spec_from_file_location('baseline',PACKAGE/'No Wick Candle Raw 2026-09-25/run_nw.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from app.catalog import get_catalog
from app.mt5_evidence_jobs import _set_values, _materialized_values
import app.mt5_evidence_jobs as parser
# Keep actual exit deal IDs: FIFO fragments are not extra winning/losing trades.
code=inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,','"exit_deal": cells[1], "number": len(trades) + 1,')
scope=dict(vars(parser));exec(code,scope)
def closing_deals(path,label):
    fragments=scope['_native_trades'](path,label);grouped={}
    for t in fragments:
        key=t['exit_deal']
        if key not in grouped:grouped[key]=dict(t);continue
        g=grouped[key]
        for field in ('volume','gross_profit','commission','swap','total_costs','net_profit'):g[field]+=t[field]
        g['open_time']=min(g['open_time'],t['open_time'])
    out=list(grouped.values())
    for i,t in enumerate(out):
        t['number']=i+1;t['result']='Win' if t['net_profit']>0 else 'Loss' if t['net_profit']<0 else 'Flat'
    return out
b._native_trades=closing_deals
PRIVATE=b.CONFIG['login']
b.ROOT=ROOT;b.OUT=ROOT/'native';b.STATUS=b.OUT/'status.json'
b.CONFIG.update(periods={'3m':'2026.06.30','6m':'2026.03.30'},end_date='2026.09.30',deposit=10000,
 currency='USD',model=4,execution_delay_ms=150,profile='Calyx Research Empty',timeout_seconds=3600,
 expert_dir='CalyxRecent20260930')
SLUGS=['gold-overnight-value-area','3-way-gold','xau-rsi-vwap','nasdaq-overnight',
 'us100-h1-orb-13utc','usdjpy-london-open-momentum','orb-volume-profile',
 'nasdaq-5m-candle-momentum','btc-top-down-fvg-liquidity','us100-month-end-flow',
 'orb-volume-profile-volume-confirmed','lta-volume-profile']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():
    if (ROOT/'selection.json').exists():return json.loads((ROOT/'selection.json').read_text())
    rows=[]
    products={p.slug:p for p in get_catalog()}
    for slug in SLUGS:
        p=products[slug]
        mode='dynamic' if p.recommended_dynamic_mode else 'safe' if p.recommended_safe_mode else 'standard'
        ex=PACKAGE/(p.dynamic_expert_source if mode=='dynamic' else p.expert_source)
        st=PACKAGE/(p.dynamic_set_source if mode=='dynamic' else (p.safe_set_source or p.set_source) if mode=='safe' else p.set_source)
        dst=ROOT/'snapshot'/slug;dst.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ex,dst/'selected.ex5');shutil.copy2(st,dst/'original.set')
        inputs=_materialized_values(_set_values(st,mode=='safe'))
        assert inputs and inputs.get('InpAdaptivePortfolioControls','false').lower()=='false'
        (dst/'inputs.json').write_text(json.dumps(inputs,indent=2))
        source=ex.with_suffix('.mq5')
        rows.append(dict(slug=slug,label=p.label,mode=mode,symbol=p.canonical,period=p.timeframe,
          expert=str(ex),set=str(st),ex5_sha256=sha(ex),set_sha256=sha(st),
          source_sha256=sha(source) if source.exists() else None,inputs=inputs,
          limitations=p.limitations,risk_note=p.risk_note))
    (ROOT/'selection.json').write_text(json.dumps(rows,indent=2))
    return rows
def main():
    rows=freeze()
    assert not b.isolated_running() and not b.port_3000_busy(),'Tester is occupied; leave other work alone'
    profile=b.TESTER/'MQL5/Profiles/Charts'/b.CONFIG['profile']
    assert profile.is_dir() and not list(profile.glob('*.chr'))
    common=b.text(b.TESTER/'Config/common.ini')
    assert int(re.search(r'(?im)^Login\s*=\s*(\d+)',common).group(1))==int(PRIVATE)
    del common
    b.OUT.mkdir(exist_ok=True)
    for row in rows:
        slug=row['slug'];dest=b.TESTER/'MQL5/Experts'/b.CONFIG['expert_dir'];dest.mkdir(exist_ok=True)
        src=ROOT/'snapshot'/slug/'selected.ex5';assert sha(src)==row['ex5_sha256']
        shutil.copy2(src,dest/(slug+'.ex5'))
        b.CONFIG.update(expert_file=slug+'.ex5',period=row['period'],common_inputs=row['inputs'],variants={slug:{'inputs':{}}})
        for period in b.CONFIG['periods']:
            done=b.OUT/f"nw-{row['symbol']}-{slug}-{period}"/'run.json'
            if done.exists() and json.loads(done.read_text()).get('audited'):continue
            m=b.run_case(row['symbol'],slug,period)
            folder=b.OUT/m['case'];report=b.REPORT_DIR/(m['case']+'.htm')
            actual=b._report_inputs(report)
            missing=[k for k,v in row['inputs'].items() if k not in actual or not b._same_setting(v,actual[k])]
            trades=closing_deals(report,m['case'])
            (folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
            assert not missing,missing
            assert len(trades)==m['metrics']['trades']
            assert abs(sum(t['net_profit'] for t in trades)-m['metrics']['net_profit'])<=max(.05,len(trades)*.011)
            assert not m['journal_flags']['init_failed'] and not m['journal_flags']['critical']
            j=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
            m['tick_notes']=sorted({line for line in j.splitlines() if any(k in line.lower() for k in ('real ticks begin','real ticks absent','ticks discarded','tick generation'))})[:30]
            m['audited']=True;m['ex5_sha256']=row['ex5_sha256'];m['trades_sha256']=sha(folder/'trades.json.gz')
            m['metrics']['relative_equity_dd_pct']=b._number(b._metric(b._read_report(report),'Equity Drawdown Relative'))
            done.write_text(json.dumps(m,indent=2))
    b.summary();b.status(state='ALL DONE',event='All current-preset tests audited')
if __name__=='__main__':main()
