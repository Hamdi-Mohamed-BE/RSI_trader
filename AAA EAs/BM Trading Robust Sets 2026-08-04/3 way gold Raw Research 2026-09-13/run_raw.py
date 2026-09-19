"""Frozen native MT5 runs; no parameter search and no live-terminal mutation."""
from __future__ import annotations
import argparse, configparser, csv, hashlib, importlib.util, json, re, shutil, subprocess, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
EXPERT=Path('AAA Research')/'3 way gold 20260913'
NAME='3 way gold'
WINDOWS={'6m':('2026.03.05','2026.09.05'),'1y':('2025.09.05','2026.09.05'),
         '3y':('2023.09.05','2026.09.05'),'5y':('2021.09.05','2026.09.05'),
         '2019-2026':('2019.01.01','2026.09.05')}
LABELS={0:'All three together',1:'Momentum',2:'Trend change',3:'Breakout'}
BASE={'InpRiskPerEnginePercent':'0.30','InpStopATR':'2.0','InpRewardRisk':'2.0',
      'InpMagicBase':'91330000','InpDeviationPoints':'30'}
spec=importlib.util.spec_from_file_location('native_parser',PACKAGE/'POC Fibonacci Volume Profile Research 2026-09-04'/'Analyze-POCFib.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False),encoding='utf-8')
def readcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes():return {p.name:sha(p) for p in sorted((ROOT/'EA').glob('*.mq*'))}
def stamp(s):return datetime.strptime(s,'%Y.%m.%d %H:%M:%S')
def hidden():
    s=subprocess.STARTUPINFO();s.dwFlags|=subprocess.STARTF_USESHOWWINDOW;s.wShowWindow=0;return s

def prepare():
    for p in (ROOT/'Runs',ROOT/'Sets',ROOT/'Audit',ROOT/'Backtest Reports',TESTER/'MQL5'/'Experts'/EXPERT,
              TESTER/'MQL5'/'Profiles'/'Tester',TESTER/'backtest-configs'/'3-way-gold',TESTER/'reports'/'3-way-gold'):
        p.mkdir(parents=True,exist_ok=True)
    for source in (ROOT/'EA').glob('*.mq*'):shutil.copy2(source,TESTER/'MQL5'/'Experts'/EXPERT/source.name)
    log=ROOT/'compile.log';started=time.time()
    command=f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{TESTER/"MQL5"/"Experts"/EXPERT/(NAME+".mq5")}" /log:"{log}"'
    subprocess.run(command,cwd=TESTER,startupinfo=hidden(),timeout=120)
    text=log.read_text(encoding='utf-16',errors='replace')
    assert log.stat().st_mtime>=started-2 and '0 errors, 0 warnings' in text,text
    shutil.copy2(TESTER/'MQL5'/'Experts'/EXPERT/(NAME+'.ex5'),ROOT/'EA'/(NAME+'.ex5'))
    print('COMPILED: zero errors and warnings',flush=True)

def raw_signals(x):
    m=c=b=0
    if x['adx']>=25:
        if x['e50']>x['e200'] and x['c1']>x['e50'] and x['plus']>x['minus'] and x['c2']<=x['e20_2'] and x['c1']>x['e20_1']:m=1
        if x['e50']<x['e200'] and x['c1']<x['e50'] and x['minus']>x['plus'] and x['c2']>=x['e20_2'] and x['c1']<x['e20_1']:m=-1
    if x['e9_2']<=x['e21_2'] and x['e9_1']>x['e21_1'] and x['rsi']>50:c=1
    if x['e9_2']>=x['e21_2'] and x['e9_1']<x['e21_1'] and x['rsi']<50:c=-1
    if x['atr2']>0 and x['tr']>=1.5*x['atr2'] and x['atr1']>x['atr2']:
        if x['c1']>x['prior20_high']:b=1
        if x['c1']<x['prior20_low']:b=-1
    return m,c,b

def validate_decisions(rows,bars):
    lookup={b['time']:i for i,b in enumerate(bars)}
    verified={};last='';feature_checks=0
    # Independent EMA implementation. The first 1,000 exported bars are excluded
    # from numerical EMA equality checks to remove unknown native seeding effects.
    emas={p:[] for p in (9,20,21,50,200)}
    for bar in bars:
        close=float(bar['close'])
        for period,a in emas.items():a.append(close if not a else a[-1]+2/(period+1)*(close-a[-1]))
    for row in rows:
        assert row['time']>last,'Repeated/out-of-order decision';last=row['time']
        assert stamp(row['closed_bar'])+timedelta(hours=1)<=stamp(row['time']),'Unclosed signal bar'
        x={k:float(v) for k,v in row.items() if k not in ('time','closed_bar')}
        expected=raw_signals(x);actual=tuple(int(x[k]) for k in ('momentum','change','breakout'))
        assert expected==actual,('Signal disagreement',row)
        i=lookup[row['closed_bar']];assert i>=20
        prior=bars[i-20:i];bar=bars[i];prev=bars[i-1]
        assert abs(x['prior20_high']-max(float(b['high']) for b in prior))<1e-7
        assert abs(x['prior20_low']-min(float(b['low']) for b in prior))<1e-7
        assert abs(x['c1']-float(bar['close']))<1e-7 and abs(x['c2']-float(prev['close']))<1e-7
        tr=max(float(bar['high'])-float(bar['low']),abs(float(bar['high'])-float(prev['close'])),abs(float(bar['low'])-float(prev['close'])))
        assert abs(x['tr']-tr)<1e-7
        atr_now=sum(max(float(bars[j]['high'])-float(bars[j]['low']),abs(float(bars[j]['high'])-float(bars[j-1]['close'])),abs(float(bars[j]['low'])-float(bars[j-1]['close']))) for j in range(i-13,i+1))/14
        assert abs(x['atr1']-atr_now)<1e-6,('ATR mismatch',row['time'],x['atr1'],atr_now)
        if i>=1000:
            for k,p,shift in [('e9_1',9,0),('e9_2',9,1),('e20_1',20,0),('e20_2',20,1),('e21_1',21,0),('e21_2',21,1),('e50',50,0),('e200',200,0)]:
                assert abs(x[k]-emas[p][i-shift])<.02,('EMA mismatch',row['time'],k,x[k],emas[p][i-shift])
            feature_checks+=1
        verified[row['time']]=(expected,x)
    return verified,feature_checks

def group_stats(trades):
    win=[t['net'] for t in trades if t['net']>0];loss=[t['net'] for t in trades if t['net']<0]
    streak=worst=0
    for t in sorted(trades,key=lambda t:(t['close_time'],int(t['position_id']))):
        streak=streak+1 if t['net']<0 else 0;worst=max(worst,streak)
    return dict(trades=len(trades),wins=len(win),losses=len(loss),breakeven=len(trades)-len(win)-len(loss),
        net_profit=round(sum(t['net'] for t in trades),2),net_win_rate=100*len(win)/len(trades) if trades else 0,
        net_pf=sum(win)/-sum(loss) if loss else None,average_win=sum(win)/len(win) if win else 0,
        average_loss=sum(loss)/len(loss) if loss else 0,largest_win=max(win,default=0),largest_loss=min(loss,default=0),max_loss_streak=worst,
        commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),fee=round(sum(t['fee'] for t in trades),2),
        longs=sum(t['direction']==1 for t in trades),shorts=sum(t['direction']==-1 for t in trades))

