"""Sequential isolated native MT5 entry-filter screen. Never live deployment."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,io,json,os,re,shutil,subprocess,time,sys
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(B.parent/'EA store'))
sp=importlib.util.spec_from_file_location('native_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER;DEST=T/'MQL5/Experts/AAA Research/ADXDI_NEXT20261003';OUT=R/'native'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
WINDOWS={'1y':('2025.10.02','2026.10.02'),'3m':('2026.07.02','2026.10.02'),
         '3y':('2023.10.02','2026.10.02'),'5y':('2021.10.02','2026.10.02')}
CORE={'BASE':(0,False,0),'DI_ONLY':(0,True,0),'ADX20':(20,False,0),'ADX25':(25,False,0),'ADX20_DI':(20,True,0),'ADX25_DI':(25,True,0)}
def variants(key):
    if key=='trio':return {'BASE':CORE['BASE'],**{prefix+'_'+v:(a,d,module) for prefix,module in [('A',1),('B',2)] for v,(a,d,m) in CORE.items() if v!='BASE'}}
    if key=='squeeze':return {**CORE,'ADX_RISING':(-1,False,0),'ADX_RISING_DI':(-1,True,0)}
    return CORE
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def status(s):save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=s));print(s,flush=True)
def compile_all(bots):
    h.free();build={}
    for key,b in bots.items():
        folder=R/'EA'/key;src=folder/'Research.mq5';log=folder/'compile.log';began=time.time()
        subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-3500:]
        assert src.with_suffix('.ex5').stat().st_mtime>=began-2
        target=DEST/key;target.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src.with_suffix('.ex5'),target/'Research.ex5');shutil.copy2(b['original'],target/'Original.ex5')
        build[key]=dict(source_sha=sha(src),binary_sha=sha(src.with_suffix('.ex5')),original_sha=sha(Path(b['original'])),
                        helpers={p.name:sha(p) for p in folder.glob('*.mqh')},compile_tail=h.text(log)[-350:])
        assert build[key]['original_sha']==b['original_sha'];status('COMPILED '+key+': 0 errors, 0 warnings')
    save(R/'BUILD.json',build)
def streaks(v):
    best={1:0,-1:0};last=0;n=0
    for x in v:
        sign=int(np.sign(x));n=n+1 if sign==last else 1;last=sign
        if sign:best[sign]=max(best[sign],n)
    return dict(max_win_streak=best[1],max_loss_streak=best[-1])
def stats(rows,native,start,end):
    v=np.array([r['net_profit'] for r in rows],dtype=float);gp=v[v>0].sum();gl=-v[v<0].sum()
    daily=pd.Series(v,index=[r['close_time'][:10] for r in rows],dtype=float).groupby(level=0).sum()
    cal=pd.date_range(start.replace('.','-'),pd.Timestamp(end.replace('.','-'))-pd.Timedelta(days=1))
    daily=daily.reindex(cal.strftime('%Y-%m-%d'),fill_value=0).to_numpy();balance=10000+np.cumsum(daily)
    opening=np.r_[10000,balance[:-1]];ret=np.divide(daily,opening,out=np.zeros_like(daily),where=opening>0);sd=ret.std(ddof=1)
    bal=np.r_[10000,10000+np.cumsum(v)];peak=np.maximum.accumulate(bal)
    return dict(net=float(v.sum()),return_pct=float(v.sum()/100),pf=float(gp/gl) if gl else None,
                win_pct=float((v>0).mean()*100) if len(v) else 0,trades=len(v),trades_month=len(v)/(len(cal)/365.2425*12),
                trades_weekday=len(v)/sum(cal.dayofweek<5),equity_dd_pct=native['equity_dd_pct'],
                closed_dd_pct=float(np.max((peak-bal)/peak)*100),sharpe=float(ret.mean()/sd*np.sqrt(365.2425)) if sd else None,
                history_quality=native['history_quality'],commission=float(sum(r['commission'] for r in rows)),
                swap=float(sum(r['swap'] for r in rows)),**streaks(v))
def trio_rows(b,folder,began):
    path=COMMON/'Calyx3WayGold/ledger.csv';assert path.exists() and path.stat().st_mtime>=began-2
    raw=path.read_bytes();(folder/'positions.csv.gz').write_bytes(gzip.compress(raw,mtime=0));df=pd.read_csv(io.BytesIO(raw))
    rows=[]
    for r in df.to_dict('records'):
        assert r['position_id']>0 and r['close_epoch']>0 and abs(r['volume']-r['closed_volume'])<1e-6,r
        rows.append(dict(position_id=int(r['position_id']),module=r['module'],number=len(rows)+1,ea=b['label'],symbol=b['symbol'],
          side='Long' if r['side']>0 else 'Short',volume=float(r['volume']),
          open_time=datetime.fromtimestamp(r['open_epoch'],timezone.utc).replace(tzinfo=None).isoformat(),
          close_time=datetime.fromtimestamp(r['close_epoch'],timezone.utc).replace(tzinfo=None).isoformat(),
          open_price=float(r['open_price']),close_price=float(r['close_price']),gross_profit=float(r['gross_profit']),
          commission=float(r['commission']),swap=float(r['swap']),fee=float(r['fee']),net_profit=float(r['net_profit']),
          actual_risk=float(r['actual_risk']),requested_risk=float(r['requested_risk']),source='Native MT5 position-ID ledger, partial closes grouped'))
    return sorted(rows,key=lambda r:(r['close_time'],r['position_id']))
def case(key,b,variant='BASE',period='1y',original=False):
    tag=f'{key}-{period}-'+('ORIGINAL' if original else variant);folder=OUT/tag;folder.mkdir(parents=True,exist_ok=True)
    start,end=WINDOWS[period];level,di,module=variants(key)[variant];inputs=dict(b['inputs'])
    if not original:inputs.update(InpStudyADXGate=str(3 if level<0 else (1 if level else 0)),InpStudyADXLevel=str(level if level>0 else 20),
        InpStudyDI=str(di).lower(),InpStudyTF=str(b['tf']),InpStudyModule=str(module),InpStudyTag=tag)
    frozen=dict(tag=tag,inputs=inputs,symbol=b['symbol'],period=b['period'],start=start,end=end,deposit=10000,model=4,delay_ms=150,
                original=original,protocol_sha=sha(R/'PROTOCOL.txt'),build=load(R/'BUILD.json')[key])
    if (folder/'manifest.json').exists():assert load(folder/'manifest.json')==frozen,'Frozen config changed'
    else:save(folder/'manifest.json',frozen)
    if (folder/'result.json').exists():return load(folder/'result.json')
    h.free();setname='adxdinext-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in inputs.items())+'\n'
    (folder/setname).write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    rp=T/'reports/adxdi-next20261003'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
    ini=folder/'tester.ini';expert='Original' if original else 'Research'
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ADXDI_NEXT20261003\\{key}\\{expert}
ExpertParameters={setname}
Symbol={b['symbol']}
Period={b['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\adxdi-next20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();status('START '+tag)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    save(R/'owned-process.json',dict(pid=proc.pid,key=tag,executable=str(T/'terminal64.exe')))
    try:proc.wait(timeout=2700)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated case timed out: '+tag)
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report '+tag
    fatal=[l for l in journal.splitlines() if re.search(r'initialization failed|start time changed|invalid volume|stop out|margin call|access violation|array out of range|zero divide|order rejected',l,re.I)]
    assert not fatal,'Invalid run; inspect journal '+tag
    rb=h._read_report(rp);assert all(x in rb for x in (b['symbol'],b['period'],start,end))
    actual=h._report_inputs(rp);mismatch=[k for k,v in inputs.items() if k not in actual or not h._same_setting(v,actual[k])];assert not mismatch,(tag,mismatch)
    from app.mt5_evidence_jobs import _metric,_number
    native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
    rows=trio_rows(b,folder,began) if key=='trio' else h._native_trades(rp,tag)
    if key!='trio':assert len(rows)==native['trades']
    assert abs(sum(r['net_profit'] for r in rows)-native['net_profit'])<.25
    audit={}
    if not original:
        p=COMMON/f'ADXDI_NEXT20261003-{tag}.csv';assert p.exists() and p.stat().st_mtime>=began-2
        raw=p.read_bytes();df=pd.read_csv(io.BytesIO(raw));g=df[df.event=='gate'];valid=g[g.valid==1]
        assert (valid.epoch>=valid.bar_epoch+valid.tf_seconds).all()
        if variant!='BASE':
            allowed=g[g.allowed==1];assert (allowed.valid==1).all()
            if level>0:assert (allowed.adx>=level).all()
            if level<0:assert (allowed.adx>allowed.previous_adx).all()
            if di:assert (((allowed.direction>0)&(allowed.plus_di>allowed.minus_di))|((allowed.direction<0)&(allowed.minus_di>allowed.plus_di))).all()
            if module:assert (g.module==module).all()
        audit=dict(placement_candidates=len(g),admitted=int(g.allowed.sum()),rejected=int((g.allowed==0).sum()),missing_indicator=int((g.valid==0).sum()))
        (folder/'audit.csv.gz').write_bytes(gzip.compress(raw,mtime=0))
    (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    (folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(rows).encode(),mtime=0))
    result=dict(tag=tag,ea=key,label=b['label'],variant=variant,window=period,original=original,start=start,end_exclusive=end,
        stats=stats(rows,native,start,end),native=native,audit=audit,seconds=time.time()-began,
        tick_notes=sorted(set(l for l in journal.splitlines() if re.search(r'real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded',l,re.I)))[:20],
        known_stop_modify_rejections=journal.count('stop modification failed'),report_sha=sha(rp))
    save(folder/'result.json',result);status('DONE '+tag+' '+json.dumps(result['stats']));return result
def parity(a,b):
    rows=lambda t:json.loads(gzip.decompress((OUT/t/'trades.json.gz').read_bytes()))
    x=rows(a['tag']);y=rows(b['tag']);fields=['open_time','close_time','side','volume','open_price','close_price','commission','swap','net_profit']
    assert len(x)==len(y) and all(all(i[k]==j[k] for k in fields) for i,j in zip(x,y)),('Parity failed',a['tag'])
    return dict(trades=len(x),identical_entry_exit_volume_costs=True,fields=fields)
def nominate(results):
    base=next(r['stats'] for r in results if r['variant']=='BASE');eligible=[]
    for r in results:
        s=r['stats']
        if r['variant']!='BASE' and s['trades']>=30 and s['net']>0 and s['pf'] is not None and s['pf']>=1.2 and s['pf']>(base['pf'] or 0) and s['sharpe'] is not None and s['sharpe']>=(base['sharpe'] or 0):eligible.append(r)
    eligible.sort(key=lambda r:(r['stats']['pf'],r['stats']['sharpe'],r['stats']['return_pct']/max(r['stats']['equity_dd_pct'],.01),r['stats']['trades']),reverse=True)
    return eligible[0]['variant'] if eligible else None
def main():
    bots=load(R/'bots.json');frozen=dict(bots=bots,variants={k:variants(k) for k in bots},windows=WINDOWS,protocol_sha=sha(R/'PROTOCOL.txt'),filter_sha=sha(R/'EA/StudyFilter.mqh'),full_pipeline=False,promotion=False)
    frozen=json.loads(json.dumps(frozen))
    if (R/'run-config.json').exists():assert load(R/'run-config.json')==frozen
    else:save(R/'run-config.json',frozen)
    if not (R/'BUILD.json').exists():compile_all(bots)
    build=load(R/'BUILD.json')
    for key,b in bots.items():
        assert sha(R/'EA'/key/'Research.mq5')==build[key]['source_sha'] and sha(Path(b['original']))==b['original_sha']
        assert {p.name:sha(p) for p in (R/'EA'/key).glob('*.mqh')}==build[key]['helpers']
        assert all(sha(Path(p))==digest for p,digest in b['helpers'].items())
    results=[];parities={};nominations={}
    for key,b in bots.items():
        original=case(key,b,original=True);base=case(key,b);parities[key]=parity(original,base);save(R/'PARITY.json',parities)
        status('PARITY '+key+': '+str(base['stats']['trades'])+' identical trades');rows=[base]
        for v in variants(key):
            if v!='BASE':rows.append(case(key,b,v))
            save(R/'PROGRESS.json',results+rows)
        chosen=nominate(rows);nominations[key]=dict(variant=chosen,retrospective_only=True,reason='Frozen eligibility/ranking rule' if chosen else 'No qualifying PF/Sharpe improvement with >=30 trades')
        save(R/'NOMINATIONS.json',nominations);results+=rows
        results.append(case(key,b,period='3m',original=True))
        if chosen:
            for period in ('3m','3y','5y'):
                if period!='3m':results.append(case(key,b,period=period,original=True))
                results.append(case(key,b,chosen,period=period));save(R/'PROGRESS.json',results)
        save(R/'PROGRESS.json',results);status('EA COMPLETE '+key+' nominee='+str(chosen))
    save(R/'SUMMARY.json',results);status('COMPLETE five screens; no production deployment')
if __name__=='__main__':main()
