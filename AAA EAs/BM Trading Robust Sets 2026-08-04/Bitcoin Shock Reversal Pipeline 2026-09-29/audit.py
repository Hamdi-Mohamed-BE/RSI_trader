"""Offline Bitcoin evidence audit; no terminal connection or strategy changes."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'Market Style Bots Raw 2026-09-29'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):
    (ROOT/name).write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')
def stamp(t):return pd.to_datetime(int(t),unit='s',utc=True).isoformat()
def streaks(p):
    w=l=mw=ml=0
    for x in p:
        w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
    return mw,ml

def main():
    spec=importlib.util.spec_from_file_location('bitcoin_oracle',SOURCE/'verify_signals.py')
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    build=json.loads((ROOT/'BUILD.json').read_text())
    assert all(sha(ROOT/k)==v==sha(SOURCE/k) for k,v in build.items())
    provenance=json.loads((ROOT/'PROVENANCE.json').read_text())
    assert sha(ROOT/'PROTOCOL.md')==provenance['protocol_sha256']
    assert sha(ROOT/'confirm.py')==provenance['wrapper_sha256']
    assert sha(SOURCE/'run.py')==provenance['source_runner_sha256']
    bars=pd.read_csv(SOURCE/'data/BTCUSD-H1.csv.gz').set_index('time')
    assert bars.index.is_monotonic_increasing and bars.index.is_unique
    times=pd.to_datetime(bars.index,unit='s',utc=True)
    evidence={};results=[];carries=[];verified=[];ledgers={}
    for window,model in [('6m',4),('1y',4),('3y',1),('5y',1),('3y',4),('5y',4)]:
        for control in [False,True]:
            tag=f"bitcoin-reversal-{'control' if control else 'raw'}-{window}-m{model}"
            fresh=window in ['3y','5y'] and model==4
            out=(ROOT if fresh else SOURCE)/'native'/tag
            r=json.loads((out/'run.json').read_text());assert r['build']==build
            assert r['bot']==dict(name='bitcoin-reversal',symbol='BTCUSD',mode=1,rr=1.5)
            assert r['inputs']['InpMode']=='1' and r['inputs']['InpRR']=='1.5'
            assert r['inputs']['InpControl']==str(control).lower()
            assert r['inputs']['InpRiskPercent']=='1' and r['inputs']['InpSeed']=='290929'
            a=r['attempt'];report=out/f'report-attempt{a}.htm.gz'
            assert hashlib.sha256(gzip.decompress(report.read_bytes())).hexdigest()==r['report_sha']
            d=pd.read_csv(out/'trades.csv.gz').sort_values(['open_epoch','position_id'])
            signals=pd.read_csv(out/'signals.csv.gz');trace=pd.read_csv(out/'trace.csv.gz')
            assert trace.time.is_monotonic_increasing and trace.time.is_unique
            p=d.net_profit.to_numpy();m=r['metrics'];assert len(d)==len(signals)==m['trades']
            assert d.position_id.is_unique and signals.position_id.is_unique
            assert set(d.position_id)==set(signals.position_id)
            assert np.allclose(d.volume,d.closed_volume,atol=1e-8)
            assert np.allclose(d.net_profit,d[['gross_profit','commission','swap','fee']].sum(axis=1),atol=.011)
            assert abs(sum(p)-m['net_profit'])<.02 and abs(10000+sum(p)-m['final_balance'])<.02
            gp=sum(max(x,0) for x in p);gl=-sum(min(x,0) for x in p)
            assert gl>0 and abs(gp/gl-m['profit_factor'])<1e-8
            assert (d.actual_risk>0).all() and (d.side*(d.open_price-d.initial_sl)>0).all()
            assert (d.side*(d.initial_tp-d.open_price)>0).all()
            assert (d.open_epoch%3600<301).all() and not (d.open_epoch//86400).duplicated().any()
            assert (d.open_epoch.to_numpy()[1:]>=d.close_epoch.to_numpy()[:-1]).all()
            before_balance=10000+np.r_[0,np.cumsum(p)[:-1]]
            assert np.allclose(d.requested_risk,.01*before_balance,atol=.011)
            journal=gzip.decompress((out/f'journal-attempt{a}.txt.gz').read_bytes()).decode()
            assert 'testing with execution delay 150 milliseconds' in journal
            assert 'demo=1' in journal and 'Exness-MT5Trial16' in journal and 'symbol=BTCUSD' in journal
            assert not re.search('position closed due end of test|initialization failed|critical error|access violation|array out of range|not enough history',journal,re.I)
            start=pd.Timestamp(r['start'].replace('.','-'),tz='UTC');end=pd.Timestamp(r['end'].replace('.','-'),tz='UTC')
            assert int(r['inputs']['InpTradeFrom'])==int(start.timestamp())
            assert (d.open_epoch>=start.timestamp()).all() and (d.close_epoch<end.timestamp()).all()
            eligible=(times>=start)&(times<end)&(times.hour>=7)&(times.hour<=16)
            days=len(set(times[eligible].date));months=(end-start).days/30.4375
            curve=np.r_[10000,10000+np.cumsum(p)];peak=np.maximum.accumulate(curve);w,l=streaks(p)
            m.update(trades_per_month=len(d)/months,trades_per_eligible_day=len(d)/days,eligible_days=days,
                win_streak=w,loss_streak=l,balance_dd_pct=float(100*np.max((peak-curve)/peak)),
                median_initial_risk_pct=float(np.median(d.actual_risk/before_balance*100)),
                max_initial_risk_pct=float(np.max(d.actual_risk/before_balance*100)),
                max_hold_hours=float(((d.close_epoch-d.open_epoch)/3600).max()))
            checked=0
            for sig in signals.itertuples():
                i=bars.index.get_indexer([int(sig.signal_time)])[0];assert i>=399,'Missing signal warmup'
                v=oracle.oracle(bars.iloc[i-399:i+1],1)
                assert v['side']==sig.raw_side and np.isclose(v['atr'],sig.atr,rtol=1e-8,atol=1e-8)
                expected=1 if oracle.hash32(int(sig.fill_time)//86400+290929)&1 else -1
                assert sig.actual_side==(expected if control else sig.raw_side)
                assert 3600<=sig.fill_time-sig.signal_time<3901
                checked+=1
            verified.append(dict(tag=tag,signals=checked,fresh=fresh))
            late_count=0
            for t in d.itertuples():
                deadline=min(int(t.open_epoch)+6*3600,int(t.open_epoch)//86400*86400+20*3600)
                if t.close_epoch<=deadline+120 and t.close_epoch//86400==t.open_epoch//86400:continue
                left=trace[trace.time<deadline];right=trace[trace.time>=deadline]
                assert len(left) and len(right)
                before=left.iloc[-1];after=right.iloc[0];late_count+=1
                carries.append(dict(tag=tag,position_id=int(t.position_id),open_utc=stamp(t.open_epoch),close_utc=stamp(t.close_epoch),
                    hours_held=(t.close_epoch-t.open_epoch)/3600,deadline_utc=stamp(deadline),
                    trace_before=stamp(before.time),trace_after=stamp(after.time),trace_gap_hours=(after.time-before.time)/3600,
                    close_minus_first_trace_seconds=int(t.close_epoch-after.time),net_profit=t.net_profit,swap=t.swap,
                    crossed_utc_date=bool(t.close_epoch//86400>t.open_epoch//86400)))
            r['flags']['late_timed_exits']=late_count
            dated=d.copy();dated['month']=pd.to_datetime(dated.close_epoch,unit='s',utc=True).dt.strftime('%Y-%m')
            monthly=dated.groupby('month').agg(trades=('net_profit','size'),net_profit=('net_profit','sum')).reset_index().to_dict('records')
            r.update(evidence_root=str(out),fresh_run=fresh,metrics=m,monthly_closed_pnl=monthly,
                costs={k:float(d[k].sum()) for k in ['gross_profit','commission','swap','fee','net_profit']})
            results.append(r);ledgers[tag]=d
            for f in [out/'run.json',report,out/'trades.csv.gz',out/'signals.csv.gz',out/'trace.csv.gz',out/f'journal-attempt{a}.txt.gz']:
                evidence[str(f)]=sha(f)
    matched=[];failures=[]
    for r in results:
        if r['control']:continue
        c=next(x for x in results if x['tag']==r['tag'].replace('-raw-','-control-'))
        a,b=ledgers[r['tag']].copy(),ledgers[c['tag']].copy()
        a['date']=a.open_epoch//86400;b['date']=b.open_epoch//86400
        pair=a.merge(b,on='date',suffixes=('_raw','_control'),validate='1:1')
        dates_matched=len(pair)==len(a)==len(b)
        delta=pair.net_profit_raw/pair.actual_risk_raw-pair.net_profit_control/pair.actual_risk_control
        matched.append(dict(raw_tag=r['tag'],matched_trades=len(pair),all_dates_matched=dates_matched,
            raw_only_dates=sorted(set(a.date)-set(b.date)),control_only_dates=sorted(set(b.date)-set(a.date)),
            max_entry_seconds=float(abs(pair.open_epoch_raw-pair.open_epoch_control).max()),mean_net_R_delta=float(delta.mean())))
        if r['window'] in ['3y','5y'] and r['model']==4:
            m=r['metrics'];label=r['window']
            if m['net_profit']<=0:failures.append(label+': net profit <=0')
            if m['profit_factor']<1.15:failures.append(label+': PF below1.15')
            if m['trades']<30:failures.append(label+': fewer than30 positions')
            if m['mean_net_R']<=c['metrics']['mean_net_R']:failures.append(label+': mean net R does not beat control')
            if not dates_matched:failures.append(label+': control opportunities differ')
            if any(r['flags'].values()):failures.append(label+': unresolved raw execution/carry flags')
            if any(c['flags'].values()):failures.append(label+': unresolved control execution/carry flags')
    recent=next(r for r in results if r['window']=='1y' and r['model']==4 and not r['control'])
    if recent['metrics']['net_profit']<=0:failures.append('1y: nonpositive result excludes current shortlist')
    save('RESULTS.json',dict(runs=results,matched_controls=matched))
    save('CARRYOVER_AUDIT.json',dict(positions=carries,note='Deadlines are6h/20UTC; broker session rule may require an earlier exit. Trace gaps do not establish the exact historical cause or live fill availability. Overlapping periods repeat positions.'))
    save('GATE.json',dict(status='RAW_GATE_REJECTED' if failures else 'RAW_GATE_PASSED',failures=failures,
        fresh_native_runs=4,reused_native_runs=8,parameter_variants_tested=0,optimization_run=False,
        monte_carlo_run=False,production_changed=False,gold_changed=False,nasdaq_changed=False))
    save('VERIFICATION.json',dict(passed=True,runs=verified,signal_checks=sum(x['signals'] for x in verified),
        fresh_signal_checks=sum(x['signals'] for x in verified if x['fresh']),source_h1_sha256=sha(SOURCE/'data/BTCUSD-H1.csv.gz'),
        independent_oracle_sha256=sha(SOURCE/'verify_signals.py'),evidence=evidence,
        note='Executed-signal and evidence-integrity pass, not strategy acceptance or exhaustive tick replay of all possible signals.'))
    print(json.dumps(dict(failures=failures,signal_checks=sum(x['signals'] for x in verified),
        fresh=[dict(tag=r['tag'],metrics=r['metrics'],flags=r['flags']) for r in results if r['fresh_run']]),indent=2))

if __name__=='__main__':main()
