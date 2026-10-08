"""Closed-cash portfolio metrics and offline entry-time allocation. No trading APIs."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import math

from .risk_metrics import annualised_sharpe
from .risk_visuals import rolling_sharpe, streak_distribution


def performance(trades, start, end, initial=10000):
    trades=sorted(trades,key=lambda t:(t['close_time'],t.get('slug',''),t.get('position_id',0)))
    wins=[t['net_profit'] for t in trades if t['net_profit']>.005]
    losses=[t['net_profit'] for t in trades if t['net_profit']<-.005]
    balance=peak=initial;dd=cashdd=0;w=l=maxw=maxl=0
    current_day=None;daily_peak=daily_anchor=initial;daily_dd=daily_cashdd=daily_loss=0
    curve=[dict(time=start+'T00:00:00+00:00',balance=initial)]
    months=defaultdict(lambda:dict(trades=0,net_profit=0.0))
    for t in trades:
        day=t['close_time'][:10]
        if day!=current_day:
            current_day=day;daily_peak=daily_anchor=balance
        net=t['net_profit'];balance+=net;peak=max(peak,balance);daily_peak=max(daily_peak,balance)
        daily_dd=max(daily_dd,(daily_peak-balance)/daily_peak*100 if daily_peak>0 else 0)
        daily_cashdd=max(daily_cashdd,daily_peak-balance)
        daily_loss=max(daily_loss,(daily_anchor-balance)/daily_anchor*100 if daily_anchor>0 else 0)
        dd=max(dd,(peak-balance)/peak*100 if peak>0 else 0);cashdd=max(cashdd,peak-balance)
        if net>.005:w+=1;l=0
        elif net<-.005:l+=1;w=0
        else:w=l=0
        maxw,maxl=max(maxw,w),max(maxl,l)
        curve.append(dict(time=t['close_time'],balance=round(balance,6)))
        m=months[t['close_time'][:7]];m['trades']+=1;m['net_profit']+=net
    avgw=sum(wins)/len(wins) if wins else None;avgl=sum(losses)/len(losses) if losses else None
    a,b=date.fromisoformat(start),date.fromisoformat(end)-timedelta(days=1)
    # A guarded account can stop admitting trades years before the selected
    # window ends. Keep the no-trade tail visible rather than truncating its
    # chart or making idle calendar months look like absent evidence.
    curve.append(dict(time=end+'T00:00:00+00:00',balance=round(balance,6)))
    cursor=date(a.year,a.month,1)
    while cursor<=b:
        months.setdefault(cursor.strftime('%Y-%m'),dict(trades=0,net_profit=0.0))
        cursor=date(cursor.year+(cursor.month==12),cursor.month%12+1,1)
    days=(b-a).days+1;weekdays=sum((a+timedelta(days=i)).weekday()<5 for i in range(days))
    stats=dict(trades=len(trades),return_pct=(balance/initial-1)*100,net_profit=balance-initial,
        initial_balance=initial,final_balance=balance,profit_factor=sum(wins)/-sum(losses) if losses else None,
        win_rate_pct=len(wins)/len(trades)*100 if trades else None,max_drawdown_pct=dd,max_drawdown_cash=cashdd,
        max_daily_closed_drawdown_pct=daily_dd,max_daily_closed_drawdown_cash=daily_cashdd,
        max_daily_closed_loss_pct=daily_loss,max_daily_equity_drawdown_pct=None,
        sharpe_ratio=annualised_sharpe(trades,a,b,initial),recovery_factor=(balance-initial)/cashdd if cashdd else None,
        max_win_streak=maxw,max_loss_streak=maxl,average_win=avgw,average_loss=avgl,
        payoff_ratio=avgw/-avgl if avgw is not None and avgl else None,trades_per_day=len(trades)/days,
        trades_per_weekday=len(trades)/weekdays if weekdays else None)
    return stats,curve,[dict(month=k,**v) for k,v in sorted(months.items())]


def history_from_trades(trades,start,end,period,label,basis,scope,missing=None,initial=10000):
    trades=sorted((t for t in trades if start<=t['close_time'][:10]<end),
        key=lambda t:(t['close_time'],t.get('slug',''),t.get('position_id',0)))
    stats,curve,months=performance(trades,start,end,initial)
    streaks=streak_distribution([dict(t,number=i,net_profit=0 if abs(t['net_profit'])<=.005 else t['net_profit']) for i,t in enumerate(trades)])
    streaks.pop('timeline',None)
    assert stats['max_win_streak']==streaks['max_win_streak'] and stats['max_loss_streak']==streaks['max_loss_streak']
    rolling=rolling_sharpe(trades,date.fromisoformat(start),date.fromisoformat(end)-timedelta(days=1),initial)
    if len(curve)>1400:
        indices=set(range(0,len(curve),math.ceil(len(curve)/1400)))|{len(curve)-1,
            min(range(len(curve)),key=lambda i:curve[i]['balance']),max(range(len(curve)),key=lambda i:curve[i]['balance'])}
        curve=[curve[i] for i in sorted(indices)]
    return dict(id=period,label=label,available=True,coverage='complete',start=start,requested_start=start,
        end_exclusive=end,stats=stats,curve=curve,months=months,rolling_sharpe=rolling,streaks=streaks,
        basis=basis,scope=scope,missing_members=missing or [],
        chart_note='Closed-position cash; metrics use every completed position. The final point marks the end-exclusive boundary, not an extra trade. Idle months show zero covered closed cash. Chart may be downsampled.')


def allocation_replay(rows,start,end,mode,value,initial,*,adaptive=False,news_percent=.10,daily_mode='off',daily_value=0):
    """Replay entry/exit events; never let future exit P/L influence entry sizing."""
    begin=datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp()
    finish=datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()
    eligible=[r for r in rows if begin<=r['op']<r['cl']<finish and r['unit_risk']>0]
    events=sorted([(r['op'],1,i) for i,r in enumerate(eligible)]+[(r['cl'],0,i) for i,r in enumerate(eligible)])
    balance=peak=initial;active={};closed=[];lossruns=defaultdict(int);daily=defaultdict(float);skips=0
    anchors={};stopped=set()
    for timestamp,kind,i in events:
        r=eligible[i];key=r['key'];losskey=r.get('lane',key);day=datetime.fromtimestamp(timestamp,timezone.utc).date().isoformat()
        anchors.setdefault(day,balance)
        if kind==1:
            if balance<=0:skips+=1;continue
            if day in stopped:skips+=1;continue
            budget=value if mode=='fixed' else balance*value/100
            budget*=r.get('risk_weight',1.)
            if adaptive:
                if r.get('news'):
                    budget=balance*news_percent/100
                else:
                    if daily[day]<=-initial*.05:skips+=1;continue
                    drawdown=(peak-balance)/peak*100
                    budget*=.25 if drawdown>=7 else .5 if drawdown>=4 else 1
                    budget*=.25 if lossruns[losskey]>=5 else .5 if lossruns[losskey]>=3 else 1
                    if key=='nasdaq-5m-candle-momentum':budget*=.25
            active[i]=budget/r['unit_risk']
        elif i in active:
            lot=active.pop(i)
            net=lot*(r['unit_gross']+r['unit_comm']+r['unit_swap'])
            balance+=net;peak=max(peak,balance);daily[day]+=net
            if daily_mode!='off':
                limit=daily_value if daily_mode=='fixed' else anchors[day]*daily_value/100
                if daily[day]<=-limit:stopped.add(day)
            lossruns[losskey]=lossruns[losskey]+1 if net<-.005 else 0
            closed.append(dict(slug=key,position_id=i,close_time=datetime.fromtimestamp(timestamp,timezone.utc).isoformat(),net_profit=net))
    return closed,dict(skipped_entries=skips,ruin=balance<=0,daily_stopped_days=len(stopped))
