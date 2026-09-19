"""Parameterized native tester runner. Separate evidence, no live-terminal mutation."""
from __future__ import annotations
import argparse, configparser, csv, hashlib, importlib.util, json, re, shutil, subprocess, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
EXPERT=Path('AAA Research')/'3 way gold Optimization 20260913'
NAME='3 way gold Optimized'
from params import DEFAULT,normalize,ident,RAW
WINDOWS={}
CURRENT=dict(DEFAULT)
CURRENT_MODEL=4
DATA=None
LABELS={0:'All three together',1:'Momentum',2:'Trend change',3:'Breakout'}
BASE=dict(DEFAULT)
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
              TESTER/'MQL5'/'Profiles'/'Tester',TESTER/'backtest-configs'/'3-way-gold-opt',TESTER/'reports'/'3-way-gold-opt'):
        p.mkdir(parents=True,exist_ok=True)
    for source in (ROOT/'EA').glob('*.mq*'):shutil.copy2(source,TESTER/'MQL5'/'Experts'/EXPERT/source.name)
    log=ROOT/'compile.log';started=time.time()
    command=f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{TESTER/"MQL5"/"Experts"/EXPERT/(NAME+".mq5")}" /log:"{log}"'
    subprocess.run(command,cwd=TESTER,startupinfo=hidden(),timeout=120)
    text=log.read_text(encoding='utf-16',errors='replace')
    assert log.stat().st_mtime>=started-2 and '0 errors, 0 warnings' in text,text
    shutil.copy2(TESTER/'MQL5'/'Experts'/EXPERT/(NAME+'.ex5'),ROOT/'EA'/(NAME+'.ex5'))
    print('COMPILED: zero errors and warnings',flush=True)

def validate_decisions(rows,bars):
    global DATA
    import numpy as np
    from data import load,signals
    if DATA is None:DATA=load()
    expected,atr=signals(DATA,CURRENT);times=DATA['h'][:,0]
    verified={};last='';feature_checks=0
    from datetime import timezone
    for row in rows:
        assert row['time']>last,'Repeated decision';last=row['time']
        assert stamp(row['closed_bar'])+timedelta(hours=1)<=stamp(row['time']),'Unclosed signal'
        epoch=stamp(row['closed_bar']).replace(tzinfo=timezone.utc).timestamp()
        i=int(np.searchsorted(times,epoch));assert times[i]==epoch
        x={k:float(v) for k,v in row.items() if k not in ('time','closed_bar')}
        # EA logs all engine raw signals, before direction and engine selection.
        c={**CURRENT,'InpDirection':0,'InpEngine':0}
        if feature_checks==0:unfiltered,_=signals(DATA,c)
        actual=tuple(int(x[k]) for k in ('momentum','change','breakout'))
        assert actual==tuple(unfiltered[i]),('Native/Python signal mismatch',row,CURRENT)
        assert abs(x['atr1']-atr[i])<.002
        for col,p,shift in [('e9_1',CURRENT['InpChangeFastEMA'],0),('e9_2',CURRENT['InpChangeFastEMA'],1),
          ('e20_1',CURRENT['InpPullbackEMA'],0),('e20_2',CURRENT['InpPullbackEMA'],1),
          ('e21_1',CURRENT['InpChangeSlowEMA'],0),('e21_2',CURRENT['InpChangeSlowEMA'],1),
          ('e50',CURRENT['InpTrendFastEMA'],0),('e200',CURRENT['InpTrendSlowEMA'],0)]:
            assert abs(x[col]-DATA['ema'][p][i-shift])<.02,(col,row['time'])
        for col,values in [('adx',DATA['ind'][CURRENT['InpADXPeriod']][1]),('plus',DATA['ind'][CURRENT['InpADXPeriod']][2]),
          ('minus',DATA['ind'][CURRENT['InpADXPeriod']][3]),('rsi',DATA['ind'][CURRENT['InpRSIPeriod']][4])]:
            assert abs(x[col]-values[i])<.02,(col,row['time'])
        verified[row['time']]=(actual,x);feature_checks+=1
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
        report=str(report.relative_to(ROOT)),report_sha256=sha(report),model=CURRENT_MODEL,config=dict(CURRENT),config_id=ident(CURRENT),execution_delay_ms=delay,run_id=runid,
        history_quality_label=meta['history_quality'],actual_first_tick=summary['first_tick'],actual_last_tick=summary['last_tick'],
        max_equity_dd_pct=max(float(summary['native_equity_dd_pct']),float(summary['observed_equity_dd_pct'])),
        max_equity_dd_cash=float(summary['observed_equity_dd_cash']),minimum_equity=float(summary['minimum_equity']),
        native_stopout=any(6 in t['exit_reasons'] for t in trades),boundary_exits=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in trades),
        max_concurrent_positions=int(float(summary['max_concurrent_positions'])),max_gross_initial_stop_risk_pct=float(summary['max_gross_initial_stop_risk_pct']),
        max_trade_risk_pct=max((t['planned_risk_pct'] for t in trades),default=0),
        fill_rr_min=min((t['fill_rr'] for t in trades),default=None),fill_rr_max=max((t['fill_rr'] for t in trades),default=None),
        execution_errors=[e for e in events if e['event'] in ('error','manage_error')],blocked_occupied=int(float(summary['occupied_signals'])),
        verified_decisions=len(signals),independent_ema_checks=feature_checks,by_engine=by_engine,summary=summary,
        quality_journal=[line for line in journal.splitlines() if re.search(r'real ticks|execution delay|3WG SELF|no history|no prices|not enough money|stop out',line,re.I)],**stats)
    save(audit/f'{tag}-trades.json',trades);save(ROOT/'Runs'/f'{tag}.json',row)
    print('RESULT '+json.dumps({k:row[k] for k in ('period','label','return_pct','trades','net_win_rate','net_pf','max_equity_dd_pct','commission','swap')}),flush=True)
    return row