def analyze(period,engine,runid,delay,report,journal):
    tag=f'{period}-engine{engine}-d{delay}';audit=ROOT/'Audit'
    summary={r['key']:r['value'] for r in readcsv(audit/f'{tag}-summary.csv')}
    events=readcsv(audit/f'{tag}-events.csv');ds=readcsv(audit/f'{tag}-deals.csv')
    decisions=readcsv(audit/f'{tag}-decisions.csv');bars=readcsv(audit/f'{tag}-h1.csv')
    signals,feature_checks=validate_decisions(decisions,bars)
    signal_by_hour={stamp(time).replace(minute=0,second=0):time for time in signals}
    assert len(signal_by_hour)==len(signals),'More than one decision per hour'
    ent={r['position_id']:r for r in events if r['event']=='entry'};groups=defaultdict(list)
    for d in ds:
        if d['symbol']=='XAUUSD' and int(d['type']) in (0,1):
            for k in ('volume','price','profit','commission','swap','fee'):d[k]=float(d[k])
            groups[d['position_id']].append(d)
    trades=[]
    for pid,g in groups.items():
        ins=[d for d in g if int(d['entry'])==0];outs=[d for d in g if int(d['entry']) in (1,3)]
        assert ins and outs and pid in ent,(tag,pid,'Missing entry/exit/audit')
        e=ent[pid];eng=int(e['engine']);direction=int(e['dir'])
        assert int(ins[0]['magic'])==int(BASE['InpMagicBase'])+eng
        assert engine in (0,eng)
        vi=sum(d['volume'] for d in ins);vo=sum(d['volume'] for d in outs);assert abs(vi-vo)<1e-7
        px=sum(d['volume']*d['price'] for d in ins)/vi;sl=float(e['sl']);tp=float(e['tp'])
        assert direction*(px-sl)>0 and direction*(tp-px)>0
        decision_time=e['decision_bar']
        # On open-session gaps, the first tick can be later than the H1 open.
        matching=signal_by_hour.get(stamp(decision_time))
        assert matching is not None and signals[matching][0][eng-1]==direction,(tag,'entry signal mismatch',e)
        assert stamp(matching)<=stamp(e['time'])
        cash={k:round(sum(d[k] for d in g),8) for k in ('profit','commission','swap','fee')}
        net=round(sum(cash.values()),8)
        trades.append(dict(position_id=pid,engine=eng,label=LABELS[eng],open_time=ins[0]['time'],close_time=outs[-1]['time'],
            open_time_msc=int(ins[0]['time_msc']),close_time_msc=int(outs[-1]['time_msc']),direction=direction,volume=vi,
            entry=px,exit=sum(d['volume']*d['price'] for d in outs)/vo,initial_sl=sl,initial_tp=tp,fill_rr=abs(tp-px)/abs(px-sl),
            planned_risk_cash=float(e['risk_cash']),planned_risk_pct=100*float(e['risk_cash'])/float(e['equity_before']),
            exit_reasons=[int(d['reason']) for d in outs],exit_comments=[d['comment'] for d in outs],**cash,net=net))
    trades.sort(key=lambda t:(t['close_time_msc'],int(t['position_id'])))
    for eng in (1,2,3):
        leg=sorted((t for t in trades if t['engine']==eng),key=lambda t:t['open_time_msc'])
        for previous,next_t in zip(leg,leg[1:]):assert previous['close_time_msc']<=next_t['open_time_msc'],('Overlapping engine',eng)
    stats=group_stats(trades);meta=parser.parse_report(report)
    assert stats['trades']==int(float(summary['native_trades']))==int(float(summary['fills']))==meta['trades']
    assert abs(stats['net_profit']-float(summary['native_net_profit']))<.06
    assert abs(stats['net_profit']-meta['net_profit'])<.06
    assert abs(stats['net_profit']+10000-float(summary['final_balance']))<.06
    assert int(float(summary['max_concurrent_positions']))<=3
    assert '3WG SELF TEST PASS' in journal
    by_engine={LABELS[k]:group_stats([t for t in trades if t['engine']==k]) for k in (1,2,3)}
    row=dict(period=period,engine=engine,label=LABELS[engine],window=WINDOWS[period],initial_balance=10000,
        final_balance=float(summary['final_balance']),return_pct=stats['net_profit']/100,source_hashes=hashes(),
        report=str(report.relative_to(ROOT)),report_sha256=sha(report),model=4,execution_delay_ms=delay,run_id=runid,
        history_quality_label=meta['history_quality'],actual_first_tick=summary['first_tick'],actual_last_tick=summary['last_tick'],
        max_equity_dd_pct=max(float(summary['native_equity_dd_pct']),float(summary['observed_equity_dd_pct'])),
        max_equity_dd_cash=float(summary['observed_equity_dd_cash']),minimum_equity=float(summary['minimum_equity']),
        native_stopout=any(6 in t['exit_reasons'] for t in trades),boundary_exits=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in trades),
        max_concurrent_positions=int(float(summary['max_concurrent_positions'])),max_gross_initial_stop_risk_pct=float(summary['max_gross_initial_stop_risk_pct']),
        max_trade_risk_pct=max((t['planned_risk_pct'] for t in trades),default=0),
        fill_rr_min=min((t['fill_rr'] for t in trades),default=None),fill_rr_max=max((t['fill_rr'] for t in trades),default=None),
        execution_errors=[e for e in events if e['event']=='error'],blocked_occupied=int(float(summary['occupied_signals'])),
        verified_decisions=len(signals),independent_ema_checks=feature_checks,by_engine=by_engine,summary=summary,
        quality_journal=[line for line in journal.splitlines() if re.search(r'real ticks|execution delay|3WG SELF|no history|no prices|not enough money|stop out',line,re.I)],**stats)
    save(audit/f'{tag}-trades.json',trades);save(ROOT/'Runs'/f'{tag}.json',row)
    print('RESULT '+json.dumps({k:row[k] for k in ('period','label','return_pct','trades','net_win_rate','net_pf','max_equity_dd_pct','commission','swap')}),flush=True)
    return row

