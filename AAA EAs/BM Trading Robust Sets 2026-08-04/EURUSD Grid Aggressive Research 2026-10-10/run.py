"""Finite high-risk native grid experiment; selection excludes the latest two years."""
from pathlib import Path
import importlib.util, math, msvcrt, shutil, traceback

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
RAW=BASE/'EURUSD EMA Volume Grid Raw 2026-10-10'
spec=importlib.util.spec_from_file_location('grid_raw_core',RAW/'run.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
n=c.n;c.ROOT=ROOT;n.R=ROOT
CURRENT=None

def case(cid,family,stage,inputs,start,end):
    source=ROOT/'EURUSD Grid Aggressive Research.mq5' if family=='guarded' else RAW/'EURUSD EMA Volume Grid Raw.mq5'
    slug='gridhr-'+cid+'-'+stage
    return dict(slug=slug,candidate=cid,family=family,stage=stage,start=start,end=end,window=stage,
        symbol='EURUSD',period='M5',label=cid,source=str(source),expert=str(source.with_suffix('.ex5')),
        input_settings={**inputs,'InpGridAuditTag':slug},candidate_overrides={},production_hashes={str(source):n.sha(source)})

def plan():
    common=dict(InpSignalTF='5',InpEMAPeriod='5',InpMagicBase='261010000',InpBasketTargetUSD='10.0')
    candidates=[];cases=[]
    for risk in [5,10]:
        for spacing in [100,300]:
            for reward in [.25,.5,1.0]:
                cid=f'cap-r{risk}-g{spacing}-tp{reward:g}'
                inputs={**common,'InpStartingLot':str(.1*risk/5),'InpLotIncrement':'0','InpGridPoints':str(spacing),
                    'InpAlternateAfterBasket':'false','InpMaxOrders':'5','InpBasketLossPercent':str(risk),
                    'InpBasketTargetR':str(reward),'InpScaleLotsWithBalance':'true','InpMaxAgeHours':'72'}
                candidates.append(dict(id=cid,family='guarded',inputs=inputs))
                cases.append(case(cid,'guarded','dev',inputs,'2020.10.10','2024.10.10'))
    for scale in [5,10,20]:
        cid=f'raw-{scale}x'
        inputs={**common,'InpStartingLot':str(.01*scale),'InpLotIncrement':str(.01*scale),
            'InpGridPoints':'300','InpBasketTargetUSD':str(10*scale),'InpAlternateAfterBasket':'true'}
        candidates.append(dict(id=cid,family='scaled',inputs=inputs))
        for stage,start in [('1y','2025.10.10'),('3y','2023.10.10')]:
            cases.append(case(cid,'scaled',stage,inputs,start,'2026.10.10'))
    p=dict(candidates=candidates,initial_cases=cases,deposit=10000,leverage='1:2000',model=4,delay_ms=150,
        selection_gate=dict(min_baskets=30,min_pf=1.05,positive_return=True,max_equity_dd=70,zero_stopout=True),
        ranking='Highest compounded equivalent monthly growth, then basket PF, then lower equity DD; development data only.',
        selected_count=3,validation=[dict(stage='validation2y',start='2024.10.10',end='2026.10.10'),
            dict(stage='validation1y',start='2025.10.10',end='2026.10.10')],
        source_hashes={str(ROOT/'EURUSD Grid Aggressive Research.mq5'):n.sha(ROOT/'EURUSD Grid Aggressive Research.mq5'),
            str(RAW/'EURUSD EMA Volume Grid Raw.mq5'):n.sha(RAW/'EURUSD EMA Volume Grid Raw.mq5')},
        protocol_sha256=n.sha(ROOT/'PROTOCOL.txt'),recent_data_untouched=False,no_live_changes=True)
    path=ROOT/'PLAN.json'
    if path.exists():assert n.read(path)==p,'Frozen experiment changed'
    else:n.save(path,p)
    return p

def monthly_metrics(trace,window,net):
    start=n.pd.Timestamp(window[0].replace('.','-'),tz='UTC');end=n.pd.Timestamp(window[1].replace('.','-'),tz='UTC')
    s=n.pd.Series([float(x['equity']) for x in trace],index=n.pd.to_datetime([int(x['epoch']) for x in trace],unit='s',utc=True)).sort_index()
    s=s[~s.index.duplicated(keep='last')]
    prior=10000;records=[];cursor=start.replace(day=1,hour=0,minute=0,second=0)
    while cursor<end:
        nxt=cursor+n.pd.DateOffset(months=1);cut=min(nxt,end)
        readings=s[(s.index>=start)&(s.index<cut)]
        eq=float(readings.iloc[-1]) if len(readings) else prior
        if cut==end:eq=10000+net
        value=100*(eq/prior-1) if prior>0 else None
        complete=cursor>=start and nxt<=end
        records.append(dict(month=cursor.strftime('%Y-%m'),equity_start=prior,equity_end=eq,return_pct=value,full_month=complete))
        prior=eq;cursor=nxt
    full=[x['return_pct'] for x in records if x['full_month'] and x['return_pct'] is not None]
    days=(end-start).days;final=10000+net
    return dict(monthly=records,full_months=len(full),average_monthly_pct=sum(full)/len(full) if full else None,
        median_monthly_pct=float(n.np.median(full)) if full else None,months_10pct=sum(x>=10 for x in full),
        positive_months=sum(x>0 for x in full),worst_month_pct=min(full) if full else None,best_month_pct=max(full) if full else None,
        compounded_equivalent_monthly_pct=100*((final/10000)**(365.25/(12*days))-1) if final>0 else None,
        capital_depleted=final<=0,
        min_sampled_equity=float(s.min()),monthly_basis='Calendar-month floating equity; boundary partial months excluded from averages/frequency.')

def verify(result,out,deals):
    row=CURRENT;settings=row['input_settings'];signals=n.export_rows(out/'signals.csv');bydeal={int(d['deal']):d for d in deals}
    assert len(signals)==len(result['trades'])
    groups={};last_sides={}
    for s in signals:
        idx=int(s['order_index']);bid=int(s['basket']);direction=int(s['side']);scale=float(s.get('lot_scale') or 1)
        assert int(s['signal_start'])+300==int(s['signal_close'])<=int(s['epoch'])
        assert int(s['v_old'])<int(s['v_mid'])<int(s['v_new'])
        assert (float(s['close'])>float(s['ema'])) if direction>0 else (float(s['close'])<float(s['ema']))
        expected=(float(settings['InpStartingLot'])+float(settings['InpLotIncrement'])*(idx-1))*scale
        expected=math.floor((expected+1e-10)/.01)*.01
        assert abs(float(s['lots'])-expected)<1e-7,(s,expected)
        if idx>1:assert float(s['nearest_points'])>=int(settings['InpGridPoints'])-1e-4
        d=bydeal[int(s['deal'])]
        assert int(d['magic'])==int(s['magic'])==261010000+bid and int(d['entry'])==0
        assert int(d['type'])==(0 if direction>0 else 1)
        assert abs(float(d['price'])-float(s['fill_price']))<1e-7
        groups.setdefault(bid,[]).append(s);last_sides[bid]=direction
        if row['family']=='guarded':
            assert idx<=5
            assert abs(float(s['target_usd'])-float(s['budget_usd'])*float(settings['InpBasketTargetR']))<=.011
    for ss in groups.values():assert [int(s['order_index']) for s in ss]==list(range(1,len(ss)+1))
    assert all(t['sl']==0 and t['tp']==0 for t in result['trades'])
    baskets=c.basket_groups(result['trades'],deals)
    if row['family']=='guarded':
        path=c.CUSTOM/(row['slug']+'-baskets.csv');assert path.is_file()
        assert path.stat().st_mtime>=n.read(out/'owned-process.json')['started']-2
        shutil.copy2(path,out/'baskets.csv');events={int(x['basket']):x for x in n.export_rows(out/'baskets.csv')}
        for b in baskets:
            e=events.get(b['id'])
            if e:
                assert abs(float(e['net'])-b['net'])<=.031
                b['reason']=e['reason'];b['budget_usd']=float(e['budget_usd']);b['target_usd']=float(e['target_usd'])
                b['budget_overshoot_usd']=max(0,-b['net']-b['budget_usd']) if b['reason']=='LOSS_BUDGET' else 0
                assert abs(b['budget_usd']-float(e['start_balance'])*float(settings['InpBasketLossPercent'])/100)<=.011
            else:assert b['terminal'] or b['stopout'],('Unclassified basket',b)
    for a,b in zip(baskets,baskets[1:]):
        assert a['close_epoch']<=b['open_epoch']
        if settings['InpAlternateAfterBasket']=='true':assert a['side']!=b['side']
    net=round(sum(b['net'] for b in baskets),2);assert abs(net-result['native']['net_profit'])<.031
    trace=n.export_rows(out/'trace.csv');v={x['metric']:float(x['value']) for x in n.export_rows(out/'stats.csv')}
    assert v['digits']==5 and abs(v['point']-.00001)<1e-10 and v['grid_points']==int(settings['InpGridPoints'])
    if row['family']=='guarded':assert v['max_positions']<=5
    s=monthly_metrics(trace,result['window'],net)
    start=n.pd.Timestamp(result['window'][0].replace('.','-'),tz='UTC');end=n.pd.Timestamp(result['window'][1].replace('.','-'),tz='UTC')
    seq=n.pd.Series([float(x['equity']) for x in trace],index=n.pd.to_datetime([int(x['epoch']) for x in trace],unit='s',utc=True))
    daily=seq.resample('D').last().reindex(n.pd.date_range(start,end-n.pd.Timedelta(days=1),freq='D')).ffill().fillna(10000);daily.iloc[-1]=10000+net
    prev=n.pd.concat([n.pd.Series([10000],index=[start-n.pd.Timedelta(days=1)]),daily]).shift(1).reindex(daily.index)
    changes=(daily/prev-1).where(prev>0).dropna()
    sharpe=math.sqrt(365)*changes.mean()/changes.std(ddof=1) if len(changes)>2 and changes.std(ddof=1)>0 else None
    terminal=[b for b in baskets if b['terminal']]
    s.update(net_profit=net,return_pct=net/100,final_balance=10000+net,orders=len(result['trades']),
        baskets=c.stats([b['net'] for b in baskets]),positions=c.stats([t['net'] for t in result['trades']]),
        stopout_baskets=sum(b['stopout'] for b in baskets),stopout_deals=int(v['stopout_deals']),
        equity_dd_pct=max(v['max_equity_dd_pct'],result['native']['equity_dd_pct']),equity_dd_usd=max(v['max_equity_dd_usd'],result['native']['equity_dd_usd']),
        max_positions=int(v['max_positions']),max_lots=v['max_lots'],max_margin=v['max_margin_usd'],max_daily_equity_dd_usd=v['max_daily_equity_dd_usd'],
        sharpe_calendar_daily_equity=sharpe,test_end_net=sum(b['net'] for b in terminal),terminal_baskets=len(terminal),
        basket_loss_exits=sum(b['reason']=='LOSS_BUDGET' for b in baskets),max_age_exits=sum(b['reason']=='MAX_AGE' for b in baskets),
        max_budget_overshoot_usd=max([b.get('budget_overshoot_usd',0) for b in baskets],default=0))
    result.update(summary=s,baskets=baskets,instrumentation=v,signal_audit_verified=True,candidate=row['candidate'],family=row['family'],stage=row['stage'])

def run_case(row):
    global CURRENT
    CURRENT=row;n.END=row['end'];n.START=row['start']
    binary,build=n.build(row);return c.run_case(row,binary,build)

def passes(m):
    return m['baskets']['count']>=30 and m['return_pct']>0 and (m['baskets']['pf'] or 0)>=1.05 and m['stopout_deals']==0 and m['equity_dd_pct']<=70

def selection(p,state):
    dev=[n.read(Path(state['complete'][row['slug']]['path'])) for row in p['initial_cases'] if row['stage']=='dev']
    def key(q):
        m=q['summary'];return (passes(m),m['compounded_equivalent_monthly_pct'],m['baskets']['pf'] or 0,-m['equity_dd_pct'])
    ranked=sorted(dev,key=key,reverse=True);selected=[dict(id=q['candidate'],passes_development_gate=passes(q['summary']),development_summary=q['summary']) for q in ranked[:3]]
    value=dict(selection_data_only=['2020.10.10','2024.10.10'],selected=selected,ranked=[dict(id=q['candidate'],passes=passes(q['summary'])) for q in ranked],
        prior_recent_history_seen=True,no_recent_results_used_for_selection=True)
    path=ROOT/'SELECTION.json'
    if path.exists():assert n.read(path)==n.safe(value),'Selection changed after validation'
    else:n.save(path,value)
    return value

def main():
    c.verify=verify;shutil.copy2(c.PRIOR/'ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh');p=plan()
    status=ROOT/'RUN_STATUS.json';state=n.read(status) if status.exists() else dict(complete={},failed={},initial_total=18,validation_total=6,no_live_changes=True)
    def batch(rows):
        for row in rows:
            if row['slug'] in state['complete']:continue
            try:
                result=run_case(row);path=ROOT/'native'/result['tag']/'results.json'
                state['complete'][row['slug']]=dict(path=str(path),candidate=row['candidate'],stage=row['stage'],summary=result['summary'])
                state['failed'].pop(row['slug'],None)
                m=result['summary'];print('MONTHLY '+row['slug']+' mean='+str(m['average_monthly_pct'])+' median='+str(m['median_monthly_pct'])+' targetMonths='+str(m['months_10pct'])+'/'+str(m['full_months']),flush=True)
            except Exception as e:
                state['failed'][row['slug']]=dict(error=str(e),trace=traceback.format_exc()[-6000:]);print('FAILED '+row['slug']+' '+str(e),flush=True)
            n.save(status,state);print('PROGRESS '+str(len(state['complete']))+'/24; failed='+str(len(state['failed'])),flush=True)
    # Development results are frozen before ANY selected candidate sees recent dates.
    batch([row for row in p['initial_cases'] if row['stage']=='dev'])
    if any(row['slug'] not in state['complete'] for row in p['initial_cases'] if row['stage']=='dev'):
        raise RuntimeError('Development audit incomplete; no selection or validation performed')
    chosen=selection(p,state);validate=[]
    mapping={x['id']:x for x in p['candidates']}
    for choice in chosen['selected']:
        candidate=mapping[choice['id']]
        for w in p['validation']:validate.append(case(candidate['id'],'guarded',w['stage'],candidate['inputs'],w['start'],w['end']))
    n.save(ROOT/'VALIDATION_PLAN.json',validate)
    batch(validate)
    batch([row for row in p['initial_cases'] if row['stage']!='dev'])
    results=[n.read(Path(v['path'])) for v in state['complete'].values()]
    n.save(ROOT/'SUMMARY.json',dict(plan=p,selection=chosen,results=results,completed=len(results),failed=state['failed'],no_live_changes=True))
    assert not state['failed'] and len(results)==24,state['failed']
    assert all(n.sha(Path(k))==v for k,v in p['source_hashes'].items())
    n.save(ROOT/'VERIFICATION.json',dict(completed=24,all_source_hashes_unchanged=True,native_cash_reconciled=True,
        signals_and_grid_depth_and_lots_verified=True,basket_loss_overshoot_disclosed=True,no_validation_retuning=True,
        source_code_tester_only=True,no_live_changes=True,not_untouched_oos=True))
    print('ALL HIGH-RISK GRID CASES FINISHED; no live changes',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);n.available();main()
