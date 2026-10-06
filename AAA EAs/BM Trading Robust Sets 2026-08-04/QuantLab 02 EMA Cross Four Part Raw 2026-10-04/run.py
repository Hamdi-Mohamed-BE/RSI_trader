"""Standalone frozen research run. Isolated tester; never uses the live MT5 API."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('nqb_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER;SOURCE=R/'EA/Calyx EMA Cross Four Part Research.mq5';EXPERT=SOURCE.with_suffix('.ex5')
PERIODS={'SMOKE':('2026.09.20','2026.10.04'),'1Y':('2025.10.04','2026.10.04'),'3M':('2026.07.04','2026.10.04')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def status(message):
    save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=message));print(message,flush=True)
def compile_ea():
    h.free();log=SOURCE.with_suffix('.compile.log');began=time.time()
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',
                   creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si,timeout=180)
    body=h.text(log) if log.exists() else 'Missing compiler output'
    assert '0 errors, 0 warnings' in body,body[-7000:]
    assert EXPERT.stat().st_mtime>=began-2
    save(R/'build.json',dict(source_sha256=sha(SOURCE),binary_sha256=sha(EXPERT),compiler_tail=body[-600:]))
    status('COMPILED standalone research EA: 0 errors, 0 warnings')
def initial_orders(report):
    from app.mt5_evidence_jobs import _clean
    text=h._read_report(report);a=text.lower().index('<b>orders</b>');b=text.lower().index('<b>deals</b>')
    rows=[]
    for body in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text[a:b],re.S|re.I):
        cells=[_clean(v) for v in re.findall(r'<td\b[^>]*>(.*?)</td>',body,re.S|re.I)]
        if len(cells)>=11 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]):rows.append(cells)
    return rows

def exact_hedged_trades(report,journal):
    """Pair by native position ticket, never by same-symbol FIFO.

    The four portions can close out of order and have different lot sizes.
    Native trigger/close messages link exit order IDs to hedged position IDs;
    the HTML Deals table remains the authority for prices, times and costs.
    Any missing or contradictory association fails the experiment.
    """
    from app.mt5_evidence_jobs import _clean,_number
    exit_positions={};pending=None
    def link(order,position):
        assert order not in exit_positions or exit_positions[order]==position
        exit_positions[order]=position
    for line in journal.splitlines():
        hit=re.search(r'(?:take profit|stop loss) triggered #(\d+).*?\[#(\d+) (?:buy|sell)',line)
        if hit:link(int(hit[2]),int(hit[1]))
        hit=re.search(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+market (?:buy|sell).*?, close #(\d+)',line)
        if hit:pending=(hit[1],int(hit[2]))
        hit=re.search(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+deal #\d+.*?done \(based on order #(\d+)\)',line)
        if hit and pending:
            assert hit[1]==pending[0],'Manual-close journal association crossed timestamps'
            link(int(hit[2]),pending[1]);pending=None
    assert pending is None
    text=h._read_report(report);text=text[text.lower().index('<b>deals</b>'):]
    entries={};completed=[];all_deal_net=0.0;seen=set()
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text,re.S|re.I):
        c=[_clean(v) for v in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S|re.I)]
        if len(c)<13 or not c[2] or c[3].lower() not in ('buy','sell'):continue
        assert c[4].lower() in ('in','out'),'Partial reversal/close-by unsupported in frozen research'
        deal=int(c[1]);assert deal not in seen;seen.add(deal)
        order=int(c[7]);volume=_number(c[5]);price=_number(c[6])
        commission=_number(c[8]);swap=_number(c[9]);profit=_number(c[10]);all_deal_net+=commission+swap+profit
        when=c[0].replace('.','-',2).replace(' ','T',1)
        if c[4].lower()=='in':
            assert order not in entries
            entries[order]=dict(side='Long' if c[3].lower()=='buy' else 'Short',volume=volume,
              open_time=when,open_price=price,commission=commission,swap=swap,gross_profit=profit,
              entry_comment=c[12],entry_order=order,entry_deal=deal,symbol=c[2])
            continue
        assert order in exit_positions,f'No exact native position association for exit order {order}'
        pos=exit_positions[order];assert pos in entries,f'Unmatched/duplicate native exit for position {pos}'
        e=entries.pop(pos);assert abs(e['volume']-volume)<1e-8
        assert c[2]==e['symbol'] and c[3].lower()==('sell' if e['side']=='Long' else 'buy')
        costs=round(e['commission']+commission+e['swap']+swap,2);gross=round(e['gross_profit']+profit,2)
        net=round(gross+costs,2)
        completed.append(dict(number=len(completed)+1,ea='Independent EMA Cross Four Part',symbol=e['symbol'],
           side=e['side'],volume=volume,open_time=e['open_time'],close_time=when,open_price=e['open_price'],close_price=price,
           gross_profit=gross,commission=round(e['commission']+commission,2),swap=round(e['swap']+swap,2),
           total_costs=costs,net_profit=net,result='Win' if net>0 else 'Loss' if net<0 else 'Flat',
           source='Native MT5 deals paired by journal position ticket',entry_comment=e['entry_comment'],exit_comment=c[12],
           position_id=pos,entry_order=e['entry_order'],entry_deal=e['entry_deal'],exit_order=order,exit_deal=deal))
    assert not entries,'Open/unmatched native positions remain'
    assert abs(sum(t['net_profit'] for t in completed)-all_deal_net)<.015
    return completed
def basket_metrics(baskets):
    pnl=[b['net_profit'] for b in baskets];wins=[x for x in pnl if x>0];losses=[x for x in pnl if x<0]
    w=l=mw=ml=0
    for b in sorted(baskets,key=lambda b:b['close_time']):
        if b['net_profit']>0:w+=1;l=0
        elif b['net_profit']<0:l+=1;w=0
        else:w=l=0
        mw=max(mw,w);ml=max(ml,l)
    return dict(baskets=len(baskets),net_profit=round(sum(pnl),2),return_pct=sum(pnl)/100,
                net_pf=sum(wins)/-sum(losses) if losses else None,
                win_rate_pct=100*len(wins)/len(pnl) if pnl else None,
                wins=len(wins),losses=len(losses),flat=sum(x==0 for x in pnl),max_win_streak=mw,max_loss_streak=ml,
                avg_win_usd=sum(wins)/len(wins) if wins else None,avg_loss_usd=sum(losses)/len(losses) if losses else None,
                avg_hold_hours=sum(b['hold_hours'] for b in baskets)/len(baskets) if baskets else None,
                boundary_baskets=sum(b['boundary_exit'] for b in baskets),boundary_net_usd=round(sum(b['net_profit'] for b in baskets if b['boundary_exit']),2))
def parse_signal_audit(journal,baskets):
    signals={}
    for line in journal.splitlines():
        match=re.search(r'QNB_SIGNAL date=(\d+) closed_bar=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) direction=(-?\d+) fast=([\d.]+) slow=([\d.]+) previous_fast=([\d.]+) previous_slow=([\d.]+) adx=([\d.]+) plus_di=([\d.]+) minus_di=([\d.]+) atr=([\d.]+)',line)
        if match:
            key=match[1];v=dict(closed_bar=match[2],direction=int(match[3]),**dict(zip(['fast','slow','previous_fast','previous_slow','adx','plus_di','minus_di','atr'],map(float,match.groups()[3:]))))
            if key in signals:assert signals[key]==v
            signals[key]=v
    entries={}
    for line in journal.splitlines():
        match=re.search(r'QNB_ENTRY date=(\d+) leg=(\d+).*?quarter_cash=([\d.]+) requested_stop_cash=([\d.]+) actual_stop_cash=([\d.]+)',line)
        if match:entries[match[1],int(match[2])]=dict(quarter_cash=float(match[3]),requested_stop_cash=float(match[4]),actual_stop_cash=float(match[5]))
    for b in baskets:
        s=signals[b['id']];op=pd.Timestamp(b['open_time'],tz='UTC')
        signal_time=pd.Timestamp(s['closed_bar'].replace('.','-'),tz='UTC')
        assert 180<=(op-signal_time).total_seconds()<190,'Entry not immediately after closed M3 signal'
        assert s['adx']>=20-1e-7 and s['atr']>0
        if b['side']=='Long':
            assert s['previous_fast']<=s['previous_slow']+1e-7 and s['fast']>s['slow'] and s['plus_di']>s['minus_di']
        else:
            assert s['previous_fast']>=s['previous_slow']-1e-7 and s['fast']<s['slow'] and s['minus_di']>s['plus_di']
        b['signal_audit']=s
        for leg in b['legs']:
            audit=entries[b['id'],leg['leg']];assert audit['requested_stop_cash']<=audit['quarter_cash']+.0002
            leg['risk_audit']=audit
        b['planned_budget_usd']=sum(t['risk_audit']['quarter_cash'] for t in b['legs'])
        b['actual_initial_stop_risk_usd']=sum(t['risk_audit']['actual_stop_cash'] for t in b['legs'])
    return dict(accepted_signal_dates=len(signals),completed_baskets=len(baskets),entry_audits=len(entries))
def group_baskets(trades,orders):
    groups={}
    for t in trades:
        match=re.fullmatch(r'QNB(\d{8})_L([1-4])',t['entry_comment']);assert match,t
        t['basket_id']=match[1];t['leg']=int(match[2]);groups.setdefault(t['basket_id'],[]).append(t)
        op=pd.Timestamp(t['open_time'],tz='UTC');cl=pd.Timestamp(t['close_time'],tz='UTC')
        t['open_ny']=op.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M:%S')
        t['close_ny']=cl.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M:%S')
        t['hold_hours']=round((cl-op).total_seconds()/3600,5)
        t['boundary_exit']='end of test' in t['exit_comment'].lower()
        when=t['open_time'].replace('-','.').replace('T',' ')
        matches=[o for o in orders if o[0]==when and o[10]==t['entry_comment']]
        assert len(matches)==1
        t['initial_sl']=float(matches[0][6].replace(' ',''));t['initial_tp']=float(matches[0][7].replace(' ','')) if matches[0][7] else None
        risk=abs(t['open_price']-t['initial_sl'])
        assert risk>0 and ((t['initial_sl']<t['open_price']) if t['side']=='Long' else (t['initial_sl']>t['open_price']))
        t['initial_rr']=abs(t['initial_tp']-t['open_price'])/risk if t['initial_tp'] is not None else None
        if t['leg']==4:assert t['initial_tp'] is None
        else:assert t['initial_tp'] is not None
        t['exit_reason']='Test-end liquidation' if t['boundary_exit'] else 'Target' if t['exit_comment'].startswith('tp ') else 'Stop/trailing stop' if t['exit_comment'].startswith('sl ') else 'Time/Friday close'
    baskets=[]
    for id_,legs in groups.items():
        legs=sorted(legs,key=lambda t:t['leg']);assert [t['leg'] for t in legs]==[1,2,3,4]
        assert len({t['side'] for t in legs})==1
        assert len({t['initial_sl'] for t in legs})==1
        opened=min(t['open_time'] for t in legs);closed=max(t['close_time'] for t in legs)
        net=round(sum(t['net_profit'] for t in legs),2)
        b=dict(id=id_,side=legs[0]['side'],open_time=opened,close_time=closed,open_ny=min(t['open_ny'] for t in legs),close_ny=max(t['close_ny'] for t in legs),
               hold_hours=round((pd.Timestamp(closed)-pd.Timestamp(opened)).total_seconds()/3600,5),
               net_profit=net,commission=round(sum(t['commission'] for t in legs),2),swap=round(sum(t['swap'] for t in legs),2),
               gross_profit=round(sum(t['gross_profit'] for t in legs),2),boundary_exit=any(t['boundary_exit'] for t in legs),legs=legs)
        assert b['open_ny'][:10].replace('-','')==id_
        clock=b['open_ny'][11:16];assert '09:33'<=clock<='15:30'
        assert pd.Timestamp(b['open_ny']).weekday()<5
        assert abs(b['gross_profit']+b['commission']+b['swap']-net)<.025
        baskets.append(b)
    baskets.sort(key=lambda b:b['open_time'])
    assert all(a['close_time']<=b['open_time'] for a,b in zip(baskets,baskets[1:])), 'Overlapping baskets'
    return baskets
def run(window):
    if window!='SMOKE':assert (R/'native/SMOKE/results.json').exists(),'Smoke must reconcile before longer runs'
    start,end=PERIODS[window];folder=R/'native'/window;folder.mkdir(parents=True,exist_ok=True)
    inputs=dict(l.split('=',1) for l in (R/'RAW.set').read_text().splitlines() if '=' in l)
    assert inputs['InpSignalTimeframe']=='3' and inputs['InpBasketRiskPercent']=='1.0'
    frozen=dict(window=window,start=start,end_exclusive=end,deposit=10000,risk_per_basket_pct=1,model=4,delay_ms=150,
                symbol='USTEC',timeframe='M3',broker='Exness-MT5Trial16',binary_sha256=sha(EXPERT),source_sha256=sha(SOURCE),
                set_sha256=sha(R/'RAW.set'),protocol_sha256=sha(R/'PROTOCOL.txt'),inputs=inputs,
                independent_assumptions=True,no_unrelated_ea_comparison=True)
    mp=folder/'manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==frozen,'Frozen experiment changed'
    else:save(mp,frozen)
    if (folder/'results.json').exists():return json.loads((folder/'results.json').read_text())
    h.free();profile=T/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr'))
    dest=T/'MQL5/Experts/AAA Research/QuantLabNQBIndependent20261004';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(EXPERT,dest/'RAW.ex5');assert sha(dest/'RAW.ex5')==frozen['binary_sha256']
    setname='qnbi-'+window+'.set';shutil.copy2(R/'RAW.set',T/'MQL5/Profiles/Tester'/setname)
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    rp=T/'reports/quantlab-nqb-independent20261004'/(window+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
    ini=folder/'tester.ini'
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\QuantLabNQBIndependent20261004\\RAW
ExpertParameters={setname}
Symbol=USTEC
Period=M3
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\quantlab-nqb-independent20261004\\{window}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free();status('START '+window)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
                          cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    save(folder/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe'),started=began))
    try:proc.wait(timeout=900)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=20);raise RuntimeError('Only owned isolated tester stopped: test timed out')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2
    assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|QNB_ENTRY_FAILED|QNB_REQUIRES_HEDGING',journal,re.I),'Invalid native run: inspect isolated journal'
    report=h._read_report(rp);assert all(v in report for v in [start,end,'USTEC','M3'])
    actual=h._report_inputs(rp)
    assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'Preset mismatch'
    from app.mt5_evidence_jobs import _metric,_number
    native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
    trades=exact_hedged_trades(rp,journal);orders=initial_orders(rp)
    assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.10
    baskets=group_baskets(trades,orders)
    assert len(trades)==4*len(baskets)
    audits=parse_signal_audit(journal,baskets)
    summary=re.findall(r'QNB_SUMMARY baskets=(\d+) minlot_skips=(\d+) entry_errors=(\d+) modify_errors=(\d+) close_errors=(\d+)',journal)
    assert summary and all(int(x[0])==len(baskets) and int(x[2])==0 for x in summary)
    assert not re.search(r'QNB_CLOSE_FAILED',journal),'Close failure, inspect actual outcomes'
    for t in trades:
        assert pd.Timestamp(t['open_time'],tz='UTC')>=pd.Timestamp(start.replace('.','-'),tz='UTC')
        assert pd.Timestamp(t['close_time'],tz='UTC')<pd.Timestamp(end.replace('.','-'),tz='UTC')
    if window!='1Y':assert native['history_quality']=='100% real ticks'
    stats=basket_metrics(baskets);assert abs(stats['net_profit']-native['net_profit'])<.015
    pnl=[t['net_profit'] for t in trades];pos=sum(x for x in pnl if x>0);neg=-sum(x for x in pnl if x<0)
    result=dict(manifest=frozen,native=native,basket_metrics=stats,baskets=baskets,trades=trades,orders=orders,
                leg_net_pf=pos/neg if neg else None,leg_net_win_rate_pct=100*sum(x>0 for x in pnl)/len(pnl) if pnl else None,
                commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),
                signal_audit=audits,ea_counters=dict(zip(['baskets','minlot_skips','entry_errors','modify_errors','close_errors'],map(int,summary[-1]))),
                report_sha256=sha(rp),seconds=round(time.time()-began,1),
                tick_notes=sorted(set(x for x in journal.splitlines() if re.search('real ticks begin|real ticks absent|ticks discarded',x,re.I)))[:15])
    save(folder/'results.json',result);save(folder/'trades.json',trades);save(folder/'baskets.json',baskets);save(folder/'orders.json',orders)
    (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    for p in rp.parent.glob(window+'*.png'):shutil.copy2(p,folder/p.name)
    csvrows=[]
    for b in baskets:
        csvrows.append({**{k:v for k,v in b.items() if k not in ['legs','signal_audit']},**{f'leg{t["leg"]}_net_usd':t['net_profit'] for t in b['legs']}})
    if csvrows:
        with (folder/'baskets.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(csvrows[0]));writer.writeheader();writer.writerows(csvrows)
    legrows=[{k:v for k,v in t.items() if k!='risk_audit'} for t in trades]
    if legrows:
        with (folder/'legs.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(legrows[0]));writer.writeheader();writer.writerows(legrows)
    status('DONE '+window+' '+json.dumps(dict(**stats,equity_dd_pct=native['equity_dd_pct'],history_quality=native['history_quality'])))
    return result
if __name__=='__main__':
    if sys.argv[1]=='compile':compile_ea()
    else:
        for window in sys.argv[1:]:run(window)
        rows=[json.loads(p.read_text()) for p in sorted((R/'native').glob('*/results.json'))]
        save(R/'RESULTS.json',rows);status('Finished standalone cases; no portfolio or comparison changes')
