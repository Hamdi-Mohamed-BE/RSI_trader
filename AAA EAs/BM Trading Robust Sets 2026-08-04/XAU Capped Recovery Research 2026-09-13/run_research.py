from __future__ import annotations
import argparse,configparser,csv,hashlib,importlib.util,json,re,shutil,subprocess,time
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('raw_native',ROOT.parent/'D14 H1 M5 Break Retest Raw 2026-09-13'/'run_raw.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
TESTER=native.TESTER
NAME='XAU Capped Recovery';EXPERT=Path('AAA Research')/'XAU Capped Recovery 20260913'
SOURCE=ROOT/'EA'/f'{NAME}.mq5';HASH=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
WINDOWS={**native.WINDOWS,'dev':('2021.09.05','2023.09.05'),'val':('2023.09.05','2024.09.05'),'later':('2024.09.05','2026.09.05')}
BASE={'InpLot':.01,'InpMultiplier':1,'InpMaxLegs':3,'InpStep':10,'InpATRStep':False,'InpATRMultiple':1,'InpBasketProfit':20,'InpOriginalExit':False,'InpBasketLoss':60,'InpDailyLoss':90,'InpDailyProfit':60,'InpCommissionPerLot':5.5,'InpLeverageCap':2000,'InpStopAtDouble':False}

def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False),encoding='utf-8')
def csvrows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def compile_ea():
    for p in [ROOT/'Sets',ROOT/'Runs',ROOT/'Audit',ROOT/'Backtest Reports',TESTER/'MQL5'/'Experts'/EXPERT,TESTER/'reports'/'capped-grid',TESTER/'backtest-configs'/'capped-grid']:
        p.mkdir(parents=True,exist_ok=True)
    target=TESTER/'MQL5'/'Experts'/EXPERT/SOURCE.name;shutil.copy2(SOURCE,target)
    log=ROOT/'compile.log';started=time.time()
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{target}" /log:"{log}"',cwd=TESTER,startupinfo=native.hidden(),timeout=120)
    content=log.read_text(encoding='utf-16',errors='replace')
    assert log.stat().st_mtime>started-2 and '0 errors, 0 warnings' in content,content
    shutil.copy2(target.with_suffix('.ex5'),ROOT/'EA'/f'{NAME}.ex5')
    print('COMPILED: zero errors, zero warnings',flush=True)

