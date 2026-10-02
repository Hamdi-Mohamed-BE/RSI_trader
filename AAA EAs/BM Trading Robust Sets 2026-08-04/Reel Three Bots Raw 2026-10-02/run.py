"""Sequential isolated MT5 research. Does not attach EAs or change live terminals."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, json, os, re, shutil, subprocess, sys, time
import pandas as pd

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
DEST=TESTER/'MQL5/Experts/AAA Research/ReelThree20261002'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/ReelThree20261002'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_read_report,_metric,_number,_report_inputs,_same_setting
SPECS={'range':('DE40Range','DE30',1002001),'atr':('GoldATRCandle','XAUUSD',1002002),'donchian':('GoldDonchian','XAUUSD',1002003),'portfolio':('ThreeBotPortfolio','XAUUSD',1002001),'portfolio-percent':('ThreeBotPortfolio','XAUUSD',1002001)}

def save(p,x):
    p.write_text(json.dumps(x,indent=2,allow_nan=False,default=str),encoding='utf-8')

def read(p):
    b=p.read_bytes()
    return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')

def free():
    p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode==0 and str(TESTER).lower() not in p.stdout.lower(),'Research tester busy; no existing process stopped'
    profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr')),'Research profile must be empty'

def compile_ea(name):
    free(); expert,_,_=SPECS[name]; log=ROOT/(name+'-compile.log'); began=time.time()
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"EA"/(expert+".mq5")}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
    assert '0 errors, 0 warnings' in read(log),read(log)
    exe=ROOT/'EA'/(expert+'.ex5');assert exe.stat().st_mtime>=began-2
    DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(exe,DEST/exe.name)
    print('COMPILE',name,'0 errors / 0 warnings',flush=True)

def logs():
    return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))

def streaks(p):
    mw=ml=w=l=0
    for x in p:
        w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
    return mw,ml

def run(name,window):
    free();expert,symbol,magic=SPECS[name]
    windows={'1y':('2025.10.01','2026.10.02','2025.06.01'),
             '6m':('2026.04.01','2026.10.02','2026.01.02'),
             'smoke':('2026.09.01','2026.09.15','2026.07.01')}
    start,end,warm=windows[window]
    tag=name+'-'+window;out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
    assert not (out/'run.json').exists(),'Existing result preserved; choose a fresh tag'
    vals={'InpFixedRiskUSD':100,'InpMagic':magic,'InpTradeFrom':start+' 00:00:00','InpTag':tag,'InpBrokerUtcOffsetHours':0,'InpSeasonalReferenceClock':'true','InpATRIncludesSignal':'true','InpMaximumDeviationPoints':1000}
    if name.startswith('portfolio'):
        vals.update(InpRiskPercent=1 if name=='portfolio-percent' else 0,InpRangeSymbol='DE30',InpGoldSymbol='XAUUSD')
    sourcefiles=[ROOT/'EA'/(expert+'.mq5'),ROOT/'EA'/'ReelRules.mqh',ROOT/'EA'/(expert+'.ex5')]
    if name.startswith('portfolio'):sourcefiles.extend([ROOT/'EA/PortfolioModules.mqh',ROOT/'build_portfolio.py'])
    frozen_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sourcefiles}
    (out/'sources').mkdir(exist_ok=True)
    for p in sourcefiles:shutil.copy2(p,out/'sources'/p.name)
    body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n';setname='rr-'+tag+'.set'
    (out/setname).write_text(body);(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body)
    report=TESTER/'reports/reel-three-20261002'/(tag+'.htm');report.parent.mkdir(parents=True,exist_ok=True)
    header=read(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ReelThree20261002\\{expert}
ExpertParameters={setname}
Symbol={symbol}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\reel-three-20261002\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    offsets={p:p.stat().st_size for p in logs()};began=time.time();print('START',tag,flush=True)
    save(ROOT/'status.json',{'running':tag,'began':datetime.now().isoformat()})
    proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
    try:proc.wait(timeout=3600)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=15);raise RuntimeError('Owned isolated research test timed out')
    journal=''
    for p in logs():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert report.exists() and report.stat().st_mtime>=began-2,'No fresh tester report'
    txt=_read_report(report);actual=_report_inputs(report)
    expected=vals|{'InpTradeFrom':int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
    assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in expected.items()),('Inputs mismatch',actual)
    assert 'testing with execution delay 150 milliseconds' in journal
    fatal=re.findall(r'[^\r\n]*(?:initialization failed|critical error|access violation|testing start time changed|not enough history)[^\r\n]*',journal,re.I)
    assert not fatal,fatal[:5]
    for suffix in ['trades.csv','equity.csv']:
        src=COMMON/(tag+'-'+suffix);assert src.exists() and src.stat().st_mtime>=began-2
        shutil.copy2(src,out/suffix)
    shutil.copy2(report,out/'report.htm')
    for p in report.parent.glob(tag+'*.png'):shutil.copy2(p,out/p.name)
    d=pd.read_csv(out/'trades.csv');metrics=_native_metrics(report)
    if len(d):
        assert ((d.volume-d.closed_volume).abs()<1e-7).all(),'Open-volume mismatch'
        assert abs(d.net_profit.sum()-metrics['net_profit'])<.03,'Ledger/report mismatch'
        assert (d.open_epoch>=expected['InpTradeFrom']).all(),'Warm-up entry found'
    pnl=d.sort_values(['close_epoch','position_id']).net_profit.to_numpy();gp=float(pnl[pnl>0].sum());gl=float(-pnl[pnl<0].sum())
    metrics.update(trades=len(d),win_rate_pct=float((pnl>0).mean()*100) if len(d) else 0,profit_factor=gp/gl if gl else None,
                   equity_dd_relative_pct=_number(_metric(txt,'Equity Drawdown Relative')),max_win_streak=streaks(pnl)[0],max_loss_streak=streaks(pnl)[1],commission=float(d.commission.sum()),swap=float(d.swap.sum()))
    data={'name':name,'symbol':symbol,'start':start,'end_exclusive':end,'warmup':warm,'model':4,'execution_delay_ms':150,'requested_risk_usd':100,'deposit':10000,'seconds':round(time.time()-began,2),'metrics':metrics,'inputs':actual,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'EA'/(expert+'.mq5'),ROOT/'EA'/'ReelRules.mqh',ROOT/'EA'/(expert+'.ex5')]},'summary':re.findall(r'RR_SUMMARY[^\r\n]*',journal),'tick_notes':sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded)[^\r\n]*',journal)))[:30]}
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==frozen_hashes[p.name] for p in sourcefiles),'Source changed during test'
    data['source_hashes']=frozen_hashes
    if name.startswith('portfolio'):
        data['risk_percent_balance']=vals['InpRiskPercent']
        data['portfolio_summary']=re.findall(r'PORTFOLIO_SUMMARY[^\r\n]*',journal)
    save(out/'run.json',data);save(ROOT/'status.json',{'finished':tag,'metrics':metrics});print('DONE',tag,json.dumps(metrics),flush=True)

if __name__=='__main__':
    mode,name=sys.argv[1:3]
    if mode=='compile':compile_ea(name)
    elif mode=='run':run(name,sys.argv[3])
    else:raise ValueError(mode)
