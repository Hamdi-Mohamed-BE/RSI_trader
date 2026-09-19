from __future__ import annotations
import argparse,configparser,csv,hashlib,importlib.util,json,re,shutil,subprocess,time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent/'D14 H1 M5 Break Retest Raw 2026-09-13'
spec=importlib.util.spec_from_file_location('existing_native',RAW/'run_raw.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
TESTER=native.TESTER
NAME='XAU Doubling Grid Raw'
EXPERT=Path('AAA Research')/'XAU Doubling Grid 20260913'
SOURCE=ROOT/'EA'/f'{NAME}.mq5'
HASH=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
WINDOWS={k:native.WINDOWS[k] for k in ('3y','6m','1y','5y')}

def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def rows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def dt(s):return datetime.strptime(s,'%Y.%m.%d %H:%M:%S')
def compile_ea():
    for p in [ROOT/'Sets',ROOT/'Audit',ROOT/'Runs',ROOT/'Backtest Reports',TESTER/'MQL5'/'Experts'/EXPERT,TESTER/'reports'/'xau-doubling-grid',TESTER/'backtest-configs'/'xau-doubling-grid']:
        p.mkdir(parents=True,exist_ok=True)
    dest=TESTER/'MQL5'/'Experts'/EXPERT/SOURCE.name;shutil.copy2(SOURCE,dest)
    log=ROOT/'compile.log';started=time.time()
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{dest}" /log:"{log}"',cwd=TESTER,startupinfo=native.hidden(),timeout=120)
    assert log.stat().st_mtime>=started-2
    text=log.read_text(encoding='utf-16',errors='replace')
    assert '0 errors, 0 warnings' in text,text
    shutil.copy2(dest.with_suffix('.ex5'),ROOT/'EA'/f'{NAME}.ex5');print('COMPILED: zero errors, zero warnings',flush=True)

def analyze(tag,period):
    report=ROOT/'Backtest Reports'/f'{tag}.htm';audit=ROOT/'Audit'
    meta=native.parser.parse_report(report);meta.pop('score',None);meta.pop('deals',None)
    soup=native.parser.read_report(report);fields={}
    for r in soup.find_all('tr'):
        cells=[native.parser.compact(c.get_text(' ',strip=True)) for c in r.find_all(['td','th'],recursive=False)]
        for i,c in enumerate(cells[:-1]):
            if c.endswith(':'):fields[c[:-1]]=cells[i+1]
    summary={r['key']:r['value'] for r in rows(audit/f'{tag}-summary.csv')}
    ev=rows(audit/f'{tag}-events.csv');deals=rows(audit/f'{tag}-deals.csv')
    for d in deals:
        for k in ('type','entry','reason'):d[k]=int(d[k])
        for k in ('volume','price','profit','commission','swap','fee'):d[k]=float(d[k])
        d['net']=sum(d[k] for k in ('profit','commission','swap','fee'))
    trading=[d for d in deals if d['symbol']=='XAUUSD' and d['type'] in (0,1)]
    groups=defaultdict(list)
    for d in trading:groups[d['position_id']].append(d)
    ts=[]
    for pid,g in groups.items():
        entries=[d for d in g if d['entry']==0];exits=[d for d in g if d['entry']==1]
        assert entries and exits,(tag,pid,'missing entry/exit')
        vi=sum(d['volume'] for d in entries);vo=sum(d['volume'] for d in exits);assert abs(vi-vo)<1e-7
        bid=int(entries[0]['comment'].split('|')[1])
        ts.append({'position_id':pid,'basket':bid,'leg_index':int(entries[0]['comment'].split('|')[2]),'volume':vi,
                   'open_time':entries[0]['time'],'close_time':exits[-1]['time'],'open_price':sum(d['price']*d['volume'] for d in entries)/vi,
                   'close_price':sum(d['price']*d['volume'] for d in exits)/vo,
                   **{k:round(sum(d[k] for d in g),8) for k in ('profit','commission','swap','fee','net')},
                   'exit_reasons':[d['reason'] for d in exits],'exit_comments':[d['comment'] for d in exits]})
    ts.sort(key=lambda t:(t['close_time'],int(t['position_id'])))
    wins=[t['net'] for t in ts if t['net']>0];losses=[t['net'] for t in ts if t['net']<0]
    assert len(ts)==meta['trades'],(tag,len(ts),meta['trades'])
    assert abs(sum(t['net'] for t in ts)-meta['net_profit'])<.051,(tag,'net mismatch',sum(t['net'] for t in ts),meta['net_profit'])
    assert abs(float(summary['initial_balance'])-3000)<.001
    assert int(float(summary['leverage']))==2000 and float(summary['stopout'])==0 and int(float(summary['stopout_mode']))==0,(tag,'account settings')
    stopouts=[d for d in trading if d['reason']==6]
    stop=stopouts[0]['time'] if stopouts else summary['first_stopout']
    journal=(audit/f'{tag}-journal.log').read_text()
    stop_lines=[x for x in journal.splitlines() if re.search(r'stop out|stopout|stop-out',x,re.I)]
    if stop_lines and not stop:raise AssertionError((tag,'stop-out journal without native deal confirmation',stop_lines))
    secured=summary['first_closed_double'];floating=summary['first_equity_double']
    baskets=[]
    for bid in sorted({t['basket'] for t in ts}):
        g=[t for t in ts if t['basket']==bid]
        baskets.append({'basket':bid,'legs':len(g),'open_time':min(t['open_time'] for t in g),'close_time':max(t['close_time'] for t in g),
                        'net':sum(t['net'] for t in g),'commission':sum(t['commission'] for t in g),'swap':sum(t['swap'] for t in g),
                        'stopout':any(6 in t['exit_reasons'] for t in g),'test_end':any('end of test' in s.lower() for t in g for s in t['exit_comments'])})
    result={**meta,'period':period,'requested_window':WINDOWS[period],'tag':tag,'source_sha256':HASH,
            'actual_first_tick':summary['first_tick'],'actual_last_tick':summary['last_tick'],
            'first_stopout':stop or None,'liquidated':bool(stop),'first_flat_6000':secured or None,'first_equity_6000':floating or None,
            'secured_3000_before_stopout':bool(secured and (not stop or secured<stop)),
            'max_equity_dd_pct':native.parser.percent(fields.get('Equity Drawdown Relative')),
            'equity_dd_relative_native':fields.get('Equity Drawdown Relative'),'equity_dd_maximal_native':fields.get('Equity Drawdown Maximal'),
            'tick_observed_max_equity_dd_pct':float(summary['max_equity_dd_pct']),
            'tick_observed_max_equity_dd_cash':float(summary['max_equity_dd_cash']),
            'peak_equity':float(summary['max_equity']),'min_equity':float(summary['min_equity']),
            'max_total_lots':float(summary['max_total_lots']),'max_single_lot':float(summary['max_single_lot']),'max_legs':int(float(summary['max_legs'])),
            'net_pf':sum(wins)/-sum(losses) if losses else None,'net_win_rate':100*len(wins)/len(ts) if ts else 0,
            'basket_count':len(baskets),'basket_win_rate':100*sum(b['net']>0 for b in baskets)/len(baskets) if baskets else 0,
            'peak_flat_balance':max([3000]+[float(e['balance']) for e in ev if e['event']=='basket_closed']),
            'daily_targets':int(float(summary['daily_targets_reached'])),'blocked_events':int(float(summary['blocked_events'])),
            'first_blocked':summary['first_blocked'] or None,
            'elapsed_calendar_days':(dt(summary['last_tick'])-dt(summary['first_tick'])).total_seconds()/86400,
            'quality_journal':[x for x in journal.splitlines() if re.search(r'real ticks|execution delay|GRID CONTRACT|stop out|stopout|TesterStop',x,re.I)],
            'summary':summary,'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest()}
    save(audit/f'{tag}-trades.json',ts);save(audit/f'{tag}-baskets.json',baskets);save(ROOT/'Runs'/f'{tag}.json',result)
    print(json.dumps({k:result[k] for k in ('period','actual_last_tick','liquidated','secured_3000_before_stopout','final_balance','trades','net_win_rate','max_equity_dd_pct','max_total_lots')},indent=2),flush=True)
    return result

def run(period):
    tag=f'xau-grid-{period}-model4';saved=ROOT/'Runs'/f'{tag}.json'
    if saved.exists():
        r=json.loads(saved.read_text());assert r['source_sha256']==HASH,'Source changed; preserve existing evidence in a new folder';return r
    magic=84913100+list(WINDOWS).index(period);setname=tag+'.set'
    (ROOT/'Sets'/setname).write_text(f'InpInitialLot=0.02\nInpPriceStep=10\nInpDailyTarget=300\nInpMagic={magic}\nInpDeviationPoints=30\n',encoding='utf-8')
    shutil.copy2(ROOT/'Sets'/setname,TESTER/'MQL5'/'Profiles'/'Tester'/setname)
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16');common=dict(ref['Common'])
    start,end=WINDOWS[period]
    content='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Tester]\n'
    content+=f'Expert={EXPERT}\\{NAME}\nExpertParameters={setname}\nSymbol=XAUUSD\nPeriod=M1\nLogin={common["login"]}\nDeposit=3000\nCurrency=USD\nLeverage=1:2000\nModel=4\nExecutionMode=1\nOptimization=0\n'
    content+=f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\xau-doubling-grid\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseCloud=0\nVisual=0\n'
    cfg=TESTER/'backtest-configs'/'xau-doubling-grid'/f'{tag}.ini';cfg.write_text(content,encoding='utf-16')
    sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')};started=time.time();print('START '+tag,flush=True)
    proc=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{cfg.relative_to(TESTER)}'],cwd=TESTER,startupinfo=native.hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:proc.wait(timeout=1800)
    except subprocess.TimeoutExpired:proc.kill();raise RuntimeError('Research tester timeout')
    report=TESTER/'reports'/'xau-doubling-grid'/f'{tag}.htm';assert report.is_file() and report.stat().st_mtime>started-2,'No fresh native report'
    for p in report.parent.glob(tag+'*'):shutil.copy2(p,ROOT/'Backtest Reports'/p.name)
    files=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/DoublingGrid-{magic}-*.csv') if p.stat().st_mtime>started-2];assert len(files)==4,(tag,len(files))
    for p in files:shutil.copy2(p,ROOT/'Audit'/(tag+p.name.split(str(magic),1)[1]))
    log=''
    for p in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if p.stat().st_mtime<started-2:continue
        with p.open('rb') as f:f.seek(sizes.get(p,0));log+=f.read().decode('utf-16-le',errors='replace')
    (ROOT/'Audit'/f'{tag}-journal.log').write_text(log,encoding='utf-8')
    return analyze(tag,period)

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--period',choices=[*WINDOWS,'all'],default='all');cli.add_argument('--analyze-only',action='store_true');args=cli.parse_args()
    if not args.analyze_only:compile_ea()
    out=[]
    for p in (WINDOWS if args.period=='all' else [args.period]):out.append(analyze(f'xau-grid-{p}-model4',p) if args.analyze_only else run(p))
    save(ROOT/'results.json',{'source_sha256':HASH,'rows':out})