def run(period,engine=0,delay=1,force=False):
    existing=ROOT/'Runs'/f'{period}-engine{engine}-d{delay}.json'
    if existing.exists() and not force:
        row=json.loads(existing.read_text());assert row['source_hashes']==hashes(),'Stale source evidence';return row
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16')
    common=dict(ref['Common']);assert common.get('server')=='Exness-MT5Trial16' and common.get('login')=='472334559','Unexpected tester account'
    profile=TESTER/'MQL5'/'Profiles'/'Charts'/'CappedResearchOnly'
    assert profile.is_dir() and not list(profile.glob('*.chr')),'Research chart profile must remain empty'
    runid=int(time.time());tag=f'{period}-engine{engine}-d{delay}-{runid}'
    settings={**BASE,'InpEngine':str(engine),'InpAuditRun':str(runid)}
    setfile=ROOT/'Sets'/(tag+'.set');setfile.write_text(''.join(f'{k}={v}\n' for k,v in settings.items()),encoding='utf-8')
    shutil.copy2(setfile,TESTER/'MQL5'/'Profiles'/'Tester'/setfile.name)
    start,end=WINDOWS[period]
    content='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())
    content+='\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
    content+=f'Expert={EXPERT}\\{NAME}\nExpertParameters={setfile.name}\nSymbol=XAUUSD\nPeriod=H1\nLogin={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel=4\nExecutionMode={delay}\nOptimization=0\n'
    content+=f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\3-way-gold\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n'
    config=TESTER/'backtest-configs'/'3-way-gold'/(tag+'.ini');config.write_text(content,encoding='utf-16')
    sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')};started=time.time()
    print(f'START {tag} : {start} to {end}',flush=True)
    p=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{config.relative_to(TESTER)}'],cwd=TESTER,startupinfo=hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    save(ROOT/'active-run.json',dict(pid=p.pid,tag=tag,started=started,terminal=str(TESTER/'terminal64.exe')))
    try:p.wait(timeout=2400)
    except subprocess.TimeoutExpired:p.kill();raise RuntimeError('Owned isolated tester exceeded timeout')
    report=TESTER/'reports'/'3-way-gold'/(tag+'.htm')
    assert report.is_file() and report.stat().st_mtime>started-2,'No fresh native MT5 report'
    for source in report.parent.glob(tag+'*'):shutil.copy2(source,ROOT/'Backtest Reports'/source.name)
    report=ROOT/'Backtest Reports'/report.name
    journal=''
    for path in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if path.stat().st_mtime<started-2:continue
        with path.open('rb') as f:f.seek(sizes.get(path,0));journal+=f.read().decode('utf-16-le',errors='replace')
    prefix=f'3WG-{runid}-{engine}'
    files=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{prefix}-*.csv') if p.stat().st_mtime>started-2]
    assert len(files)==6,('Expected six native audit files',len(files))
    for f in files:shutil.copy2(f,ROOT/'Audit'/(f'{period}-engine{engine}-d{delay}'+f.name[len(prefix):]))
    (ROOT/'Audit'/(tag+'-journal.log')).write_text(journal,encoding='utf-8')
    return analyze(period,engine,runid,delay,report,journal)

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--periods',default=','.join(WINDOWS));cli.add_argument('--engine',type=int,default=0,choices=range(4));cli.add_argument('--delay',type=int,default=1);cli.add_argument('--compile-only',action='store_true');cli.add_argument('--components',action='store_true');cli.add_argument('--force',action='store_true');a=cli.parse_args()
    prepare()
    if not a.compile_only:
        for period in a.periods.split(','):run(period,a.engine,a.delay,a.force)
        if a.components:
            for engine in (1,2,3):run('5y',engine,a.delay)
        save(ROOT/'results.json',[json.loads(p.read_text()) for p in sorted((ROOT/'Runs').glob('*.json'))])
