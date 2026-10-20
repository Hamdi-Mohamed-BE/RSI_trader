"""Independent comparison audit; imports independent verifiers, not replay engines.

The packaged Top5 account is reconstructed here without Prop Ready guards.
The other twelve cases reuse the separately written independent risk ledger.
Only VERIFICATION.json is written; no terminal or account is accessed.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter,defaultdict
from bisect import bisect_left
from zoneinfo import ZoneInfo
import csv
import importlib.util
import json
import math
import statistics

ROOT=Path(__file__).resolve().parent
ORIGINAL=ROOT.parent/'Prop Ready 1K Risk Replay 2026-10-17'
ACTUAL=ORIGINAL/'Actual5Percent'
SPEC=importlib.util.spec_from_file_location('independent_actual5_verifier',ACTUAL/'independent_verify.py')
prior=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)
source=prior.source
load,digest,require,close=source.load,source.digest,source.require,source.close
UTC=timezone.utc
TZ=ZoneInfo('Europe/Prague')


def reconstructed_owned_marks(trades,trace,begin,end):
    """Never turn post-liquidation cash into pre-liquidation floating equity."""
    ordered=sorted(trades,key=lambda p:(p['open_epoch'],p['position_id']))
    opens=[p['open_epoch'] for p in ordered]
    boundaries={p[key] for p in ordered for key in ('open_epoch','close_epoch')}
    marks=defaultdict(list)
    discarded=Counter()
    previous=None
    for point in trace:
        phase=point.get('phase')
        require(phase in (None,'','market_sample','finish_after_native_liquidation'),
                'Unknown native sampling phase','phase_causality')
        if phase not in (None,'','market_sample'):
            discarded['post_liquidation_snapshot']+=1
            continue
        stamp=int(point['epoch'])
        if not begin<=stamp<end:continue
        require(previous is None or stamp>=previous,'Native mark timestamp regression','captured_marks')
        if stamp==previous:
            discarded['duplicate_market_sample']+=1
            continue
        previous=stamp
        if stamp in boundaries:
            discarded['position_boundary']+=1
            continue
        index=bisect_left(opens,stamp)-1
        if index>=0 and opens[index]<stamp<ordered[index]['close_epoch']:
            trade=ordered[index]
            swap=float(point['open_swap'])/trade['volume'] if point.get('open_swap') else None
            floating=(float(point['equity'])-float(point['balance']))/trade['volume']
            require(math.isfinite(floating),'Finite owned native floating','captured_marks')
            marks[trade['position_id']].append((stamp,floating,swap))
        else:
            require(abs(float(point['equity'])-float(point['balance']))<.021,
                    'Unowned nonzero market floating equity','captured_marks')
            discarded['flat_market_sample']+=1
    return marks,dict(discarded)


def verify_owned_native_marks(data,native,begin,end):
    diagnostics=[]
    for case in native['cases']:
        path=Path(case['path'])
        trades=load(path)['trades']
        with (path.parent/'equity.csv').open(encoding='utf-8-sig',newline='') as file:
            trace=list(csv.DictReader(file))
        marks,discarded=reconstructed_owned_marks(trades,trace,begin,end)
        for q in (p for p in data['candidates'] if p['ea']==case['slug']):
            expected=marks[q['position_id']]
            require(len(q['marks'])==len(expected),'Owned source mark count after phase filtering','captured_marks')
            for actual,point in zip(q['marks'],expected):
                require(actual[0]==point[0],'Owned source sample timestamp','captured_marks')
                close(actual[1],point[1],'Owned source floating per lot','captured_marks')
                numeric(actual[2],point[2],'Owned source swap per lot','captured_marks')
        diagnostics.append(dict(ea=case['slug'],export_revision=load(path).get('observational_export_revision',1),
            captured_owned_marks=sum(len(v) for v in marks.values()),discarded=discarded))
    return diagnostics


def verify_export_only_revision():
    """Prove the V3 repair is exactly four observational exporter changes."""
    folder=ROOT/'native'
    plan=load(folder/'EXPORT V3 PLAN.json')
    freeze=load(folder/'EXPORT V3 FREEZE.json')
    require(freeze['frozen_before_remaining_reruns'] and freeze['observational_export_only']
            and freeze['unchanged_trading_protocol'],'V3 protocol freeze declarations','native_export_revision')
    require(plan['strategy_parameters_dates_sizing_timers_unchanged'] and plan['no_source_reselection']
            and plan['no_synthetic_closing_deals'] is True and not plan['live_changes'],
            'V3 has no rule, risk, timer, date or live change','native_export_revision')
    for path,expected in freeze['files'].items():
        require(digest(path)==expected,'V3 immutable observational repair evidence','native_export_revision')
    old=(folder/'ReadOnlyAuditBase.mqh').read_text(encoding='utf-8-sig').replace('\r\n','\n')
    new=(folder/'ReadOnlyAuditBaseV3.mqh').read_text(encoding='utf-8-sig').replace('\r\n','\n')
    edits={
        'FileWrite(rr05_equity_file,"epoch","balance","equity");':'FileWrite(rr05_equity_file,"epoch","balance","equity","phase");',
        'FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));':'FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),"market_sample");',
        'FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));':'FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),"finish_after_native_liquidation");',
        '!HistorySelect(0,TimeCurrent())':'!HistorySelect(0,TimeCurrent()+86400)',
    }
    expected=old
    for before,after in edits.items():
        require(expected.count(before)==1,'Unique old observational export statement','native_export_revision')
        expected=expected.replace(before,after)
    require(expected==new,'Exactly four read-only exporter edits; no trading code delta','native_export_revision')
    before=(folder/'ReadOnlyAudit.mqh').read_text(encoding='utf-8-sig').replace('\r\n','\n')
    after=(folder/'ReadOnlyAuditV3.mqh').read_text(encoding='utf-8-sig').replace('\r\n','\n')
    nonblank=lambda text:'\n'.join(line for line in text.splitlines() if line.strip())
    require(nonblank(before.replace('ReadOnlyAuditBase.mqh','ReadOnlyAuditBaseV3.mqh'))==nonblank(after),
            'Read-only wrapper switches only the observational include, ignoring blank-line serialization','native_export_revision')


def numeric(actual,expected,label,category='client_numeric'):
    if expected is None:
        require(actual is None,label,category)
    elif isinstance(expected,(str,bool)):
        require(actual==expected,(label,actual,expected),category)
    else:
        close(actual,expected,label,category)


def verify_top5_sources(data,native,native_plan,manifest):
    require(native['source_server']=='Exness-MT5Trial16','Explicit Top5 fallback feed','top5_sources')
    require(len(native['cases'])==5,'Five native Top5 cases','top5_sources')
    require(native_plan['start']=='2026-08-17' and native_plan['end_exclusive']=='2026-10-17','Exact native date range','top5_sources')
    require(native_plan['portfolio_result'] is False and native_plan['optimization'] is False,'Unoptimized standalone native source','top5_sources')
    planned={x['slug']:x for x in native_plan['cases']}
    delivered={x['slug']:x for x in manifest['entries']}
    require(set(planned)==set(delivered)=={x['slug'] for x in native['cases']},'Package/native membership','top5_sources')
    require(len({q['id'] for q in data['candidates']})==len(data['candidates']),'Unique Top5 fill IDs','top5_sources')
    verified=0
    for case in native['cases']:
        path=Path(case['path'])
        plan=planned[case['slug']]
        require(plan['public_ex5_sha256']==delivered[case['slug']]['ex5_sha256'],'Frozen source/public fingerprint','top5_sources')
        require(plan['inputs']==delivered[case['slug']]['inputs'],'Frozen source/public inputs','top5_sources')
        for file,expected in plan['production_hashes'].items():
            require(digest(file)==expected,'Copied production graph hash','top5_sources')
        require(digest(path)==case['sha256'],'Native completion hash','top5_sources')
        saved=load(path)
        build_path=Path(saved.get('build_receipt_path',ROOT/'native/builds'/case['slug']/'build.json'))
        build=load(build_path)
        require(build['callback_only_copy_verified'] and build['strategy_and_ClientGuard_graph_unchanged']
                and build['tester_only'] and build['compile']=='0 errors, 0 warnings',
                'Native strategy/risk/source graph unchanged under observational instrumentation','top5_sources')
        require(build['binary_sha256']==saved['binary_sha256']==digest(build_path.parent/'Audit.ex5'),
                'Native instrumented binary fingerprint','top5_sources')
        require(digest(build_path)==saved['build_receipt_sha256'],'Native instrumentation receipt fingerprint','top5_sources')
        native_trades={t['position_id']:t for t in saved['trades']}
        receipts=list(csv.DictReader((path.parent/'entry_risk.csv').open(encoding='utf-8-sig')))
        by_id={int(x['position_id']):x for x in receipts}
        require(len(by_id)==len(receipts),'Unique Top5 risk receipts','top5_sources')
        deals=defaultdict(list)
        for d in csv.DictReader((path.parent/'deals.csv').open(encoding='utf-8-sig')):
            deals[int(d['position_id'])].append(d)
        candidates=[q for q in data['candidates'] if q['ea']==case['slug']]
        require(len(candidates)==len(native_trades),'Every native fill retained','top5_sources')
        for q in candidates:
            verified+=1
            t=native_trades[q['position_id']]
            receipt=by_id[q['position_id']]
            require(q['unit_risk_method']=='native_actual_fill_OrderCalcProfit','Native unit risk method','top5_sources')
            require(receipt['calculation_ok']=='1' and receipt['margin_ok']=='1' and receipt['sl_source']=='entry_order','Native risk receipt valid','top5_sources')
            for key,field in (('unit_risk','unit_risk'),('receipt_margin_one_lot','margin_one_lot'),('open_price','entry_price'),('sl','sl')):
                close(q[key],float(receipt[field]),('Top5 receipt',q['id'],key),'top5_sources')
            require(abs(q['op']-int(receipt['epoch']))<=1,'Fill receipt timing','top5_sources')
            require(q['op']==t['open_epoch'] and not t['partial'],'Exact source fill ownership','top5_sources')
            censored=any('end of test' in c.lower() for c in t['exit_comments'])
            require(q['end_censored']==censored and (q['cl'] is None)==censored,'Artificial test-end exit censored','top5_sources')
            opened=[d for d in deals[q['position_id']] if int(d['entry'])==0]
            require(len(opened)==1,'One source position entry','top5_sources')
            entry=sum(float(opened[0][k]) for k in ('gross','commission','swap','fee'))/t['volume']
            close(q['entry_unit_cost'],entry,'Top5 entry fee isolation','top5_sources')
            close(q['unit_gross']*t['volume'],t['gross'],'Top5 native gross','top5_sources')
            close(q['unit_commission']*t['volume'],t['commission']+t['fee'],'Top5 native costs','top5_sources')
            close(q['unit_swap']*t['volume'],t['swap'],'Top5 native swap','top5_sources')
    require(verified==len(data['candidates']),'All Top5 candidates verified','top5_sources')
    require(delivered['nasdaq-5m-candle-momentum']['inputs']['InpRequireDIAgreement']=='false','Current Top5 Nasdaq DI OFF','top5_sources')


def client_audit(record,data,plan,broker):
    begin,end=(int(datetime.fromisoformat(x).timestamp()) for x in plan['window_utc'])
    initial=float(plan['initial_balance'])
    scenario,stress=record['scenario'],record['stress']
    priority={ea:n for n,ea in enumerate(plan['portfolios']['top5'])}
    events=[]
    for q in data['candidates']:
        events.append((q['op'],3,priority[q['ea']],q['id'],q,None))
        if q['cl'] is not None and q['cl']<end:
            events.append((q['cl'],4 if q['cl']==q['op'] else 1,priority[q['ea']],q['id'],q,None))
        events.extend((m[0],2,priority[q['ea']],q['id'],q,m) for m in q['marks'])
    date=datetime.fromtimestamp(begin,TZ).date()
    while True:
        stamp=int(datetime.combine(date,datetime.min.time(),tzinfo=TZ).timestamp())
        if stamp>=end:break
        if stamp>=begin:events.append((stamp,0,-1,'',None,None))
        date+=timedelta(days=1)
    events.sort(key=lambda e:e[:4])
    active,trades,flows,curve={},[],[],[]
    per_ea=defaultdict(Counter)
    counts,quality=Counter(),Counter()
    cash=equity=initial
    max_age=max_initial_lag=0
    exhaustion=min_margin_level=None
    decisions=iter(record['decisions'])
    detailed=[]

    def observe(stamp):
        nonlocal equity,max_age,max_initial_lag,exhaustion,min_margin_level
        equity=cash+sum(p['volume']*p['floating'] for p in active.values())
        for p in active.values():
            if p['mark_epoch'] is None:
                quality['initial_zero_observations']+=1
                max_initial_lag=max(max_initial_lag,max(0,stamp-p['op']))
            else:
                age=max(0,stamp-p['mark_epoch'])
                max_age=max(max_age,age)
                quality['stale_over_900s_observations']+=age>900
        if equity<=0 and exhaustion is None:exhaustion=stamp
        margin=sum(p['margin'] for p in active.values())
        if margin>0:
            level=100*equity/margin
            min_margin_level=level if min_margin_level is None else min(level,min_margin_level)
        curve.append(dict(epoch=stamp,balance=cash,equity=equity))

    def spread(q,entering):
        spec=broker['symbols'][q['symbol']]
        price=q['open_price'] if entering else q['close_price']
        return spec['quote_spread']*spec['trade_contract_size']/(price if q['symbol']=='USDJPY' else 1.)

    for stamp,kind,_,_,q,mark in events:
        if not begin<=stamp<end:continue
        if kind==0:observe(stamp)
        elif kind==2:
            if q['id'] not in active:continue
            require(q['op']<mark[0]<=stamp and (q['cl'] is None or mark[0]<q['cl']),'Client owned past-only mark','client_causality')
            p=active[q['id']]
            if p['mark_epoch'] is None:max_initial_lag=max(max_initial_lag,mark[0]-q['op'])
            p.update(floating=mark[1],swap=mark[2] if mark[2] is not None else 0.,mark_epoch=mark[0])
            quality['owned_marks']+=1
            quality['missing_open_swap_marks']+=mark[2] is None
            observe(stamp)
        elif kind in (1,4):
            if q['id'] not in active:continue
            require(q['cl']==stamp and not q['end_censored'],'Client real source close only','client_censoring')
            observe(stamp)
            p=active.pop(q['id'])
            swap=q['unit_swap']*(2 if stress and q['unit_swap']<0 else 1)
            exit_cash=round((q['unit_gross']+q['unit_commission']+swap-q['entry_unit_cost']-(spread(q,False) if stress else 0.))*p['volume'],2)
            cash=round(cash+exit_cash,2)
            net=round(p['entry_cash']+exit_cash,2)
            trades.append(dict(id=q['id'],ea=q['ea'],symbol=q['symbol'],op=q['op'],cl=stamp,
                side=q['side'],open_price=q['open_price'],close_price=q['close_price'],sl=q['sl'],tp=q['tp'],
                lots=p['volume'],risk=p['risk'],entry_cash=p['entry_cash'],exit_cash=exit_cash,net=net,
                balance=cash,gross=q['unit_gross']*p['volume'],commission=q['unit_commission']*p['volume'],swap=swap*p['volume']))
            counts['closed']+=1
            per_ea[q['ea']]['closed']+=1
            observe(stamp)
            flows.append(dict(epoch=stamp,cash=exit_cash,id=q['id'],kind='exit'))
        else:
            observe(stamp)
            spec=broker['symbols'][q['symbol']]
            budget=scenario['value'] if scenario['mode']=='fixed' else cash*scenario['value']/100.
            step,unit=spec['volume_step'],q['unit_risk']
            if cash>0 and math.isfinite(cash) and unit>0 and math.isfinite(unit) and budget>0:
                floored=round(min(math.floor((budget/unit+1e-10)/step)*step,spec['volume_max']),8)
                override=floored<spec['volume_min']
                volume=spec['volume_min'] if override else floored
            else:volume,budget,override=0.,0.,False
            risk=unit*volume
            margin=q['receipt_margin_one_lot']*volume
            used=sum(p['margin'] for p in active.values())
            if exhaustion is not None or equity<=0:reason='capital_exhaustion_unresolved'
            elif any(p['ea']==q['ea'] for p in active.values()):reason='same_ea_exposure'
            elif volume<=0:reason='invalid_budget'
            elif margin>equity-used:reason='margin_proxy'
            else:reason='opened'
            expected=dict(id=q['id'],ea=q['ea'],epoch=stamp,equity=equity,balance=cash,
                budget=budget,source_volume_ceiling=None,volume=volume,stop_risk=risk,
                minimum_lot_risk=spec['volume_min']*unit,minimum_lot_override=override,
                stop_risk_pct_equity=100*risk/equity if equity>0 else None,reason=reason)
            actual=next(decisions)
            for key,value in expected.items():numeric(actual[key],value,('Client decision',q['id'],key),'client_decisions')
            detailed.append(expected)
            counts[reason]+=1
            per_ea[q['ea']]['candidates']+=1
            per_ea[q['ea']][reason]+=1
            if reason!='opened':continue
            require(risk<=budget+1e-7 or override,'Client risk overshoot only at disclosed minimum','client_guards')
            require(spec['volume_min']<=volume<=spec['volume_max'],'Client broker volume bounds','client_guards')
            require(margin<=equity-used,'Client free-margin admission','client_guards')
            entry_cash=round((q['entry_unit_cost']-(spread(q,True) if stress else 0.))*volume,2)
            cash=round(cash+entry_cash,2)
            flows.append(dict(epoch=stamp,cash=entry_cash,id=q['id'],kind='entry'))
            active[q['id']]=dict(volume=volume,risk=risk,margin=margin,entry_cash=entry_cash,
                floating=0.,swap=0.,mark_epoch=None,ea=q['ea'],symbol=q['symbol'],op=q['op'])
            observe(stamp)
    observe(end-1)
    require(next(decisions,None) is None,'All client decisions audited','client_decisions')
    require(len(detailed)==len(data['candidates']),'Client candidate coverage','client_decisions')
    require(len(trades)==len(record['trades']),'Client closed-position count','client_cash')
    for actual,expected in zip(record['trades'],trades):
        for key,value in expected.items():numeric(actual[key],value,('Client trade',expected['id'],key),'client_cash')
    require(record['cash_flows']==flows,'Client actual entry/exit cash ledger','client_cash')
    require(record['metrics']['counts']==dict(counts),'Client reason totals','client_counts')
    require(record['per_ea']=={k:dict(v) for k,v in per_ea.items()},'Client EA totals','client_counts')
    require(len(record['curve'])==len(curve),'Client curve length','client_curve')
    for expected,actual in zip(curve,record['curve']):
        for key,value in expected.items():numeric(actual[key],value,('Client curve',key),'client_curve')
    quality.update(maximum_past_mark_age_seconds=max_age,maximum_initial_zero_segment_seconds=max_initial_lag)
    require(record['mark_quality']==dict(quality),'Client mark quality and staleness','client_causality')
    require(len(record['open_positions'])==len(active),'Client censored position count','client_censoring')
    for actual in record['open_positions']:
        p=active[actual['id']]
        for key,value in dict(ea=p['ea'],symbol=p['symbol'],op=p['op'],lots=p['volume'],
            initial_risk=p['risk'],paid_entry_cash=p['entry_cash'],mark_epoch=p['mark_epoch'],
            mark_unit=p['floating'],sampled_floating=p['floating']*p['volume']).items():
            numeric(actual[key],value,('Client censored position',key),'client_censoring')
    expected_metrics=source.metrics([t['net'] for t in trades])
    expected_metrics.update(ending_balance=cash,ending_sampled_equity=equity,
        return_pct=100*(cash/initial-1),ending_equity_return_pct=100*(equity/initial-1),
        cash_profit=round(cash-initial,2),unrealized_sampled_profit=equity-cash,
        open_positions=len(active),hard_loss_latch=False,first_breach_epoch=None,
        capital_exhaustion_epoch=exhaustion,minimum_sampled_margin_level=min_margin_level,
        min_lot_override_entries=sum(x['reason']=='opened' and x['minimum_lot_override'] for x in detailed),
        broker_stopout_reconstructed=False,historical_path_executable_uncertainty=exhaustion is not None,
        average_trades_per_calendar_day=len(trades)/61.,average_trades_per_weekday=len(trades)/45.)
    for key,value in expected_metrics.items():numeric(record['metrics'][key],value,key,'client_metrics')
    require(record['metrics']['paused_days']==[],'No invented client daily loss pauses','client_metrics')
    close(cash,round(initial+sum(t['net'] for t in trades)+sum(p['entry_cash'] for p in active.values()),2),'Closed profits plus open entry fees','client_cash')
    check_client_drawdowns(record,curve,initial)
    check_client_calendar(record,flows,begin,end,initial,cash)
    return dict(portfolio='top5',view='as_packaged',scenario=scenario['id'],stress=stress,
        candidates=len(data['candidates']),closed_positions=len(trades),ending_cash=cash,
        ending_sampled_equity=equity,open_positions=len(active),sampled_equity_dd_pct=record['metrics']['max_sampled_equity_dd_pct'],
        min_lot_override_entries=expected_metrics['min_lot_override_entries'],capital_exhaustion_epoch=exhaustion),detailed


def check_client_drawdowns(record,curve,initial):
    eq_peak=cash_peak=initial
    daily_eq_peak=daily_cash_peak=initial
    dd_cash=dd_pct=closed_cash=closed_pct=daily_eq=daily_cash=daily_anchor=0.
    date=None
    for p in curve:
        current=datetime.fromtimestamp(p['epoch'],TZ).date()
        if current!=date:
            date=current
            anchor=daily_cash_peak=p['balance']
            daily_eq_peak=p['equity']
        eq_peak,cash_peak=max(eq_peak,p['equity']),max(cash_peak,p['balance'])
        daily_eq_peak,daily_cash_peak=max(daily_eq_peak,p['equity']),max(daily_cash_peak,p['balance'])
        dd_cash=max(dd_cash,eq_peak-p['equity'])
        dd_pct=max(dd_pct,100*(eq_peak-p['equity'])/eq_peak)
        closed_cash=max(closed_cash,cash_peak-p['balance'])
        closed_pct=max(closed_pct,100*(cash_peak-p['balance'])/cash_peak)
        daily_eq=max(daily_eq,daily_eq_peak-p['equity'])
        daily_cash=max(daily_cash,daily_cash_peak-p['balance'])
        daily_anchor=max(daily_anchor,anchor-p['equity'])
    for key,value in dict(max_sampled_equity_dd_cash=dd_cash,max_sampled_equity_dd_pct=dd_pct,
        max_closed_dd_cash=closed_cash,max_closed_dd_pct=closed_pct,max_daily_sampled_equity_dd_cash=daily_eq,
        max_daily_closed_dd_cash=daily_cash,max_daily_anchor_equity_loss=daily_anchor).items():
        close(record['metrics'][key],value,key,'client_drawdowns')


def check_client_calendar(record,flows,begin,end,initial,ending_cash):
    by_date=defaultdict(float)
    for flow in flows:by_date[datetime.fromtimestamp(flow['epoch'],UTC).date().isoformat()]+=flow['cash']
    cash=initial
    rates=[]
    require(len(record['daily'])==(end-begin)//86400,'All calendar days including zero-trade days','client_calendar')
    for n,actual in enumerate(record['daily']):
        label=datetime.fromtimestamp(begin+n*86400,UTC).date().isoformat()
        require(actual['date']==label,'Client cash calendar date','client_calendar')
        net=round(by_date[label],2)
        close(actual['opening_balance'],cash,'Client daily opening cash','client_calendar')
        close(actual['net_profit'],net,'Client daily cash profit','client_calendar')
        rates.append(net/cash if cash>0 else None)
        cash=round(cash+net,2)
        close(actual['ending_balance'],cash,'Client daily ending cash','client_calendar')
    close(cash,ending_cash,'Client calendar cash reconciliation','client_calendar')
    valid=all(x is not None for x in rates)
    sharpe=statistics.mean(rates)/statistics.stdev(rates)*math.sqrt(365) if valid and statistics.stdev(rates)>0 else None
    numeric(record['metrics']['daily_closed_return_sharpe'],sharpe,'Client cash-return Sharpe','client_calendar')
    require(len(record['months'])==3,'Three partial/full client months','client_calendar')
    for actual in record['months']:
        days=[d for d in record['daily'] if d['date'].startswith(actual['month'])]
        op,cl=days[0]['opening_balance'],days[-1]['ending_balance']
        values=dict(opening_balance=op,ending_balance=cl,net_profit=round(sum(d['net_profit'] for d in days),2),
            return_pct=(cl/op-1)*100 if op>0 else None)
        for key,value in values.items():numeric(actual[key],value,('Client monthly',key),'client_calendar')


def cost_diagnostics(records):
    diagnostics=[]
    for portfolio in ('top5','prop_ready'):
        for view in ('as_packaged','common_research'):
            for name in ('fixed50','compound5'):
                pair=[r for r in records if (r['portfolio'],r['view'],r['scenario']['id'])==(portfolio,view,name)]
                baseline=next(r for r in pair if not r['stress'])
                stressed=next(r for r in pair if r['stress'])
                first=next(((a,b) for a,b in zip(baseline['decisions'],stressed['decisions'])
                    if (a['reason']=='opened')!=(b['reason']=='opened')),None)
                by_id={t['id']:t for t in baseline['trades']}
                matched=0
                for t in stressed['trades']:
                    a=by_id.get(t['id'])
                    if a and abs(a['lots']-t['lots'])<1e-10:
                        require(t['net']<=a['net']+1e-8,'Higher costs cannot improve an identical-volume trade','cost_paths')
                        matched+=1
                diagnostics.append(dict(portfolio=portfolio,view=view,scenario=name,
                    first_admission_divergence_utc=datetime.fromtimestamp(first[0]['epoch'],UTC).isoformat() if first else None,
                    first_admission_divergence=dict(recorded=first[0],stress=first[1]) if first else None,
                    matched_equal_volume_trades=matched,
                    explanation='Aggregate returns can follow different admitted trades after cost-sensitive sizing/guard decisions; this is not a same-trade execution-cost comparison.'))
    return diagnostics


def largest_gap_loss_forensics(records,data,native):
    """Explain actual stop-fill loss beyond the planned stop geometry."""
    record=next(r for r in records if (r['portfolio'],r['view'],r['scenario']['id'],r['stress'])==
                ('top5','common_research','fixed50',False))
    trade=min(record['trades'],key=lambda p:p['net'])
    q=next(q for q in data['top5']['candidates'] if q['id']==trade['id'])
    meta=next(c for c in native['cases'] if c['slug']==q['ea'])
    folder=Path(meta['path']).parent
    parts=[d for d in csv.DictReader((folder/'deals.csv').open(encoding='utf-8-sig'))
           if int(d['position_id'])==q['position_id']]
    exits=[d for d in parts if int(d['entry'])==1]
    require(len(exits)==1 and not q['end_censored'],'Gap loss is an actual owned exit, not end-of-test liquidation','gap_forensics')
    require(exits[0]['comment'].lower().startswith('sl '),'Largest observed loss is a stop execution','gap_forensics')
    close(trade['risk'],q['unit_risk']*trade['lots'],'Gap loss allocation remains within planned stop risk','gap_forensics')
    close(trade['net'],trade['gross']+trade['commission']+trade['swap'],'Gap loss costs reconcile','gap_forensics')
    slip=q['sl']-q['close_price'] if q['side'].lower() in ('buy','long','0') else q['close_price']-q['sl']
    return dict(portfolio='top5',view='common_research',scenario='fixed50',stress=False,
        position=trade['id'],open_utc=datetime.fromtimestamp(q['op'],UTC).isoformat(),
        close_utc=datetime.fromtimestamp(q['cl'],UTC).isoformat(),
        close_Prague=datetime.fromtimestamp(q['cl'],TZ).isoformat(),
        side=q['side'],entry_price=q['open_price'],original_stop=q['sl'],actual_exit=q['close_price'],
        adverse_stop_fill_difference_points=slip,lots=trade['lots'],planned_stop_cash=trade['risk'],
        gross=trade['gross'],commission=trade['commission'],swap=trade['swap'],net=trade['net'],
        loss_multiple_of_planned_stop=abs(trade['net'])/trade['risk'],native_exit_reason=exits[0]['reason'],
        native_exit_comment=exits[0]['comment'],end_censored=False,
        explanation='A source-native stop filled beyond the original stop at the Sunday reopening, with weekend financing added. Planned-risk floors do not guarantee an execution price or cap the realized loss. No synthetic final liquidation or sizing-rule change was used.')


def main():
    frozen=load(ROOT/'FROZEN.json')
    results=load(ROOT/'RESULTS.json')
    plan=load(ROOT/'PLAN.json')
    data=load(ROOT/'INPUTS.json')
    broker=load(ORIGINAL/'BROKER.json')
    for file,expected in {**frozen['files'],**frozen['source_files']}.items():
        require(digest(file)==expected,'Comparison/ancestor immutable hash','comparison_freeze')
    require(frozen['frozen_before_outcomes'] is True,'Comparison frozen before risk outcomes','comparison_freeze')
    require(results['frozen_sha256']==digest(ROOT/'FROZEN.json'),'Comparison outcome freeze receipt','comparison_freeze')
    require(results['plan']==plan and results['broker']==broker,'Published plan/broker exact match','protocol')
    native_frozen=load(ROOT/'native/FROZEN.json')
    for file,expected in {**native_frozen['files'],**native_frozen['source_files']}.items():
        require(digest(file)==expected,'Native/production immutable hash','native_freeze')
    require(native_frozen['frozen_before_results'] is True,'Native source frozen before outcomes','native_freeze')
    native=load(ROOT/'native/native_cases.json')
    native_plan=load(ROOT/'native/native_plan.json')
    manifest=load(ROOT.parents[2]/'clients/_owner/top5/manifest.json')
    verify_top5_sources(data['top5'],native,native_plan,manifest)
    source.verify_sources(data['prop_ready'],load(ORIGINAL/'native_cases.json'),load(ORIGINAL/'FROZEN.json'))
    begin,end=(int(datetime.fromisoformat(x).timestamp()) for x in plan['window_utc'])
    verify_export_only_revision()
    phase_diagnostics=verify_owned_native_marks(data['top5'],native,begin,end)
    prior.verify_native_mark_values(data['prop_ready'],load(ORIGINAL/'native_cases.json'),begin,end)
    expected={(s['portfolio'],s['view'],s['id'],stress) for s in plan['scenarios'] for stress in (False,True)}
    actual=[(r['portfolio'],r['view'],r['scenario']['id'],r['stress']) for r in results['results']]
    require(len(actual)==16 and set(actual)==expected,'Exactly sixteen declared portfolio/policy/risk/cost cases','protocol')
    summaries=[]
    for record in results['results']:
        portfolio=record['portfolio']
        require(record['scenario']['portfolio']==portfolio and record['scenario']['view']==record['view'],'Scenario/view identity','protocol')
        if record['scenario']['guard_policy']=='client':summary,_=client_audit(record,data[portfolio],plan,broker)
        else:
            summary,_=prior.audit(record,data[portfolio],dict(priority=plan['portfolios'][portfolio]),plan,broker)
            summary.update(portfolio=portfolio,view=record['view'])
        summaries.append(summary)
    diagnostics=cost_diagnostics(results['results'])
    gap_forensics=largest_gap_loss_forensics(results['results'],data,native)
    payload=dict(status='PASS',checks=sum(source.CHECKS.values()),categories=dict(source.CHECKS),
        verified_candidates={k:len(v['candidates']) for k,v in data.items()},scenarios=summaries,
        cost_path_diagnostics=diagnostics,phase_causality=phase_diagnostics,largest_gap_loss=gap_forensics,
        result_sha256=digest(ROOT/'RESULTS.json'),freeze_sha256=digest(ROOT/'FROZEN.json'),
        verifier_sha256=digest(__file__),method='Separate independent client event ledger and earlier independent Prop/common ledger; never imports compare.py, run.py or replay.py. Verifies every native risk receipt and owned past floating mark, all admissions/volumes/fees/censored positions/curves/metrics/cash calendars and frozen hashes.',
        limitations=['Two exposed months and synthetic resizing are not evidence of a durable edge or a future return.',
            'Historical source is Trial16, current demo margin/contract metadata is Trial15; not an exact current-demo native portfolio.',
            'Standalone source candidates do not reconstruct unobserved counterfactual signals or liquidity/size-dependent costs.',
            'Sampled floating drawdown and margin levels cannot certify intrabar risk or broker stopout paths.',
            'As-packaged results deliberately have different caps, compounding bases and minimum-lot policies; use the common research view for controlled comparisons.'])
    (ROOT/'VERIFICATION.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='PASS',checks=payload['checks'],verified_candidates=payload['verified_candidates'],scenarios=summaries),indent=2))


if __name__=='__main__':main()
