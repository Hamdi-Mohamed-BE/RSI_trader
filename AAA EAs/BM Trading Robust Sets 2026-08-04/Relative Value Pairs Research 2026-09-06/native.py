"""Native multi-symbol execution validation in a dedicated portable DEMO tester."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, time, re
from datetime import datetime
import pandas as pd
import numpy as np
from research import ROOT,PAIRS,BASE,load_pair,features,dump

TESTER=ROOT.parent/'_Backtests'/'MT5-DMC-20260811'
SOURCE=ROOT/'EA'/'Calyx Relative Value Pairs EA.mq5'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes'/'Terminal'/'Common'/'Files'/'CalyxPairs'
EXPERT='Calyx Relative Value'
spec=importlib.util.spec_from_file_location('report_parser',ROOT.parent/'US100 Momentum Continuation Research 2026-08-31'/'Analyze-Reports.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def compile_ea():
    log=SOURCE.with_suffix('.compile.log')
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    out=log.read_text(encoding='utf-16')
    print(out.strip().splitlines()[-1],flush=True)
    if '0 errors, 0 warnings' not in out:raise RuntimeError('Compilation failed or warnings remain')
    target=TESTER/'MQL5'/'Experts'/EXPERT;target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE.with_suffix('.ex5'),target/SOURCE.with_suffix('.ex5').name)

def config(pair,c,case):
    q=json.loads((ROOT/'Data'/f'{pair}-quality.json').read_text())['costs']
    meta=json.loads((ROOT/'Data'/'metadata.json').read_text())['symbols']
    a,b=PAIRS[pair]
    return dict(InpSymbolA=a,InpSymbolB=b,InpTimeframeMinutes=c['tf'],InpWindow=c['window'],InpModel=c['model'],InpEntryZ=c['entry'],
        InpSession=c['session'],InpStopMode=c['stop'],InpExitMode=c['exit'],InpRR=c['rr'],InpManagement=c['manage'],InpDirection=c['direction'],
        InpHoldHours=c['hold'],InpRiskPercent=1.,InpServerUTCOffsetHours=0,InpSpreadFloorA=q[0]['zero_spread_floor_points']*meta[a]['point'],
        InpSpreadFloorB=q[1]['zero_spread_floor_points']*meta[b]['point'],InpMagic=969060201,InpCase=case)

def run(pair,label,c,stage='test',model=0,execution=-1):
    start,end={'smoke':('2025.09.01','2025.10.01'),'test':('2025.09.01','2026.09.01'),'full':('2023.09.01','2026.09.01'),'recent':('2026.01.01','2026.09.01')}[stage]
    case=f'{pair}-{label}-{stage}-model{model}'
    if execution!=-1:case+=f'-delay{execution}'
    params=config(pair,c,case)
    fingerprint=hashlib.sha256((SOURCE.read_text()+json.dumps(params,sort_keys=True)+start+end+str(model)+('random-1' if execution==-1 else f'fixed-{execution}')).encode()).hexdigest()
    out=ROOT/'Native'/case;out.mkdir(parents=True,exist_ok=True)
    done=out/'result.json'
    if done.exists():
        row=json.loads(done.read_text())
        if row['fingerprint']==fingerprint:return row
    (ROOT/'Sets').mkdir(exist_ok=True)
    st='\n'.join(f'{k}={v}' for k,v in params.items())+'\n'
    (ROOT/'Sets'/(case+'.set')).write_text(st,encoding='utf-8')
    (TESTER/'MQL5'/'Profiles'/'Tester'/(case+'.set')).write_text(st,encoding='utf-8')
    reportdir=TESTER/'reports'/'calyx-pairs';reportdir.mkdir(parents=True,exist_ok=True)
    report=reportdir/(case+'.htm')
    if report.exists():report.rename(report.with_name(case+f'.old-{time.time_ns()}.htm'))
    job=TESTER/'backtest-configs'/'calyx-pairs';job.mkdir(parents=True,exist_ok=True)
    ini=job/(case+'.ini')
    ini.write_text(f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert={EXPERT}\\Calyx Relative Value Pairs EA
ExpertParameters={case}.set
Symbol={PAIRS[pair][0]}
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode={execution}
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\calyx-pairs\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    agentlog=TESTER/'Tester'/'Agent-127.0.0.1-3000'/'logs'/(datetime.now().strftime('%Y%m%d')+'.log')
    offset=agentlog.stat().st_size if agentlog.exists() else 0
    print('NATIVE START',case,flush=True);t0=time.monotonic()
    try:
        subprocess.run(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',timeout=240 if model==4 else 900,creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired:
        dump(out/'unavailable.json',dict(pair=pair,model=model,status='no_report_within_bounded_history_wait',timeout_seconds=240 if model==4 else 900,case=case))
        raise RuntimeError('Native history/test wait exceeded the bound; no result claimed: '+case)
    if not report.exists():raise RuntimeError('No MT5 report: '+case)
    if agentlog.exists():
        with agentlog.open('rb') as handle:handle.seek(offset);logtext=handle.read().decode('utf-16-le',errors='replace')
        # Keep only data-quality and execution summaries, not megabytes of fills.
        auditlines=[line for line in logtext.splitlines() if any(w in line.lower() for w in ('real tick','synchroniz','mismatch','discard','absent','generated','passed to tester','pair audit','final balance','history begins'))]
        (out/'tester-audit.txt').write_text('\n'.join(auditlines),encoding='utf-8')
    for p in reportdir.glob(case+'*'):
        if '.old-' not in p.name:shutil.copy2(p,out/p.name)
    for suffix in ('baskets','features'):
        p=COMMON/(case+'-'+suffix+'.csv')
        if not p.exists():raise RuntimeError('Missing native '+suffix+' audit')
        shutil.copy2(p,out/(suffix+'.csv'))
    row=parser.parse_report(out/report.name)
    html=parser.read_report(out/report.name)
    from bs4 import BeautifulSoup
    reporttext=' '.join(BeautifulSoup(html,'html.parser').get_text(' ').split())
    relative=re.search(r'Equity Drawdown Relative:\s*([\d.]+)%',reporttext)
    row['dd_pct_at_max_cash_event']=row['equity_dd_pct']
    if relative:row['equity_dd_pct']=float(relative.group(1))
    baskets=pd.read_csv(out/'baskets.csv')
    # An order can fail before opening either leg; those IDs are not closed baskets.
    net=float(baskets['net'].sum())
    if abs(net-row['net_profit'])>.06:raise RuntimeError(f'Basket ledger mismatch: {net} vs {row["net_profit"]}')
    nativefeatures=pd.read_csv(out/'features.csv')
    d,_,_=load_pair(pair);f=features(d,c['tf'],c['window'],c['model'])
    py=pd.DataFrame(f,index=d.index.as_unit('s').asi8,columns=['z','beta','mean','sd','atr','low','high','signal_spread','mean_log_b'])
    comparison=nativefeatures.set_index('time').join(py,rsuffix='_python',how='inner').dropna()
    featureerrors={k:float(np.max(np.abs(comparison[k]-comparison[k+'_python']))) for k in py.columns} if len(comparison) else {}
    if len(comparison) and featureerrors['z']>1e-6:raise RuntimeError('Native/Python signal mismatch: '+str(featureerrors))
    wins=int((baskets['net']>0).sum());loss=-float(baskets.loc[baskets.net<0,'net'].sum());gain=float(baskets.loc[baskets.net>0,'net'].sum())
    row.update(pair=pair,label=label,stage=stage,model=model,execution_mode=execution,config=c,fingerprint=fingerprint,
        baskets=len(baskets),basket_win_rate=wins/len(baskets)*100 if len(baskets) else 0,basket_profit_factor=gain/loss if loss else None,
        leg_trades=row['trades'],complete_two_leg_baskets=int(((baskets.entry_fills==2)&(baskets.exit_fills==2)).sum()),
        feature_comparisons=len(comparison),feature_max_absolute_errors=featureerrors,elapsed_seconds=round(time.monotonic()-t0,2))
    dump(done,row)
    print('NATIVE DONE',case,{k:row[k] for k in ('return_pct','baskets','basket_win_rate','basket_profit_factor','equity_dd_pct','history_quality_pct','elapsed_seconds')},flush=True)
    return row

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--compile',action='store_true');ap.add_argument('--smoke',action='store_true');ap.add_argument('--real',action='store_true');ap.add_argument('--pair',choices=list(PAIRS));a=ap.parse_args()
    compile_ea()
    if not a.compile:
        choices=json.loads((ROOT/'selection.json').read_text())
        for pair in PAIRS:
            if a.pair and pair!=a.pair:continue
            for label,c in [('baseline',BASE),('selected',choices[pair]['config'])]:
                if a.real and label=='baseline':continue
                run(pair,label,c,'smoke' if a.smoke else 'test',4 if a.real else 0)
            if not a.smoke and not a.real:run(pair,'selected',choices[pair]['config'],'full')