def analyze(tag,window,parameters,delay,optimization=False):
    audit=ROOT/'Audit';report=ROOT/'Backtest Reports'/f'{tag}.htm'
    meta={} if optimization else native.parser.parse_report(report)
    meta.pop('score',None);meta.pop('deals',None)
    summary={r['key']:r['value'] for r in csvrows(audit/f'{tag}-summary.csv')}
    ev=csvrows(audit/f'{tag}-events.csv');ds=csvrows(audit/f'{tag}-deals.csv')
    groups=defaultdict(list)
    for d in ds:
        if d['symbol']!='XAUUSD' or int(d['type']) not in (0,1):continue
        for k in ('volume','price','profit','commission','swap','fee'):d[k]=float(d[k])
        d['net']=sum(d[k] for k in ('profit','commission','swap','fee'))
        groups[d['position_id']].append(d)
    trades=[]
    for pid,g in groups.items():
        ins=[d for d in g if d['entry']=='0'];outs=[d for d in g if d['entry']=='1']
        assert ins and outs,(tag,pid,'missing entry/exit')
        vi=sum(d['volume'] for d in ins);vo=sum(d['volume'] for d in outs);assert abs(vi-vo)<1e-7
        bid=int(ins[0]['comment'].split('|')[1]);leg=int(ins[0]['comment'].split('|')[2])
        trades.append({'position_id':pid,'basket':bid,'leg_index':leg,'volume':vi,'open_time':ins[0]['time'],'close_time':outs[-1]['time'],
                       'open_price':sum(d['volume']*d['price'] for d in ins)/vi,'close_price':sum(d['volume']*d['price'] for d in outs)/vo,
                       **{k:round(sum(d[k] for d in g),8) for k in ('profit','commission','swap','fee','net')},
                       'exit_reasons':[int(d['reason']) for d in outs],'exit_comments':[d['comment'] for d in outs]})
    trades.sort(key=lambda t:(t['close_time'],int(t['position_id'])))
    if optimization:
        meta={'initial_balance':3000,'trades':len(trades),'net_profit':round(sum(t['net'] for t in trades),2),
              'commission':round(sum(t['commission'] for t in trades),2),'swap':round(sum(t['swap'] for t in trades),2),
              'history_quality':'Native optimization; generated ticks in pre-2026 development window'}
    assert len(trades)==meta['trades'],(tag,len(trades),meta['trades'])
    assert abs(sum(t['net'] for t in trades)-meta['net_profit'])<.06,(tag,'profit mismatch')
    baskets=[]
    for bid in sorted({t['basket'] for t in trades}):
        g=[t for t in trades if t['basket']==bid]
        end=next((e for e in ev if e['event']=='basket_closed' and int(e['basket'])==bid),None)
        baskets.append({'basket':bid,'legs':len(g),'open_time':min(t['open_time'] for t in g),'close_time':max(t['close_time'] for t in g),'net':sum(t['net'] for t in g),
                        'commission':sum(t['commission'] for t in g),'swap':sum(t['swap'] for t in g),'reason':end['note'] if end else 'test_end',
                        'end_balance':float(end['balance']) if end else float(summary['final_balance']),
                        'stopout':any(6 in t['exit_reasons'] for t in g)})
    wins=[t['net'] for t in trades if t['net']>0];loss=[t['net'] for t in trades if t['net']<0]
    bw=[b['net'] for b in baskets if b['net']>0];bl=[b['net'] for b in baskets if b['net']<0]
    journal=(audit/f'{tag}-journal.log').read_text()
    r={**meta,'tag':tag,'window':window,'parameters':parameters,'execution_delay_ms':delay,'source_sha256':HASH,
       'native_report_sha256':hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None,
       'native_optimization':optimization,'actual_start':summary['first_tick'],'actual_end':summary['last_tick'],
       'net_profit':round(sum(t['net'] for t in trades),2),'final_balance':float(summary['final_balance']),
       'net_win_rate':100*len(wins)/len(trades) if trades else 0,'net_pf':sum(wins)/-sum(loss) if loss else None,
       'basket_count':len(baskets),'basket_win_rate':100*len(bw)/len(baskets) if baskets else 0,'basket_pf':sum(bw)/-sum(bl) if bl else None,
       'worst_basket':min((b['net'] for b in baskets),default=0),'best_basket':max((b['net'] for b in baskets),default=0),
       'max_equity_dd_pct':float(summary['max_equity_dd_pct']),'max_equity_dd_cash':float(summary['max_equity_dd_cash']),
       'peak_equity':float(summary['max_equity']),'min_equity':float(summary['min_equity']),'max_lots':float(summary['max_total_lots']),
       'insolvent_at':summary['insolvent_at'] or None,'native_stopout':any(b['stopout'] for b in baskets),
       'first_flat_6000':summary['first_closed_double'] or None,'summary':summary,
       'daily_loss_locks':int(float(summary['daily_loss_locks'])),'daily_profit_locks':int(float(summary['daily_profit_locks'])),
       'stop_sync_failures':sum(e['event']=='stop_sync_failed' for e in ev),
       'quality_journal':[line for line in journal.splitlines() if re.search(r'real ticks|execution delay|CAPPED CONTRACT|stop out',line,re.I)]}
    r['return_pct']=100*r['net_profit']/3000
    save(audit/f'{tag}-trades.json',trades);save(audit/f'{tag}-baskets.json',baskets);save(ROOT/'Runs'/f'{tag}.json',r)
    print(json.dumps({k:r[k] for k in ('tag','net_profit','final_balance','trades','net_win_rate','net_pf','max_equity_dd_pct','insolvent_at','stop_sync_failures')}),flush=True)
    return r

