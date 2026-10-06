"""Frozen shared-account UK100 native tests. No live MT5 API or unrelated controls."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent;os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('uk_native_helpers',B/'QuantLab 02 EMA Cross Four Part Raw 2026-10-04/run.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior);h=prior.h;T=h.TESTER
SOURCE=R/'EA/Calyx UK100 Three Module Research.mq5';EXPERT=SOURCE.with_suffix('.ex5')
PERIODS={'SMOKE':('2026.09.01','2026.10.04'),'1Y':('2025.10.04','2026.10.04'),'3M':('2026.07.04','2026.10.04')}
LABELS={1:'Post-drop recovery',2:'Monday dip',3:'Trend pullback'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(v):save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=v));print(v,flush=True)
def compile_ea():
    h.free();log=SOURCE.with_suffix('.compile.log');began=time.time()
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si,timeout=180)
    body=h.text(log) if log.exists() else 'No compiler output'
    assert '0 errors, 0 warnings' in body,body[-8000:]
    assert EXPERT.stat().st_mtime>=began-2
    save(R/'build.json',dict(source_sha256=sha(SOURCE),binary_sha256=sha(EXPERT),compiler_tail=body[-650:]))
    status('COMPILED research EA: zero errors/warnings')

def exact_trades(path,journal):
    from app.mt5_evidence_jobs import _clean,_number
    mapping={}
    for line in journal.splitlines():
        hit=re.search(r'UKT_DEAL_MAP deal=(\d+) position=(\d+) order=(\d+) entry=(\d+)',line)
        if hit:
            deal=int(hit[1]);v=dict(position=int(hit[2]),order=int(hit[3]),entry=int(hit[4]))
            assert deal not in mapping or mapping[deal]==v;mapping[deal]=v
    assert mapping,'No exact native deal-position audit'
    body=h._read_report(path);body=body[body.lower().index('<b>deals</b>'):]
    entries={};trades=[];ledger=[];balance=10000.;seen=set()
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',body,re.S|re.I):
        c=[_clean(v) for v in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S|re.I)]
        if len(c)<13 or not c[2] or c[3].lower() not in ('buy','sell'):continue
        deal=int(c[1]);assert deal not in seen;seen.add(deal);m=mapping[deal];order=int(c[7])
        assert order==m['order'] and c[4].lower() in ('in','out')
        assert m['entry']==(0 if c[4].lower()=='in' else 1)
        pos=m['position'];volume=_number(c[5]);price=_number(c[6])
        commission=_number(c[8]);swap=_number(c[9]);gross=_number(c[10]);net=round(commission+swap+gross,2)
        when=c[0].replace('.','-',2).replace(' ','T',1);balance=round(balance+net,2)
        assert abs(balance-_number(c[11]))<.035,'Actual deal balance does not reconcile'
        ledger.append(dict(deal=deal,time=when,position_id=pos,direction=c[4],cash_flow=net,balance=_number(c[11])))
        if c[4].lower()=='in':
            assert pos not in entries
            match=re.fullmatch(r'UKT(\d{8})_M([1-3])',c[12]);assert match
            entries[pos]=dict(module=int(match[2]),date=match[1],volume=volume,open_price=price,open_time=when,
              side='Long' if c[3].lower()=='buy' else 'Short',gross_profit=gross,commission=commission,swap=swap,
              entry_comment=c[12],entry_deal=deal,entry_order=order)
            continue
        assert pos in entries,'No complete-position association'
        e=entries.pop(pos);assert abs(volume-e['volume'])<1e-8
        assert c[3].lower()==('sell' if e['side']=='Long' else 'buy')
        pnl=round(e['gross_profit']+gross+e['commission']+commission+e['swap']+swap,2)
        trades.append(dict(number=len(trades)+1,position_id=pos,module=e['module'],module_name=LABELS[e['module']],symbol=c[2],
          side=e['side'],volume=volume,open_time=e['open_time'],close_time=when,open_price=e['open_price'],close_price=price,
          gross_profit=round(e['gross_profit']+gross,2),commission=round(e['commission']+commission,2),swap=round(e['swap']+swap,2),
          net_profit=pnl,result='Win' if pnl>0 else 'Loss' if pnl<0 else 'Flat',date=e['date'],
          entry_comment=e['entry_comment'],exit_comment=c[12],entry_deal=e['entry_deal'],exit_deal=deal,
          entry_order=e['entry_order'],exit_order=order,boundary_exit='end of test' in c[12].lower()))
    assert not entries and set(mapping)==seen
    assert abs(sum(t['net_profit'] for t in trades)-sum(x['cash_flow'] for x in ledger))<.015
    return trades,ledger

def metrics(ts):
    pnl=[t['net_profit'] for t in ts];wins=[x for x in pnl if x>0];losses=[x for x in pnl if x<0]
    w=l=mw=ml=0
    for t in sorted(ts,key=lambda t:(t['close_time'],t['exit_deal'])):
        if t['net_profit']>0:w+=1;l=0
        elif t['net_profit']<0:l+=1;w=0
        else:w=l=0
        mw=max(mw,w);ml=max(ml,l)
    return dict(trades=len(ts),net_profit=round(sum(pnl),2),return_pct=sum(pnl)/100,
      net_pf=sum(wins)/-sum(losses) if losses else None,win_rate_pct=100*len(wins)/len(ts) if ts else None,
      wins=len(wins),losses=len(losses),flat=sum(x==0 for x in pnl),max_win_streak=mw,max_loss_streak=ml,
      avg_win_usd=sum(wins)/len(wins) if wins else None,avg_loss_usd=sum(losses)/len(losses) if losses else None,
      expectancy_usd=sum(pnl)/len(ts) if ts else None,boundary_positions=sum(t['boundary_exit'] for t in ts))

def audit(trades,orders,journal):
    entries={};signals={};outcomes={}
    for line in journal.splitlines():
        if 'UKT_SIGNAL ' in line:
            hit=re.search(r'UKT_SIGNAL date=(\d+) module=(\d+) direction=(-?\d+) bar=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) (.*)',line)
            assert hit
            s=dict(date=hit[1],module=int(hit[2]),direction=int(hit[3]),bar=hit[4],
                   **{k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',hit[5])})
            key=s['date'],s['module'];assert key not in signals or signals[key]==s;signals[key]=s
        hit=re.search(r'UKT_ENTRY date=(\d+) module=(\d+) position=(\d+) .*?equity=([\d.]+) budget=([\d.]+) requested_stop_cash=([\d.]+) actual_stop_cash=([\d.]+)',line)
        if hit:
            e=dict(date=hit[1],module=int(hit[2]),position=int(hit[3]),equity=float(hit[4]),budget=float(hit[5]),
                   requested_stop_cash=float(hit[6]),actual_stop_cash=float(hit[7]))
            pos=e['position'];assert pos not in entries or entries[pos]==e;entries[pos]=e
        hit=re.search(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+UKT_RESULT position=(\d+) module=(\d+) net=(-?[\d.]+) losing_streak=(\d+) pause=(\d+) blocked_until=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})',line)
        if hit:
            o=dict(time=hit[1].replace('.','-',2).replace(' ','T',1),position=int(hit[2]),module=int(hit[3]),net=float(hit[4]),
                   losing_streak=int(hit[5]),pause=bool(int(hit[6])),blocked_until=hit[7].replace('.','-',2).replace(' ','T',1))
            assert o['position'] not in outcomes or outcomes[o['position']]==o;outcomes[o['position']]=o
    assert len(entries)==len(trades)==len(signals)
    seen=set();active=[];max_active=0
    for t in sorted(trades,key=lambda t:t['entry_deal']):
        op=pd.Timestamp(t['open_time'],tz='UTC');cl=pd.Timestamp(t['close_time'],tz='UTC')
        london=op.tz_convert('Europe/London');close_london=cl.tz_convert('Europe/London')
        t['open_london']=london.strftime('%Y-%m-%d %H:%M:%S');t['close_london']=close_london.strftime('%Y-%m-%d %H:%M:%S')
        t['hold_hours']=(cl-op).total_seconds()/3600;t['overnight']=t['open_london'][:10]!=t['close_london'][:10]
        t['weekend_hold']=(close_london.date()-london.date()).days>=2 and any(d.weekday()>=5 for d in pd.date_range(london.normalize(),close_london.normalize(),freq='D'))
        assert london.weekday()<5 and 8<=london.hour<16 and t['date']==london.strftime('%Y%m%d')
        key=t['date'],t['module'];assert key not in seen;seen.add(key)
        s=signals[key];t['signal_audit']=s;e=entries[t['position_id']];t['risk_audit']=e
        assert e['module']==t['module'] and e['date']==t['date']
        # Native account-currency profit estimates are rounded to cents. This
        # audit is after the delayed fill, not the pre-order one-lot estimate.
        # Keep tiny observed cent-rounding differences, not fictitious resizing.
        assert e['requested_stop_cash']<=e['budget']+.011 and abs(e['budget']-.01*e['equity'])<.0002
        assert 3600<=(op-pd.Timestamp(s['bar'].replace('.','-'),tz='UTC')).total_seconds()<3610
        assert s['direction']==(1 if t['side']=='Long' else -1) and s['atr']>0 and s['previous_atr']>0
        if t['module'] in (1,2):assert s['signal_close']>s['signal_open'] and s['signal_close']>s['prior_high'] and t['side']=='Long'
        if t['module']==1:
            assert s['drop']>=3*s['previous_atr']-1e-7 and s['prior_rsi']<=10+1e-7
            assert abs(s['drop']-(s['peak']-s['prior_close']))<1e-7
        if t['module']==2:
            assert london.weekday()==0 and s['friday']>0 and s['prior_close']<=s['friday']-.5*s['previous_atr']+1e-7
        if t['module']==3:
            if t['side']=='Long':assert s['trend']>s['slow'] and s['trend']>s['previous_trend'] and s['prior_close']<=s['previous_pull'] and s['signal_close']>s['pull'] and s['signal_close']>s['signal_open']
            else:assert s['trend']<s['slow'] and s['trend']<s['previous_trend'] and s['prior_close']>=s['previous_pull'] and s['signal_close']<s['pull'] and s['signal_close']<s['signal_open']
        matches=[o for o in orders if int(o[1])==t['entry_order']]
        assert len(matches)==1 and matches[0][10]==t['entry_comment']
        sl=float(matches[0][6].replace(' ',''));tp=float(matches[0][7].replace(' ',''))
        t['initial_sl']=sl;t['initial_tp']=tp;t['actual_initial_rr']=abs(tp-t['open_price'])/abs(sl-t['open_price'])
        assert (sl<t['open_price']<tp) if t['side']=='Long' else (tp<t['open_price']<sl)
        t['exit_reason']='Test-end liquidation' if t['boundary_exit'] else 'Target' if t['exit_comment'].startswith('tp ') else 'Stop' if t['exit_comment'].startswith('sl ') else '48-hour exit'
        active=[x for x in active if x['exit_deal']>t['entry_deal']]
        assert all(x['module']!=t['module'] for x in active)
        active.append(t);max_active=max(max_active,len(active));assert len(active)<=3
        if t['position_id'] in outcomes:
            o=outcomes[t['position_id']];assert o['module']==t['module'] and abs(o['net']-t['net_profit'])<.011
        else:assert t['boundary_exit'],'Missing complete-position loss-brake audit'
    pauses=[o for o in outcomes.values() if o['pause']]
    # Completed-position ordering and net-cost accounting must reproduce the loss brake.
    streak=0
    for t in sorted(trades,key=lambda t:t['exit_deal']):
        if t['position_id'] not in outcomes:continue
        o=outcomes[t['position_id']];streak=streak+1 if t['net_profit']<0 else 0
        should_pause=streak>=3
        assert o['pause']==should_pause
        if should_pause:
            streak=0;assert (pd.Timestamp(o['blocked_until'])-pd.Timestamp(o['time'])).total_seconds()==86400
        assert o['losing_streak']==streak
    for p in pauses:
        assert not any(p['time']<t['open_time']<p['blocked_until'] for t in trades),'Entry occurred during loss-brake pause'
    return dict(accepted_signals=len(signals),exact_entry_risk_audits=len(entries),net_outcomes=len(outcomes),pauses=len(pauses),
      requested_risk_cash_precision_allowance_usd=.011,
      maximum_requested_risk_excess_usd=max((t['risk_audit']['requested_stop_cash']-t['risk_audit']['budget'] for t in trades),default=0),
      maximum_concurrent_positions=max_active,overnight_positions=sum(t['overnight'] for t in trades),
      weekend_positions=sum(t['weekend_hold'] for t in trades),end_liquidations=sum(t['boundary_exit'] for t in trades))

def run(window):
    if window!='SMOKE':assert (R/'native/SMOKE/results.json').exists(),'Reconcile smoke before longer tests'
    start,end=PERIODS[window];folder=R/'native'/window;folder.mkdir(parents=True,exist_ok=True)
    inputs=dict(l.split('=',1) for l in (R/'RAW.set').read_text().splitlines() if '=' in l)
    frozen=dict(window=window,start=start,end_exclusive=end,deposit=10000,risk_percent_per_trade=1,maximum_slots=3,
      model=4,delay_ms=150,symbol='UK100',timeframe='H1',broker='Exness-MT5Trial16',shared_account=True,independent_assumptions=True,
      source_sha256=sha(SOURCE),binary_sha256=sha(EXPERT),set_sha256=sha(R/'RAW.set'),protocol_sha256=sha(R/'PROTOCOL.txt'),inputs=inputs)
    mp=folder/'manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==frozen
    else:save(mp,frozen)
    if (folder/'results.json').exists():return json.loads((folder/'results.json').read_text())
    h.free();profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    dest=T/'MQL5/Experts/AAA Research/QuantLabUKIndependent20261004';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(EXPERT,dest/'RAW.ex5');assert sha(dest/'RAW.ex5')==frozen['binary_sha256']
    setname='ukt-'+window+'.set';shutil.copy2(R/'RAW.set',T/'MQL5/Profiles/Tester'/setname)
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ini=folder/'tester.ini'
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\QuantLabUKIndependent20261004\\RAW
ExpertParameters={setname}
Symbol=UK100
Period=H1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\quantlab-uk-independent20261004\\{window}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    rp=T/'reports/quantlab-uk-independent20261004'/(window+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
    offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free();status('START '+window)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
      cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    save(folder/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
    try:proc.wait(timeout=900)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Own isolated tester timed out')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2
    assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|UKT_ENTRY_FAILED|UKT_CLOSE_FAILED|UKT_AUDIT_FAILED|UKT_REQUIRES_HEDGING',journal,re.I),'Invalid native run; inspect isolated journal'
    body=h._read_report(rp);assert all(v in body for v in [start,end,'UK100','H1'])
    actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items())
    from app.mt5_evidence_jobs import _number,_metric
    native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(body,'Equity Drawdown Relative'))
    trades,ledger=exact_trades(rp,journal);orders=prior.initial_orders(rp)
    assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.015
    stats=metrics(trades);audits=audit(trades,orders,journal)
    counts={i:sum(t['module']==i for t in trades) for i in LABELS}
    summaries=re.findall(r'UKT_SUMMARY drop=(\d+) monday=(\d+) trend=(\d+) pauses=(\d+) blocked_bars=(\d+) minlot_skips=(\d+) entry_errors=(\d+) close_errors=(\d+) processed_exits=(\d+)',journal)
    assert summaries and all(tuple(map(int,s[:3]))==tuple(counts.values()) for s in summaries)
    counters=dict(zip(['drop','monday','trend','pauses','blocked_bars','minlot_skips','entry_errors','close_errors','processed_exits'],map(int,summaries[-1])))
    assert counters['pauses']==audits['pauses'] and counters['processed_exits']==audits['net_outcomes']
    for t in trades:
        assert pd.Timestamp(t['open_time'])>=pd.Timestamp(start.replace('.','-')) and pd.Timestamp(t['close_time'])<pd.Timestamp(end.replace('.','-'))
    result=dict(manifest=frozen,native=native,net_metrics=stats,module_metrics={str(i):metrics([t for t in trades if t['module']==i]) for i in LABELS},
      trades=trades,ledger=ledger,orders=orders,audit=audits,counters=counters,
      commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),
      report_sha256=sha(rp),seconds=round(time.time()-began,1),
      tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:15])
    save(folder/'results.json',result);save(folder/'trades.json',trades);save(folder/'ledger.json',ledger)
    (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    for p in rp.parent.glob(window+'*.png'):shutil.copy2(p,folder/p.name)
    rows=[{k:v for k,v in t.items() if k not in ['signal_audit','risk_audit']} for t in trades]
    if rows:
        with (folder/'trades.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    status('DONE '+window+' '+json.dumps(dict(**stats,equity_dd_pct=native['equity_dd_pct'],history_quality=native['history_quality'],modules=counts,pauses=audits['pauses'])))
    return result
if __name__=='__main__':
    if sys.argv[1]=='compile':compile_ea()
    else:
        for w in sys.argv[1:]:run(w)
        save(R/'RESULTS.json',[json.loads(p.read_text()) for p in sorted((R/'native').glob('*/results.json'))])
        status('Standalone raw tests finished; no production changes')
