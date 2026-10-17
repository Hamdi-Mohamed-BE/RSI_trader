"""Offline fixed-protocol whole-position ranking of fresh native MT5 results."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import csv, gzip, hashlib, json, math, re, statistics

ROOT=Path(__file__).resolve().parent
INITIAL=10000.0

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def iso(epoch):return datetime.fromtimestamp(epoch,timezone.utc).isoformat()

def position_metrics(trades):
    values=[t['net'] for t in trades]
    wins=[v for v in values if v>0];losses=[v for v in values if v<0]
    high=running=dd=0.0;wr=lr=mw=ml=0
    for value in values:
        running+=value;high=max(high,running);dd=max(dd,high-running)
        wr=wr+1 if value>0 else 0;lr=lr+1 if value<0 else 0;mw=max(mw,wr);ml=max(ml,lr)
    return dict(trades=len(values),positions=len(values),exit_fills=sum(t['exit_legs'] for t in trades),wins=len(wins),losses=len(losses),breakeven=len(values)-len(wins)-len(losses),
        net_profit=round(sum(values),8),net_pnl=round(sum(values),8),return_pct=round(sum(values)/INITIAL*100,8),profit_factor=sum(wins)/-sum(losses) if losses else None,
        profit_factor_status='finite' if losses else 'no_losing_positions' if wins else 'no_trades_or_no_gain_loss',
        win_rate_pct=100*len(wins)/len(values) if values else None,gross_profit=sum(wins),gross_loss=-sum(losses),
        max_win_streak=mw,max_loss_streak=ml,avg_win=sum(wins)/len(wins) if wins else None,avg_loss=sum(losses)/len(losses) if losses else None,
        avg_trade=sum(values)/len(values) if values else None,payoff_ratio=(sum(wins)/len(wins))/(-sum(losses)/len(losses)) if wins and losses else None,
        largest_win=max(wins) if wins else None,largest_loss=min(losses) if losses else None,
        mean_hold_minutes=sum((t['close_epoch']-t['open_epoch'])/60 for t in trades)/len(trades) if trades else None,
        position_recognition_drawdown_cash=dd,partial_positions=sum(t['partial'] for t in trades),
        commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),fee=sum(t['fee'] for t in trades))

def account_cash_metrics(deals,start,end):
    begin=datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    finish=datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    cash=sorted(deals,key=lambda d:(int(d.get('time_msc') or int(d['epoch'])*1000),int(d['deal'])))
    balance=peak=INITIAL;dd=ddpct=0;daily_cash=defaultdict(float);daily_flows=defaultdict(list);curve=[dict(time=begin.isoformat(),balance=INITIAL)]
    for d in cash:
        epoch=int(d.get('time_msc') or int(d['epoch'])*1000)/1000
        value=sum(float(d[k]) for k in ('gross','commission','swap','fee'))
        balance+=value;peak=max(peak,balance);dd=max(dd,peak-balance);ddpct=max(ddpct,100*(peak-balance)/peak)
        daily_cash[iso(epoch)[:10]]+=value
        daily_flows[iso(epoch)[:10]].append(value)
        curve.append(dict(time=iso(epoch),balance=round(balance,8),deal_ticket=int(d['deal'])))
    daily=[];b=INITIAL;returns=[];day=begin
    while day<finish:
        opening=b;value=daily_cash[day.date().isoformat()];b+=value
        day_balance=day_peak=opening;day_dd=day_dd_pct=0.0
        for flow in daily_flows[day.date().isoformat()]:
            day_balance+=flow;day_peak=max(day_peak,day_balance)
            day_dd=max(day_dd,day_peak-day_balance)
            if day_peak>0:day_dd_pct=max(day_dd_pct,100*(day_peak-day_balance)/day_peak)
        rate=value/opening if opening>0 else None
        if rate is not None:returns.append(rate)
        daily.append(dict(date=day.date().isoformat(),net_profit=round(value,8),opening_balance=round(opening,8),ending_balance=round(b,8),return_pct=100*rate if rate is not None else None,max_closed_drawdown_cash=day_dd,max_closed_drawdown_pct=day_dd_pct))
        day+=timedelta(days=1)
    sharpe=math.sqrt(365)*statistics.mean(returns)/statistics.stdev(returns) if len(returns)>1 and statistics.stdev(returns)>0 else None
    assert len(daily)==61 and abs(b-balance)<1e-6
    return dict(max_closed_drawdown_cash=dd,max_closed_drawdown_pct=ddpct,max_daily_closed_drawdown_cash=max(d['max_closed_drawdown_cash'] for d in daily),max_daily_closed_drawdown_pct=max(d['max_closed_drawdown_pct'] for d in daily),closed_balance_daily_sharpe=sharpe,closed_balance_sharpe_days=len(returns),closed_balance_sharpe_annualization=365,final_balance=balance),daily,curve

def build_member(row,result,start,end):
    path=ROOT/'native'/result['tag']
    with (path/'deals.csv').open(encoding='utf-8-sig') as stream:deals=list(csv.DictReader(stream))
    cashmetrics,daily,curve=account_cash_metrics(deals,start,end)
    position_deals=defaultdict(list)
    for deal in deals:position_deals[int(deal['position_id'])].append(deal)
    trades=[]
    for trade in result['trades']:
        forced=any('end of test' in comment.lower() for comment in trade['exit_comments'])
        raw=position_deals[trade['position_id']]
        opened=min(int(d['time_msc']) for d in raw if int(d['entry'])==0)
        closed=max(int(d['time_msc']) for d in raw if int(d['entry'])==1)
        trades.append(dict(trade,open_time=iso(opened/1000),close_time=iso(closed/1000),open_epoch_msc=opened,close_epoch_msc=closed,date=iso(closed/1000)[:10],end_of_test_liquidation=forced))
    trades.sort(key=lambda t:(t['close_epoch_msc'],t['position_id']))
    metrics=position_metrics(trades)
    metrics.update(average_positions_per_calendar_day=len(trades)/61,days_with_position_closes=len({t['date'] for t in trades}))
    metrics.update(cashmetrics,native_equity_drawdown_pct=result['native']['equity_dd_pct'],native_balance_drawdown_pct=result['native']['balance_dd_pct'],native_mt5_sharpe=result['native'].get('sharpe_ratio'),native_report_profit_factor=result['native'].get('profit_factor'))
    assert abs(metrics['net_profit']-result['native']['net_profit'])<.031
    assert abs(metrics['final_balance']-INITIAL-metrics['net_profit'])<.031
    natural=[t for t in trades if not t['end_of_test_liquidation']]
    months=[]
    for month in dict.fromkeys(d['date'][:7] for d in daily):
        ds=[d for d in daily if d['date'].startswith(month)]
        ts=[t for t in trades if t['date'].startswith(month)]
        monthly=position_metrics(ts)
        monthly['position_return_pct_of_original_capital']=monthly.pop('return_pct')
        months.append(dict(month=month,**monthly,cash_net_profit=sum(d['net_profit'] for d in ds),cash_return_pct=100*(ds[-1]['ending_balance']/ds[0]['opening_balance']-1) if ds[0]['opening_balance'] else None))
    inputs=result['inputs']
    rr={k:v for k,v in inputs.items() if any(token in k.lower() for token in ('rewardrisk','targetr','usetakeprofit','tp','trail','breakeven'))}
    filters={k:v for k,v in inputs.items() if 'DI' in k or any(token in k.lower() for token in ('adx','markov'))}
    quality=dict(history_quality=result['native']['history_quality'],tick_notes=result.get('tick_notes',[]),flags=result['flags'],calendar_audit=result.get('calendar_audit'),
        boundary_position_count=len(trades)-len(natural),sample_label='No trades' if not trades else 'Tiny sample: fewer than 10 positions' if len(trades)<10 else 'Small sample: fewer than 30 positions' if len(trades)<30 else 'Short two-month sample',
        native_seconds=result['seconds'],native_cash_reconciled=True,report_sha256=result['report_sha256'],binary_sha256=result['binary_sha256'])
    with (path/'equity.csv').open(encoding='utf-8-sig') as stream:trace=list(csv.DictReader(stream))
    observed=[int(d['epoch']) for d in trace]
    quality.update(first_captured_native_snapshot_utc=iso(min(observed)) if observed else None,last_captured_native_snapshot_utc=iso(max(observed)) if observed else None,
        actual_first_quote_not_exported=True,cutoff_note='Read-only equity snapshots record native TimeCurrent; first captured snapshot is not certified as the first history quote. Last snapshot is the last observed native test time, not the last trade.',
        last_observation_on_final_calendar_day=bool(observed and iso(max(observed))[:10]=='2026-10-15'))
    journal=gzip.decompress((path/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
    data_messages=[line.strip() for line in journal.splitlines() if re.search(r'real ticks absent|ticks discarded|no real ticks|generated ticks',line,re.I)]
    quality.update(reported_tick_fallback_or_discard_messages=sorted(set(data_messages)),reported_tick_fallback_or_discard_message_count=len(data_messages),
        native_tick_generation_summaries=sorted(set(re.findall(r'[^\r\n]*\d+ ticks, \d+ bars generated[^\r\n]*',journal))),
        tick_authenticity_note='Native reported history quality and logged fallback/discard messages are disclosed; these are not an independent certification of historical execution or slippage.')
    return dict(id=row['slug'],slug=row['slug'],name=row['label'],symbol=row['symbol'],timeframe=row['period'],status='tested' if trades else 'zero_trades',metrics=metrics,
        natural_close_only_metrics=position_metrics(natural),rules=dict(rr=rr,filters=filters,current_inputs=inputs,safe_by_design=row['safe_by_design'],dynamic_by_design=row['dynamic_by_design']),
        sizing=dict(selected_dynamic_risk_percent=row['selected_risk_percent'],news_per_order=row['news'],adaptive_portfolio_controls=False,
            historical_loss_reference_only=row['historical_loss_sizing'],historical_loss_points=inputs.get('InpHistoricalLossPoints'),
            allocation_note='1% per module trade; simultaneous modules can exceed 1% total exposure.' if row['slug']=='3-way-gold' else 'Single pending breakout entry at the full selected 1% per entry; not a pair of half-risk OCO orders.' if row['slug']=='xau-weakness' else '0.10% per pending side/order; both sides can fill in one event, approximately 0.20% combined before gaps/costs/rounding.' if row['news'] else 'Selected risk is per independently managed entry, not a portfolio-wide daily or aggregate exposure limit.',
            note='No stop: 1% balance budget relative to frozen historical worst loss; not a guaranteed future loss cap.' if row['historical_loss_sizing'] else 'Native 1% equity-risk input (news 0.10% per order); original broker lot rounding, split-order/module allocations, costs and gaps retained. Not a guaranteed loss cap.'),
        quality=quality,monthly=months,daily=daily,closed_balance_curve=curve,trades=trades,source_path=row['source'],preset_path=row['preset'])

def main():
    plan=read(ROOT/'PLAN.json');state=read(ROOT/'RUN_STATUS.json');frozen=read(ROOT/'FROZEN.json')
    assert all(sha(p)==v for p,v in frozen['files'].items())
    assert not state['failed'] and len(state['complete'])+len(state['missing'])==37,'Native batch is incomplete'
    news_risk_path=ROOT/'NEWS-RISK-RECEIPTS.json'
    news_risk=read(news_risk_path)
    assert news_risk['harness_no_hidden_risk_override_verified']
    rows=[]
    for row in plan['cases']:
        slug=row['slug']
        if slug in state['missing']:
            rows.append(dict(id=slug,slug=slug,name=row['label'],symbol=row['symbol'],timeframe=row['period'],status='unavailable',reason=state['missing'][slug],rank=None))
            continue
        receipt=state['complete'][slug]
        assert sha(receipt['path'])==receipt['sha256']
        result=read(receipt['path']);assert result['current_active_input_verification']
        member=build_member(row,result,plan['start'],plan['end_exclusive'])
        if row['news']:
            diagnosis=news_risk['by_slug'][slug]
            assert abs(diagnosis['summary']['net_profit']-member['metrics']['net_profit'])<.000001
            member['rules']['news_event_parameters']=news_risk['event_parameters'][slug]
            member['sizing']['news_order_risk_receipts']=diagnosis
            member['sizing']['news_risk_caveats']=news_risk['caveats']
            by_position={receipt['position_id']:receipt for receipt in diagnosis['orders']}
            assert set(by_position)=={t['position_id'] for t in member['trades']}
            for trade in member['trades']:
                trade['news_order_risk_receipt']=by_position[trade['position_id']]
        rows.append(member)
    ranking=sorted([r for r in rows if r['status']=='tested'],key=lambda r:(-r['metrics']['return_pct'],r['id']))
    for number,row in enumerate(ranking,1):row['rank']=number
    for row in rows:row.setdefault('rank',None)
    summary=dict(schema_version=1,meta=dict(window=dict(start=plan['start'],end_exclusive=plan['end_exclusive'],completed_days=61,through='2026-10-15',timezone='UTC tester timestamp convention'),
        initial_balance=INITIAL,normal_dynamic_risk_percent=1,news_dynamic_risk_percent_per_order=.10,standalone_native=True,shared_portfolio=False,optimization=False,
        equal_return_tie_break='Deterministic ascending strategy ID, consistent with the frozen return-only ranking.',
        source='Fresh isolated Exness native MT5 backtests only; no connected-account journal data.',rank_basis=plan['primary_ranking'],
        coverage=dict(roster=37,reproducible=len(state['complete']),unavailable=len(state['missing']),ranked=len(ranking),zero_trade=sum(r['status']=='zero_trades' for r in rows)),
        frozen_before_results=True,live_changes=False,prepared_at_utc=plan['prepared_at_utc'],generated_at_utc=datetime.now(timezone.utc).isoformat()),
        top10=ranking[:10],all_eas=rows,ranking=[dict(id=r['id'],rank=r['rank'],name=r['name'],symbol=r['symbol'],metrics=r['metrics']) for r in ranking],
        missing=[r for r in rows if r['status']=='unavailable'],zero_trade=[dict(id=r['id'],name=r['name']) for r in rows if r['status']=='zero_trades'],
        limitations=[
            'Top ten selected retrospectively from this same short two-month window; not optimized rules, untouched OOS, or proof of future performance. All tested candidates are disclosed.',
            'Each EA has its own fresh $10,000 simulated balance with native dynamic sizing. These are not additive portfolio returns or a simultaneous shared-margin account.',
            'Native ending return includes explicitly flagged end-of-test liquidations. Natural-close-only metrics are a secondary subset and must not replace total marked-to-market performance.',
            'Whole-position statistics combine native partial exits and include opening/closing commissions, swaps and fees. Native MT5 PF/Sharpe are retained separately and can have different definitions.',
            'Closed-balance daily Sharpe uses actual native deal cash, all 61 completed calendar days including zero-cash days, sqrt(365), and zero risk-free rate. Two months is not a stable Sharpe estimate.',
            'Maximum native equity DD is report-derived tick-path floating-equity drawdown; cash drawdown/Sharpe use the actual native closed-cash ledger. No offline fractional-lot rescaling is used.',
            'Current Full recommended strategy/DI/Safe/dynamic-exit defaults are retained. Only dynamic risk is standardized and portfolio adaptive multipliers disabled for standalone comparisons.',
            'The tester executes freshly compiled, read-only-instrumented copies of the frozen current MQ5 source. Archived production EX5 hashes prove unchanged provenance, not bit-identical execution or source-to-existing-EX5 parity; a stale production binary is not independently ruled out.',
            'Hourly profiles have no stop-loss. Their 1% input sizes against a fixed historical-loss reference, not a maximum possible future loss.',
            'News Pulse uses an official receipted five-event schedule, not a point-in-time calendar vintage. Stops, offsets and fallback execution remain current production rules. Gold News V9 cannot be reproduced without its pre-release prediction archive.',
            'The 0.10% news setting is a nominal sizing input, not a realized-loss or filled-stop-risk ceiling. Effective event-specific distances supersede generic SET values. Broker upward rounding and news entry gaps increased stop exposure; the worst observed filled/planned ratio was 10.6 times on XAG. Exact placement equity was not exported, so no exact per-order equity-budget certification is claimed.',
            'Dates are native completed-day boundaries under the saved UTC tester timestamp convention, not the earlier Lagos account-journal snapshot. No live account, BAT, production source or website changes are made.'
        ],news_risk_diagnostics=dict(source_path=str(news_risk_path),source_sha256=sha(news_risk_path),caveats=news_risk['caveats']),provenance=dict(plan_sha256=sha(ROOT/'PLAN.json'),freeze_sha256=sha(ROOT/'FROZEN.json'),run_status_sha256=sha(ROOT/'RUN_STATUS.json'),analyzer_sha256=sha(Path(__file__)),news_risk_receipts_sha256=sha(news_risk_path)))
    save(ROOT/'SUMMARY.json',summary)
    print(json.dumps(dict(meta=summary['meta'],top10=[dict(rank=r['rank'],name=r['name'],metrics=r['metrics']) for r in summary['top10']]),indent=2))

if __name__=='__main__':main()
