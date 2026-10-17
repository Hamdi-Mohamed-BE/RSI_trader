"""Offline audited native shared-account summaries; never adds standalone returns."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
import csv, gzip, hashlib, importlib.util, json, math, re, statistics
R=Path(__file__).resolve().parent;B=R.parent;INITIAL=10000.0;PRAGUE=ZoneInfo('Europe/Prague')
spec=importlib.util.spec_from_file_location('prior_offline_metrics',B/'Top10 EA Two Month Backtest 2026-10-16/analyze.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def rows(p):
    with Path(p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def iso(epoch):return datetime.fromtimestamp(epoch,timezone.utc).isoformat()
def deal_cash(d):return sum(float(d[k]) for k in ('gross','commission','swap','fee'))
def group_positions(deals):
    grouped=defaultdict(list);seen=set()
    for d in deals:
        assert int(d['deal']) not in seen;seen.add(int(d['deal']));grouped[int(d['position_id'])].append(d)
    trades=[]
    for pid,items in grouped.items():
        items.sort(key=lambda d:(int(d['time_msc']),int(d['deal'])))
        opened=[d for d in items if int(d['entry'])==0];closed=[d for d in items if int(d['entry'])==1]
        assert len(opened)==1 and closed and len(opened)+len(closed)==len(items),('Unsupported position accounting',pid)
        a=opened[0];z=closed[-1];volume=float(a['volume']);assert abs(volume-sum(float(d['volume']) for d in closed))<1e-7
        assert all(int(d['type'])!=int(a['type']) for d in closed)
        costs={k:round(sum(float(d[k]) for d in items),8) for k in ('gross','commission','swap','fee')}
        trades.append(dict(position_id=pid,open_epoch=int(a['time_msc'])/1000,close_epoch=int(z['time_msc'])/1000,
            open_time=iso(int(a['time_msc'])/1000),close_time=iso(int(z['time_msc'])/1000),date=iso(int(z['time_msc'])/1000)[:10],
            open_prague=datetime.fromtimestamp(int(a['time_msc'])/1000,PRAGUE).isoformat(),close_prague=datetime.fromtimestamp(int(z['time_msc'])/1000,PRAGUE).isoformat(),
            symbol=a['symbol'],side='Long' if int(a['type'])==0 else 'Short',volume=volume,open_price=float(a['price']),close_price=sum(float(d['price'])*float(d['volume']) for d in closed)/volume,
            magic=int(a['magic']),sl=float(a['sl']),tp=float(a['tp']),entry_comment=a['comment'],exit_comments=[d['comment'] for d in closed],exit_legs=len(closed),partial=len(closed)>1,
            end_of_test_liquidation=any('end of test' in d['comment'].lower() for d in closed),net=round(sum(costs.values()),8),**costs))
    trades.sort(key=lambda t:(t['close_epoch'],t['position_id']))
    assert abs(sum(t['net'] for t in trades)-sum(deal_cash(d) for d in deals))<1e-6
    return trades
def cash_metrics(deals,start,end):
    balance=peak=INITIAL;dd=ddpct=0;daily_cash=defaultdict(float);flows=defaultdict(list)
    curve=[dict(time=start+'T00:00:00+00:00',balance=INITIAL)]
    for d in sorted(deals,key=lambda d:(int(d['time_msc']),int(d['deal']))):
        value=deal_cash(d);balance+=value;peak=max(peak,balance);dd=max(dd,peak-balance);ddpct=max(ddpct,100*(peak-balance)/peak)
        date=iso(int(d['time_msc'])/1000)[:10];daily_cash[date]+=value;flows[date].append(value)
        curve.append(dict(time=iso(int(d['time_msc'])/1000),balance=round(balance,8),deal_ticket=int(d['deal'])))
    begin=datetime.fromisoformat(start).replace(tzinfo=timezone.utc);finish=datetime.fromisoformat(end).replace(tzinfo=timezone.utc);day=begin;b=INITIAL;daily=[];returns=[]
    while day<finish:
        date=day.date().isoformat();opening=b;value=daily_cash[date];b+=value
        running=high=opening;daydd=0
        for flow in flows[date]:running+=flow;high=max(high,running);daydd=max(daydd,high-running)
        rate=value/opening if opening>0 else None
        if rate is not None:returns.append(rate)
        daily.append(dict(date=date,opening_balance=round(opening,8),ending_balance=round(b,8),net_profit=round(value,8),return_pct=100*rate if rate is not None else None,max_closed_drawdown_cash=round(daydd,8)))
        day+=timedelta(days=1)
    assert abs(b-balance)<1e-6
    sharpe=math.sqrt(365)*statistics.mean(returns)/statistics.stdev(returns) if len(returns)>1 and statistics.stdev(returns)>0 else None
    return dict(final_balance=round(balance,8),max_closed_drawdown_cash=dd,max_closed_drawdown_pct=ddpct,max_daily_closed_drawdown_cash=max((d['max_closed_drawdown_cash'] for d in daily),default=0),closed_balance_daily_sharpe=sharpe,sharpe_days=len(returns),sharpe_annualization=365),daily,curve
def scenario(result,cfg):
    manifest=result['manifest'];tag=manifest['tag'];folder=R/'native'/tag;deals=rows(folder/'deals.csv');trades=group_positions(deals)
    metrics=old.position_metrics(trades);cash,daily,curve=cash_metrics(deals,manifest['start'],manifest['end_exclusive']);metrics.update(cash)
    metrics.update(native_equity_drawdown_pct=result['native']['equity_dd_pct'],native_balance_drawdown_pct=result['native']['balance_dd_pct'],native_mt5_sharpe=result['native'].get('sharpe_ratio'),native_report_profit_factor=result['native'].get('profit_factor'))
    assert abs(metrics['net_profit']-result['native']['net_profit'])<.031
    assert abs(metrics['final_balance']-INITIAL-metrics['net_profit'])<.031
    entry_day_count=len({t['open_prague'][:10] for t in trades})
    metrics.update(average_positions_per_calendar_day=len(trades)/len(daily) if daily else None,filled_entry_days_prague=entry_day_count,average_positions_per_active_entry_day=len(trades)/entry_day_count if entry_day_count else None,days_with_position_closes=len({t['date'] for t in trades}),natural_close_subset=old.position_metrics([t for t in trades if not t['end_of_test_liquidation']]),forced_boundary_positions=sum(t['end_of_test_liquidation'] for t in trades))
    for day in daily:
        daytrades=[t for t in trades if t['date']==day['date']];day.update(positions_closed=len(daytrades),whole_position_pnl_at_final_close=sum(t['net'] for t in daytrades))
    monthly=[]
    for month in dict.fromkeys(d['date'][:7] for d in daily):
        ds=[d for d in daily if d['date'].startswith(month)];ts=[t for t in trades if t['date'].startswith(month)]
        monthmetrics=old.position_metrics(ts);monthmetrics['whole_position_return_pct_of_initial']=monthmetrics.pop('return_pct')
        monthly.append(dict(month=month,**monthmetrics,cash_net_profit=round(sum(d['net_profit'] for d in ds),8),cash_return_pct=100*(ds[-1]['ending_balance']/ds[0]['opening_balance']-1)))
    contributions=[]
    for row in cfg['entries']:
        magic=int(row['inputs']['InpMagic']);ts=[t for t in trades if t['magic']==magic and t['symbol']==row['symbol']]
        effective_inputs=dict(row['input_settings']);name=row['label']
        if row['key']=='N5':
            effective_inputs['InpRequireDIAgreement']=str(manifest['case']['di']).lower()
            name='Nasdaq 5M Momentum — DI '+('ON' if manifest['case']['di'] else 'OFF')
        contributions.append(dict(id=row['slug'],name=name,symbol=row['symbol'],magic=magic,metrics=old.position_metrics(ts),trades=ts,inputs=effective_inputs))
    assert sum(c['metrics']['trades'] for c in contributions)==len(trades)
    assert abs(sum(c['metrics']['net_profit'] for c in contributions)-metrics['net_profit'])<1e-6
    status=None;prague=[];risk=None
    if not manifest['case'].get('direct'):
        raw=rows(folder/'status.csv')[0];status={k:(float(v) if '.' in v else int(v)) for k,v in raw.items()}
        status['label']={0:'Not passed within test window',1:'Natural phase target passed',-1:'Failed maximum daily loss',-2:'Failed maximum loss',-3:'Invalid: ledger unavailable'}[status['status']]
        status['status_time_utc']=iso(status['status_epoch']) if status['status_epoch'] else None
        status['status_time_prague']=datetime.fromtimestamp(status['status_epoch'],PRAGUE).isoformat() if status['status_epoch'] else None
        status['first_captured_native_snapshot_utc']=iso(status['first_observed'])
        status['last_captured_native_snapshot_utc']=iso(status['last_observed'])
        entries=[int(d['epoch']) for d in deals if int(d['entry'])==0]
        status['calendar_days_from_first_entry_to_terminal_event']=(datetime.fromtimestamp(status['status_epoch'],PRAGUE).date()-datetime.fromtimestamp(min(entries),PRAGUE).date()).days+1 if entries and status['status_epoch'] else None
        status['calendar_days_from_test_start_to_terminal_event']=(datetime.fromtimestamp(status['status_epoch'],PRAGUE).date()-datetime.fromisoformat(manifest['start']).date()).days+1 if status['status_epoch'] else None
        status['pass_probability']=None;status['median_pass_days']=None
        eventrows=rows(folder/'events.csv');status['terminal_events']=[e for e in eventrows if e['kind'] in ('natural_phase_pass','permanent_phase_failure','ledger_failure')]
        status['observed_entry_days_full_window']=status['entry_days']
        status['terminal_entry_days']=int(status['terminal_events'][0]['entry_days']) if status['terminal_events'] else None
        if status['terminal_events']:
            terminal=status['terminal_events'][0]
            status.update(positions_open_at_terminal=int(terminal['positions']),orders_open_at_terminal=int(terminal['orders']),completed_positions_by_terminal_second=sum(int(t['close_epoch'])<=status['status_epoch'] for t in trades),entries_by_terminal_second=sum(int(t['open_epoch'])<=status['status_epoch'] for t in trades),floating_at_terminal=status['status_equity']-status['status_balance'])
        if manifest['case']['challenge'] and status['status']<0:
            last_close=max((t['close_epoch'] for t in trades),default=status['status_epoch'])
            journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
            market_lines=[line for line in journal.splitlines() if '\tCore 01\t' in line and 'failed market' in line.lower() and 'market closed' in line.lower()]
            times=[]
            for line in market_lines:
                match=re.search(r'Core 01\t(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})',line)
                if match:times.append(datetime.strptime(match[1],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).isoformat())
            status['liquidation']=dict(last_position_close_utc=iso(last_close),lag_seconds_after_second_resolution_breach=max(0,last_close-status['status_epoch']),post_failure_entry_count=sum(int(d['entry'])==0 and int(d['epoch'])>status['status_epoch'] for d in deals),market_closed_log_mentions=sum('market closed' in line.lower() for line in journal.splitlines()),failed_market_close_attempts_core01=len(market_lines),first_market_closed_utc=min(times) if times else None,last_market_closed_utc=max(times) if times else None,warning='Close requests were retried after an already observed breach. Market closure/gaps mean neither the loss floor nor immediate liquidation is guaranteed.')
        cash_by_prague=defaultdict(float);entry_prague=set()
        for d in deals:
            date=datetime.fromtimestamp(int(d['epoch']),PRAGUE).date().isoformat();cash_by_prague[date]+=deal_cash(d)
            if int(d['entry'])==0:entry_prague.add(date)
        for d in rows(folder/'days.csv'):
            key=d['prague_day'];date=key[:4]+'-'+key[4:6]+'-'+key[6:8]
            item={k:float(v) for k,v in d.items() if k!='prague_day'}
            item.update(date=date,cash_net_profit=round(cash_by_prague[date],8),entry_day=date in entry_prague,observed_daily_breach=float(d['minimum_observed_equity'])<float(d['daily_equity_floor'])-1e-7)
            prague.append(item)
        metrics['max_daily_equity_loss_observed_cash']=max((d['max_equity_loss_from_day_start'] for d in prague),default=None)
        metrics['max_daily_equity_loss_observed_pct_of_initial']=metrics['max_daily_equity_loss_observed_cash']/INITIAL*100 if prague else None
        metrics['max_daily_equity_peak_to_trough_observed_cash']=max((d['equity_peak_to_trough'] for d in prague),default=None)
        admissions=rows(folder/'admissions.csv');accepted=[a for a in admissions if a['decision']=='admitted'];rejected=[a for a in admissions if a['decision']!='admitted']
        contracts=rows(folder/'contracts.csv');sizes={c['symbol']:float(c['contract_size']) for c in contracts}
        contract_by_symbol={c['symbol']:c for c in contracts};matched_admissions=set()
        for trade in trades:
            trade['initial_filled_stop_risk_cash']=abs(trade['open_price']-trade['sl'])*trade['volume']*sizes[trade['symbol']]
            candidates=[(i,a) for i,a in enumerate(accepted) if i not in matched_admissions and int(a['magic'])==trade['magic'] and a['symbol']==trade['symbol'] and abs(float(a['lots'])-trade['volume'])<1e-8 and 0<=trade['open_epoch']-int(a['epoch'])<=3]
            assert len(candidates)==1,('Admission/fill matching',tag,trade['position_id'],candidates)
            index,admission=candidates[0];matched_admissions.add(index);budget=float(admission['nominal_budget']);request_equity=budget*100
            unit_distance=abs(float(admission['requested_entry'])-float(admission['sl']))*sizes[trade['symbol']]
            raw_lots=budget/unit_distance if unit_distance else None
            trade.update(request_equity=request_equity,planned_stop_risk_cash=float(admission['planned_stop_risk']),planned_stop_risk_pct_of_request_equity=100*float(admission['planned_stop_risk'])/request_equity,filled_stop_risk_pct_of_request_equity=100*trade['initial_filled_stop_risk_cash']/request_equity,requested_entry_price=float(admission['requested_entry']),fill_minus_requested_entry=trade['open_price']-float(admission['requested_entry']),unrounded_risk_lots=raw_lots,lot_rounding_cause='broker minimum lot' if raw_lots is not None and raw_lots<float(contract_by_symbol[trade['symbol']]['volume_min'])-1e-9 else 'ceil to broker lot step' if raw_lots is not None and trade['volume']>raw_lots+1e-9 else 'none')
        risk=dict(nominal_dynamic_percent=1,actual_planned_stop_cash_min=min((float(a['planned_stop_risk']) for a in accepted),default=None),actual_planned_stop_cash_max=max((float(a['planned_stop_risk']) for a in accepted),default=None),planned_risk_over_nominal_budget=max((float(a['planned_stop_risk'])/float(a['nominal_budget']) for a in accepted if float(a['nominal_budget'])>0),default=None),initial_filled_stop_risk_cash_min=min((t['initial_filled_stop_risk_cash'] for t in trades),default=None),initial_filled_stop_risk_cash_max=max((t['initial_filled_stop_risk_cash'] for t in trades),default=None),largest_planned_risk_trade=max(trades,key=lambda t:t['planned_stop_risk_pct_of_request_equity']) if trades else None,largest_filled_risk_trade=max(trades,key=lambda t:t['filled_stop_risk_pct_of_request_equity']) if trades else None,admission_attempts=len(admissions),admitted=len(accepted),rejected=len(rejected),reject_reasons={reason:sum(a['decision']==reason for a in rejected) for reason in sorted({a['decision'] for a in rejected})},entry_request_zero_spread_count=sum(float(a['ask'])==float(a['bid']) for a in accepted),admissions=admissions,contracts=contracts,max_observed_gross_margin15=status['max_margin15'],stop_risk_note='Stop-distance cash excludes commission, swap, fees and further gap/slippage. Percent denominator is equity at entry request, not a separately exported post-fill equity snapshot.')
    trace=rows(folder/'equity.csv');quality=dict(history_quality=result['native'].get('history_quality'),tick_notes=result['tick_notes'],warnings=result['warnings'],first_captured_snapshot_utc=iso(int(trace[0]['epoch'])) if trace else None,last_captured_snapshot_utc=iso(int(trace[-1]['epoch'])) if trace else None,native_seconds=result['seconds'],report_sha256=result['report_sha256'],binary_sha256=manifest['binary_sha256'],cash_reconciled=True,secondary_dispatch='USTEC primary ticks plus1secondtimer; sampled latest secondary quotes, not every secondary tick')
    return dict(id=tag,label=tag,metrics=metrics,status=status,risk=risk,quality=quality,contributions=contributions,monthly=monthly,daily=daily,daily_prague=prague,trades=trades,curve=curve,manifest=manifest)
def parity(scenarios):
    a=next(s for s in scenarios if s['id']=='N5-alone')['trades'];b=next(s for s in scenarios if s['id']=='N5-direct-parity')['trades']
    fields=['open_epoch','close_epoch','symbol','side','volume','open_price','close_price','sl','tp','gross','commission','swap','fee','net','exit_legs','entry_comment','exit_comments']
    differences=[]
    if len(a)!=len(b):differences.append(dict(field='position_count',adapter=len(a),direct=len(b)))
    for i,(x,y) in enumerate(zip(a,b)):
        for key in fields:
            if x[key]!=y[key]:differences.append(dict(position_index=i,field=key,adapter=x[key],direct=y[key]))
    return dict(passed=not differences,adapter_positions=len(a),direct_positions=len(b),fields=fields,differences=differences,meaning='Exact current-source mechanical input freeze, no complete productionEX5parity certification. Direct source excludes the shared margin admission wrapper; parity only meaningful if no risk-margin rejections.')
def main():
    cfg=read(R/'CONFIG.json');runs=read(R/'RUNS.json');scenarios=[scenario(r,cfg) for r in runs]
    by={s['id']:s for s in scenarios};full=by['noDI-shared-diagnostic'];control=by['DIon-shared-control'];challenge=by['noDI-challenge']
    output=dict(meta=dict(title='FTMO Swing: Nasdaq5M noDI + RSI VWAP Gold + EMA3',start=cfg['start'],end_exclusive=cfg['end_exclusive'],initial_balance=10000,currency='USD',risk_percent_per_entry=1,native_simultaneous_portfolio=True,not_summed_standalone=True,model=4,delay_ms=150,native_leverage=15,source_compiled=True,production_or_live_changes=False,phase2_handover=read(R/'PHASE2-HANDOVER.json') if (R/'PHASE2-HANDOVER.json').exists() else None),rules=cfg['account_policy'],scenarios=scenarios,baseline=full,control=control,challenge=challenge,verification=by.get('noDI-verification'),controls=[s for s in scenarios if s['manifest']['case']['index']>0],parity=parity(scenarios),comparison=dict(return_percentage_point_difference_noDI_minus_DI=full['metrics']['return_pct']-control['metrics']['return_pct'],net_cash_difference=full['metrics']['net_profit']-control['metrics']['net_profit']),limitations=read(R/'PLAN.json')['limitations'],provenance=dict(frozen_sha256=sha(R/'FROZEN.json'),build_sha256=sha(R/'BUILD.json'),runs_sha256=sha(R/'RUNS.json'),analyzer_sha256=sha(Path(__file__)),source_plan_sha256=sha(R/'PLAN.json')))
    save(R/'SUMMARY.json',output)
    print(json.dumps(dict(scenarios=[dict(id=s['id'],metrics=s['metrics'],status=s['status'],risk_rejections=s['risk']['reject_reasons'] if s['risk'] else None) for s in scenarios],parity=output['parity'],summary_sha256=sha(R/'SUMMARY.json')),indent=2))
if __name__=='__main__':main()