def run(label,period='3y',params=None,delay=1,window=None):
    pars={**BASE,**(params or {})};win=window or WINDOWS[period];tag=f'{label}-{period}-d{delay}'
    saved=ROOT/'Runs'/f'{tag}.json'
    if saved.exists():
        r=json.loads(saved.read_text());assert r['source_sha256']==HASH and r['parameters']==pars and tuple(r['window'])==tuple(win),'Saved run specification mismatch';return r
    magic=85000000+int(hashlib.sha256(tag.encode()).hexdigest()[:6],16)
    values={**pars,'InpMagic':magic};setname=tag+'.set'
    def value(v):return str(v).lower() if isinstance(v,bool) else str(v)
    (ROOT/'Sets'/setname).write_text(''.join(f'{k}={value(v)}\n' for k,v in values.items()),encoding='utf-8')
    shutil.copy2(ROOT/'Sets'/setname,TESTER/'MQL5'/'Profiles'/'Tester'/setname)
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16');common=dict(ref['Common'])
    text='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Experts]\nAllowLiveTrading=0\nEnabled=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
    text+=f'Expert={EXPERT}\\{NAME}\nExpertParameters={setname}\nSymbol=XAUUSD\nPeriod=M1\nLogin={common["login"]}\nDeposit=3000\nCurrency=USD\nLeverage=1:2000\nModel=4\nExecutionMode={delay}\nOptimization=0\n'
    text+=f'FromDate={win[0]}\nToDate={win[1]}\nForwardMode=0\nReport=reports\\capped-grid\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseCloud=0\nVisual=0\n'
    cfg=TESTER/'backtest-configs'/'capped-grid'/f'{tag}.ini';cfg.write_text(text,encoding='utf-16')
    sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')};started=time.time()
    print('START '+tag,flush=True)
    proc=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{cfg.relative_to(TESTER)}'],cwd=TESTER,startupinfo=native.hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:proc.wait(timeout=1800)
    except subprocess.TimeoutExpired:proc.kill();raise RuntimeError('Research tester timeout')
    report=TESTER/'reports'/'capped-grid'/f'{tag}.htm';assert report.exists() and report.stat().st_mtime>started-2,'No fresh native report'
    for p in report.parent.glob(tag+'*'):shutil.copy2(p,ROOT/'Backtest Reports'/p.name)
    files=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/CappedGrid-{magic}-*.csv') if p.stat().st_mtime>started-2];assert len(files)==4
    for p in files:shutil.copy2(p,ROOT/'Audit'/(tag+p.name.split(str(magic),1)[1]))
    log=''
    for p in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if p.stat().st_mtime<started-2:continue
        with p.open('rb') as f:f.seek(sizes.get(p,0));log+=f.read().decode('utf-16-le',errors='replace')
    (ROOT/'Audit'/f'{tag}-journal.log').write_text(log,encoding='utf-8')
    return analyze(tag,win,pars,delay)

def rank(r,min_baskets):
    safe=not(r['native_stopout'] or r['insolvent_at'])
    eligible=safe and r['net_profit']>0 and r['basket_count']>=min_baskets
    return (eligible,safe,r['net_profit']/(1+r['max_equity_dd_cash']))

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--stage',choices=['baseline','search','final','diagnostics'],default='baseline');a=cli.parse_args()
    compile_ea()
    if a.stage=='baseline':
        out=[run('baseline',p) for p in ('3y','6m','1y','5y')];save(ROOT/'baseline.json',out)
    elif a.stage=='search':
        dev=[]
        for gap in (10,20,30,'atr'):
            for profit in (10,20,30):
                pars={'InpStep':10 if gap=='atr' else gap,'InpATRStep':gap=='atr','InpBasketProfit':profit}
                dev.append(run(f'g{gap}-p{profit}','dev',pars))
        top=sorted(dev,key=lambda r:rank(r,30),reverse=True)[:3]
        val=[run(r['tag'].split('-dev-')[0],'val',r['parameters']) for r in top]
        chosen=max(val,key=lambda r:rank(r,20))
        save(ROOT/'selection.json',{'development':dev,'validation':val,'selected':chosen,'eligible_on_validation':rank(chosen,20)[0],
             'frozen_before_later_test':True,'ranking':'positive eligible first; net profit / (1 + equity DD dollars)'})
    elif a.stage=='final':
        chosen=json.loads((ROOT/'selection.json').read_text())['selected'];pars=chosen['parameters']
        out=[run('selected',p,pars) for p in ('later','6m','1y','3y','5y')]
        out.extend([run('selected-slow','6m',pars,delay=1000),run('selected-low-margin','6m',{**pars,'InpLeverageCap':200})])
        save(ROOT/'final.json',out)
    elif a.stage=='diagnostics':
        from run_diagnostics_batch import main
        main()
