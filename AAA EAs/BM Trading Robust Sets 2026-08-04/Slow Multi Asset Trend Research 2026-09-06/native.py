"""Compile and validate frozen settings in the isolated MT5 demo Strategy Tester."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, time
from datetime import datetime

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
SOURCE=ROOT/'EA'/'Calyx Slow Trend EA.mq5'
EXPERT_DIR='Calyx Slow Trend'
SYMBOLS=('XAUUSD','XAGUSD','BTCUSD','ETHUSD','USTEC','US30','EURUSD','GBPJPY')
TF={'H4':16388,'D1':16408,'W1':32769}
HORIZON={'1m':0,'3m':1,'6m':2,'1-3-6m':3,'3-6-12m':4}
TREND={'none':0,'ema100':1,'ema200':2,'ema200-rising':3}
SESSION={'all-day':-1,'asia':60,'london':480,'new-york':810,'overlap':840}
spec=importlib.util.spec_from_file_location('report_parser',PACKAGE/'US100 Momentum Continuation Research 2026-08-31'/'Analyze-Reports.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def compile_ea():
    log=SOURCE.with_suffix('.compile.log')
    command=f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"'
    subprocess.run(command,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    text=log.read_text(encoding='utf-16') if log.exists() else ''
    if '0 errors, 0 warnings' not in text or not SOURCE.with_suffix('.ex5').exists():
        raise RuntimeError('EA compilation failed:\n'+text[-5000:])
    target=TESTER/'MQL5'/'Experts'/EXPERT_DIR;target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE.with_suffix('.ex5'),target/SOURCE.with_suffix('.ex5').name)
    (ROOT/'EA'/'compile.log').write_text(text,encoding='utf-8')
    print('COMPILE 0 errors, 0 warnings',flush=True)

def mt5_inputs(c,symbol):
    return dict(InpSignalTimeframe=TF[c['tf']],InpHorizonMode=HORIZON[c['horizon']],InpTrendMode=TREND[c['trend']],
        InpAllowLong=c['direction'] in ('both','long-only'),InpAllowShort=c['direction']=='both',InpSessionMinuteUTC=SESSION[c['session']],
        InpStopMode=c['stop_mode'],InpStopATR=c['stop_atr'],InpExitMode=c['exit_mode'],InpRewardRisk=c['rr'],InpMaximumHoldDays=c['max_hold_days'],
        InpManagement=c['manage'],InpRiskPercent=1.0,InpMaximumDeviationPoints=100,InpMagic=969060310+SYMBOLS.index(symbol),InpTesterOnly=True)

def trade_audit(report):
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(report.read_text(encoding='utf-16'),'html.parser');inside=False;opened=None;trades=[]
    for tr in soup.find_all('tr'):
        if tr.get_text(' ',strip=True)=='Deals':inside=True;continue
        if not inside:continue
        c=[' '.join(td.get_text(' ',strip=True).split()) for td in tr.find_all('td')]
        if len(c)!=13 or c[4] not in ('in','out'):continue
        when=datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S');cash=sum(float(c[i].replace(' ','')) for i in (8,9,10));balance=float(c[11].replace(' ',''))
        if c[4]=='in':
            if opened is not None:raise RuntimeError('Overlapping position in single-market audit')
            opened=dict(entry_time=when.isoformat(),entry_price=float(c[6].replace(' ','')),side=c[3],volume=float(c[5]),cash=cash,before=balance-cash)
        else:
            if opened is None:raise RuntimeError('Unmatched native exit')
            net=opened.pop('cash')+cash;before=opened.pop('before')
            trades.append(dict(**opened,exit_time=when.isoformat(),exit_price=float(c[6].replace(' ','')),net=net,return_fraction=net/before,holding_days=(when-datetime.fromisoformat(opened['entry_time'])).total_seconds()/86400))
            opened=None
    return trades

def run(symbol,label,c,stage='test',model=0,execution=-1,timeout=1200):
    start,end={'smoke':('2025.09.01','2025.10.01'),'test':('2025.09.01','2026.09.01'),'full':('2023.09.01','2026.09.01')}[stage]
    case=f'{symbol.lower()}-{label}-{stage}-model{model}'+(('' if execution==-1 else f'-delay{execution}'))
    params=mt5_inputs(c,symbol)
    fingerprint=hashlib.sha256((SOURCE.read_text()+json.dumps(params,sort_keys=True)+start+end+str(model)+str(execution)).encode()).hexdigest()
    out=ROOT/'Native'/case;out.mkdir(parents=True,exist_ok=True);result=out/'result.json'
    if result.exists():
        old=json.loads(result.read_text())
        if old.get('fingerprint')==fingerprint:return old
    set_name=case+'.set';sets=ROOT/'Sets';sets.mkdir(exist_ok=True)
    set_text='\n'.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}' for k,v in params.items())+'\n'
    (sets/set_name).write_text(set_text,encoding='utf-8');(TESTER/'MQL5'/'Profiles'/'Tester'/set_name).write_text(set_text,encoding='utf-8')
    reportdir=TESTER/'reports'/'calyx-slow-trend';reportdir.mkdir(parents=True,exist_ok=True);report=reportdir/(case+'.htm')
    if report.exists():report.rename(report.with_name(case+f'.old-{time.time_ns()}.htm'))
    job=TESTER/'backtest-configs'/'calyx-slow-trend';job.mkdir(parents=True,exist_ok=True);ini=job/(case+'.ini')
    ini.write_text(f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert={EXPERT_DIR}\\Calyx Slow Trend EA
ExpertParameters={set_name}
Symbol={symbol}
Period=M15
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
Report=reports\\calyx-slow-trend\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    print('NATIVE START',case,flush=True);begin=time.monotonic()
    try:subprocess.run(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired:
        dump(out/'unavailable.json',dict(case=case,status='bounded_timeout',seconds=timeout));raise
    if not report.exists():raise RuntimeError('MT5 produced no report for '+case)
    for p in reportdir.glob(case+'*'):
        if '.old-' not in p.name:shutil.copy2(p,out/p.name)
    row=parser.parse_report(out/report.name);trades=trade_audit(out/report.name)
    if len(trades)!=row['trades'] or abs(sum(x['net'] for x in trades)-row['net_profit'])>.06:
        raise RuntimeError(f'{case}: native trade ledger does not reconcile ({len(trades)} vs {row["trades"]})')
    dump(out/'trades.json',trades)
    row.update(symbol=symbol,label=label,stage=stage,model=model,execution_mode=execution,config=c,inputs=params,fingerprint=fingerprint,elapsed_seconds=round(time.monotonic()-begin,2),audit=dict(trades=len(trades),max_holding_days=max((x['holding_days'] for x in trades),default=0)))
    dump(result,row);print('NATIVE DONE',case,{k:row[k] for k in ('return_pct','profit_factor','win_rate','equity_dd_pct','trades','history_quality_pct','elapsed_seconds')},flush=True)
    return row

def main(args):
    compile_ea();choices=json.loads((ROOT/'selection-lock.json').read_text())
    symbols=(args.symbol,) if args.symbol else SYMBOLS
    for symbol in symbols:
        c=choices[symbol]['config']
        if args.smoke:run(symbol,'selected',c,'smoke',1,1,300);continue
        if args.real:run(symbol,'selected',c,'test',4,-1,300);continue
        run(symbol,'baseline',dict(tf='D1',horizon='1-3-6m',trend='ema200-rising',direction='both',session='all-day',stop_mode=0,stop_atr=2.5,exit_mode=0,rr=2.,max_hold_days=0,manage=0),'test',0,-1)
        run(symbol,'selected',c,'test',0,-1)
        run(symbol,'selected',c,'full',1,-1)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--symbol',choices=SYMBOLS);ap.add_argument('--smoke',action='store_true');ap.add_argument('--real',action='store_true');main(ap.parse_args())