def run(config,window,stage='native',delay=1,model=4,force=False):
    global CURRENT,CURRENT_MODEL,BASE
    CURRENT=normalize(config);CURRENT_MODEL=model;BASE=dict(CURRENT)
    engine=CURRENT['InpEngine'];period=stage+'-'+ident(CURRENT)+'-'+window[0].replace('.','')+'-'+window[1].replace('.','')+'-m'+str(model)
    WINDOWS[period]=window
    existing=ROOT/'Runs'/f'{period}-engine{engine}-d{delay}.json'
    if existing.exists() and not force:
        row=json.loads(existing.read_text());assert row['source_hashes']==hashes(),'Stale source evidence';return row
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16')
    common=dict(ref['Common']);assert common.get('server')=='Exness-MT5Trial16' and common.get('login')=='472334559','Unexpected tester account'
    profile=TESTER/'MQL5'/'Profiles'/'Charts'/'CappedResearchOnly'
    assert profile.is_dir() and not list(profile.glob('*.chr')),'Research chart profile must remain empty'
    runid=int(time.time());tag=f'{period}-engine{engine}-d{delay}-{runid}'
    settings={**BASE,'InpEngine':str(engine),'InpAuditRun':str(runid)}
    setfile=ROOT/'Sets'/(tag+'.set');setfile.write_text(''.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}\n' for k,v in settings.items()),encoding='utf-8')
    shutil.copy2(setfile,TESTER/'MQL5'/'Profiles'/'Tester'/setfile.name)
    start,end=WINDOWS[period]
    content='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())
    content+='\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
    content+=f'Expert={EXPERT}\\{NAME}\nExpertParameters={setfile.name}\nSymbol=XAUUSD\nPeriod=H1\nLogin={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel={model}\nExecutionMode={delay}\nOptimization=0\n'
    content+=f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\3-way-gold-opt\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n'
    config=TESTER/'backtest-configs'/'3-way-gold-opt'/(tag+'.ini');config.write_text(content,encoding='utf-16')
    sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')};started=time.time()
    print(f'START {tag} : {start} to {end}',flush=True)
    p=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{config.relative_to(TESTER)}'],cwd=TESTER,startupinfo=hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    save(ROOT/'active-run.json',dict(pid=p.pid,tag=tag,started=started,terminal=str(TESTER/'terminal64.exe')))
    try:p.wait(timeout=2400)
    except subprocess.TimeoutExpired:p.kill();raise RuntimeError('Owned isolated tester exceeded timeout')
    report=TESTER/'reports'/'3-way-gold-opt'/(tag+'.htm')
    assert report.is_file() and report.stat().st_mtime>started-2,'No fresh native MT5 report'
    for source in report.parent.glob(tag+'*'):shutil.copy2(source,ROOT/'Backtest Reports'/source.name)
    report=ROOT/'Backtest Reports'/report.name
    journal=''
    for path in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if path.stat().st_mtime<started-2:continue
        with path.open('rb') as f:f.seek(sizes.get(path,0));journal+=f.read().decode('utf-16-le',errors='replace')
    prefix=f'3WGO-{runid}-{engine}'
    files=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{prefix}-*.csv') if p.stat().st_mtime>started-2]
    assert len(files)==6,('Expected six native audit files',len(files))
    for f in files:shutil.copy2(f,ROOT/'Audit'/(f'{period}-engine{engine}-d{delay}'+f.name[len(prefix):]))
    (ROOT/'Audit'/(tag+'-journal.log')).write_text(journal,encoding='utf-8')
    return analyze(period,engine,runid,delay,report,journal)

def parity():
    from params import WINDOWS
    r=run(DEFAULT,WINDOWS['6m'],'parity')
    original=json.loads((RAW/'Audit'/'6m-engine0-d1-trades.json').read_text())
    actual=json.loads((ROOT/'Audit'/f"{r['period']}-engine0-d1-trades.json").read_text())
    assert original==actual,'Default EA trade ledger differs from frozen raw version'
    save(ROOT/'raw-parity.json',dict(passed=True,trades=len(actual),source_hashes=hashes(),full_trade_ledger_identical=True))
    print('FULL RAW LEDGER PARITY PASS',len(actual),flush=True)
    return r

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--parity',action='store_true');a=cli.parse_args()
    prepare()
    if a.parity:parity()
