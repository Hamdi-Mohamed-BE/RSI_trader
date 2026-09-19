from __future__ import annotations
import argparse,configparser,csv,hashlib,importlib.util,json,re,shutil,subprocess,time
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
EXPERT=Path('AAA Research')/'LTA AOI Exits 20260913'
NAME='LTA AOI Research'
WINDOWS={'6m':('2026.03.05','2026.09.05'),'1y':('2025.09.05','2026.09.05'),
         '3y':('2023.09.05','2026.09.05'),'5y':('2021.09.05','2026.09.05')}
LABELS=['Current 3R','Previous-day TP','Previous-week TP','Nearest day/week TP','Frozen AOI trail','Rolling AOI trail']
BASESET=PACKAGE/'Selected Portfolio Settings 2026-09-01'/'01 LTA Volume Profile - CURRENT - ALL DAY.set'

def hidden():
    s=subprocess.STARTUPINFO();s.dwFlags|=subprocess.STARTF_USESHOWWINDOW;s.wShowWindow=0;return s
def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False),encoding='utf-8')
def csvrows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def fingerprint():
    paths=[*sorted((ROOT/'EA').glob('*.mq*')),BASESET]
    return {str(p.relative_to(PACKAGE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def compile_ea():
    for p in [ROOT/'Runs',ROOT/'Sets',ROOT/'Audit',ROOT/'Backtest Reports',TESTER/'MQL5'/'Experts'/EXPERT,
              TESTER/'reports'/'lta-aoi',TESTER/'backtest-configs'/'lta-aoi']:
        p.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'EA').glob('*.mq*'):shutil.copy2(p,TESTER/'MQL5'/'Experts'/EXPERT/p.name)
    log=ROOT/'compile.log';start=time.time()
    cmd=f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{TESTER/"MQL5"/"Experts"/EXPERT/(NAME+".mq5")}" /log:"{log}"'
    subprocess.run(cmd,cwd=TESTER,startupinfo=hidden(),timeout=120)
    text=log.read_text(encoding='utf-16',errors='replace')
    assert log.stat().st_mtime>start-2 and '0 errors, 0 warnings' in text,text
    shutil.copy2(TESTER/'MQL5'/'Experts'/EXPERT/(NAME+'.ex5'),ROOT/'EA'/(NAME+'.ex5'))
    print('COMPILED: zero errors and warnings',flush=True)
def audit_ladder(text):
    return sorted(float(x.rsplit('=',1)[1]) for x in text.split(';') if x)
def analyze(period,case,runid,delay,journal,report,source_hashes):
    tag=f'{period}-case{case}-d{delay}';a=ROOT/'Audit'
    summ={r['key']:r['value'] for r in csvrows(a/f'{tag}-summary.csv')}
    ev=csvrows(a/f'{tag}-events.csv');ds=csvrows(a/f'{tag}-deals.csv')
    groups=defaultdict(list)
    for d in ds:
        if d['symbol']!='XAUUSD' or int(d['type']) not in (0,1):continue
        for k in ('volume','price','profit','commission','swap','fee'):d[k]=float(d[k])
        groups[d['position_id']].append(d)
    entries={r['position_id']:r for r in ev if r['event']=='entry'}
    assert not any(r['event']=='missing_position' for r in ev)
    trades=[]
    for pid,g in groups.items():
        ins=[d for d in g if d['entry']=='0'];outs=[d for d in g if d['entry'] in ('1','3')]
        assert ins and outs and pid in entries,(tag,pid,'entry/exit/audit missing')
        vi=sum(d['volume'] for d in ins);vo=sum(d['volume'] for d in outs)
        assert abs(vi-vo)<1e-7
        e=entries[pid];direction=int(e['dir']);px=sum(d['volume']*d['price'] for d in ins)/vi
        sl=float(e['sl']);tp=float(e['tp']);lv=audit_ladder(e['ladder'])
        assert direction*(px-sl)>0 and (tp==0 or direction*(tp-px)>0)
        if case>=4:assert tp==0
        if 'aoi_target' in e['note']:assert min(abs(tp-x) for x in lv)<.002
        for key in ('PD','PW'):
            assert e['note'].split(f'|{key}=')[1].split('|')[0]<=e['time'],(tag,'future profile')
        cash={k:round(sum(d[k] for d in g),8) for k in ('profit','commission','swap','fee')}
        net=sum(cash.values());rr=abs(tp-px)/abs(px-sl) if tp else None
        trades.append({'position_id':pid,'open_time':ins[0]['time'],'close_time':outs[-1]['time'],
                       'direction':direction,'volume':vi,'open_price':px,'close_price':sum(d['volume']*d['price'] for d in outs)/vo,
                       'initial_sl':sl,'initial_tp':tp,'initial_rr':rr,'target_kind':e['note'].split('|')[0],
                       'planned_risk_cash':float(e['note'].split('|risk=')[1].split('|')[0]),
                       'risk_equity_pct':100*float(e['note'].split('|risk=')[1].split('|')[0])/float(e['equity']),
                       **cash,'net':net,'exit_comments':[d['comment'] for d in outs],'exit_reasons':[int(d['reason']) for d in outs]})
    trades.sort(key=lambda t:(t['close_time'],int(t['position_id'])))
    for e in ev:
        if e['event'] not in ('trail','trail_failed','trail_distance_rejected'):continue
        direction=int(e['dir']);buf=float(e['buffer']);old=float(e['old_sl']);new=float(e['sl'])
        broken=float(e['broken']);prev=float(e['previous']);c1=float(e['close1']);c2=float(e['close2'])
        levels=audit_ladder(e['ladder']);i=levels.index(broken)
        assert abs(levels[i-direction]-prev)<1e-7
        assert direction*(new-old)>0 and direction*(c1-broken-direction*buf)>-1e-7
        assert direction*(c2-broken-direction*buf)<1e-7
        assert e['closed_bar']>=entries[e['position_id']]['time'] and e['closed_bar']<e['time']
    net=round(sum(t['net'] for t in trades),2)
    assert abs(net-float(summ['native_net_profit']))<.1,(tag,'native net mismatch',net,summ)
    assert abs(float(summ['initial_balance'])+net-float(summ['final_balance']))<.1
    assert len(trades)==int(float(summ['native_trades']))==len(entries),(tag,'trade count mismatch')
    wins=[t['net'] for t in trades if t['net']>0];losses=[t['net'] for t in trades if t['net']<0]
    streak=worst=0
    for t in trades:streak=streak+1 if t['net']<0 else 0;worst=max(worst,streak)
    row={'period':period,'case':case,'label':LABELS[case],'window':WINDOWS[period],
         'delay_ms':delay,'model':4,'run_id':runid,'source_hashes':source_hashes,
         'net_profit':net,'final_balance':float(summ['final_balance']),'return_pct':net/100,
         'trades':len(trades),'net_win_rate':100*len(wins)/len(trades) if trades else 0,
         'net_pf':sum(wins)/-sum(losses) if losses else None,'max_equity_dd_pct':float(summ['native_dd_pct']),
         'observed_equity_dd_pct':float(summ['max_dd_pct']),'observed_equity_dd_cash':float(summ['max_dd_cash']),
         'conservative_equity_dd_pct':max(float(summ['max_dd_pct']),float(summ['native_dd_pct'])),
         'max_loss_streak':worst,'average_win':sum(wins)/len(wins) if wins else 0,'average_loss':sum(losses)/len(losses) if losses else 0,
         **{k:round(sum(t[k] for t in trades),2) for k in ('commission','swap','fee')},
         'long_trades':sum(t['direction']>0 for t in trades),'short_trades':sum(t['direction']<0 for t in trades),
         'planned_rr_min':min((t['initial_rr'] for t in trades if t['initial_rr'] is not None),default=None),
         'planned_rr_max':max((t['initial_rr'] for t in trades if t['initial_rr'] is not None),default=None),
         'native_stopout':any(6 in t['exit_reasons'] for t in trades),
         'max_planned_risk_equity_pct':max((t['risk_equity_pct'] for t in trades),default=0),
         'report':str(report.relative_to(ROOT)),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
         'quality_journal':[x for x in journal.splitlines() if re.search(r'real ticks|execution delay|AOI CONTRACT|no history|no prices|not enough money',x,re.I)],
         'summary':summ}
    save(a/f'{tag}-trades.json',trades);save(ROOT/'Runs'/f'{tag}.json',row)
    print('RESULT '+json.dumps({k:row[k] for k in ('period','label','return_pct','trades','net_win_rate','net_pf','max_equity_dd_pct','commission','swap')}),flush=True)
    return row
def run(period,case=None,delay=1,force=False):
    cases=list(range(6)) if case is None else [case]
    hashes=fingerprint()
    paths=[ROOT/'Runs'/f'{period}-case{c}-d{delay}.json' for c in cases]
    if not force and all(p.exists() for p in paths):
        rows=[json.loads(p.read_text()) for p in paths]
        assert all(r['source_hashes']==hashes for r in rows),'Stale source evidence'
        return rows
    runid=int(time.time());tag=f'{period}-'+('batch' if case is None else f'case{case}')+f'-d{delay}-{runid}'
    settings={}
    for line in BASESET.read_text(encoding='utf-8-sig').splitlines():
        if '=' in line:
            key,val=line.split('=',1);settings[key]=val.split('||')[0]
    settings.update(InpUseMarkovRegimeFilter='true',InpMarkovReturnWindow='40',InpMarkovThreshold='0.05',InpMarkovSignalGate='0.05',
                    InpMarkovMinLabels='252',InpMarkovHistoryBars='2600',InpAdaptivePortfolioControls='false',
                    InpExitCase='0||0||1||5||Y' if case is None else str(case),InpAuditRun=str(runid))
    setting=ROOT/'Sets'/(tag+'.set');setting.write_text(''.join(f'{k}={v}\n' for k,v in settings.items()),encoding='utf-8')
    shutil.copy2(setting,TESTER/'MQL5'/'Profiles'/'Tester'/setting.name)
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16')
    common=dict(ref['Common']);assert common.get('server','').startswith('Exness'), 'Unexpected tester broker'
    profile=TESTER/'MQL5'/'Profiles'/'Charts'/'CappedResearchOnly'
    assert profile.exists() and not list(profile.glob('*.chr')),'Isolated chart profile must be empty'
    content='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())
    content+='\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
    ext='xml' if case is None else 'htm';start,end=WINDOWS[period]
    content+=f'Expert={EXPERT}\\{NAME}\nExpertParameters={setting.name}\nSymbol=XAUUSD\nPeriod=M15\nLogin={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel=4\nExecutionMode={delay}\nOptimization={1 if case is None else 0}\nOptimizationCriterion=6\n'
    content+=f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\lta-aoi\\{tag}.{ext}\nReplaceReport=1\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n'
    config=TESTER/'backtest-configs'/'lta-aoi'/(tag+'.ini');config.write_text(content,encoding='utf-16')
    sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')};began=time.time()
    print(f'START {tag}: {start} to {end}',flush=True)
    p=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{config.relative_to(TESTER)}'],cwd=TESTER,startupinfo=hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    save(ROOT/'active-run.json',{'pid':p.pid,'terminal':str(TESTER/'terminal64.exe'),'tag':tag,'started':began})
    try:p.wait(timeout=3600)
    except subprocess.TimeoutExpired:p.kill();raise RuntimeError('Owned isolated tester timeout')
    report=TESTER/'reports'/'lta-aoi'/f'{tag}.{ext}'
    assert report.exists() and report.stat().st_mtime>began-2,'No fresh native report'
    for source in report.parent.glob(tag+'*'):shutil.copy2(source,ROOT/'Backtest Reports'/source.name)
    report=ROOT/'Backtest Reports'/report.name
    journal=''
    for path in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if path.stat().st_mtime<began-2:continue
        with path.open('rb') as f:f.seek(sizes.get(path,0));journal+=f.read().decode('utf-16-le',errors='replace')
    (ROOT/'Audit'/(tag+'-journal.log')).write_text(journal,encoding='utf-8')
    result=[]
    for c in cases:
        files=[q for q in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/LTA-AOI-{runid}-{c}-*.csv') if q.stat().st_mtime>began-2]
        assert len(files)==4,(c,len(files),'Incomplete native audit')
        for q in files:shutil.copy2(q,ROOT/'Audit'/(f'{period}-case{c}-d{delay}'+q.name.split(f'{runid}-{c}',1)[1]))
        result.append(analyze(period,c,runid,delay,journal,report,hashes))
    return result
if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--periods',default='6m,1y,3y,5y');cli.add_argument('--case',type=int);cli.add_argument('--delay',type=int,default=1);cli.add_argument('--compile-only',action='store_true');cli.add_argument('--force',action='store_true');a=cli.parse_args()
    compile_ea()
    if not a.compile_only:
        for period in a.periods.split(','):run(period,a.case,a.delay,a.force)
