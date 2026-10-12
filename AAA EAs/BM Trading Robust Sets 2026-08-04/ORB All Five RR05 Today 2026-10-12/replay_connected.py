"""Transparent closed-bar/tick reconstruction of five frozen ORBs; offline, not native MT5."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
import hashlib,html,json,math
import numpy as np

R=Path(__file__).resolve().parent;B=R.parent
data=np.load(R/'connected-bars-ticks.npz',allow_pickle=False)
meta=json.loads((R/'connected-snapshot.json').read_text())
plan={p['slug']:p for p in json.loads((B/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json').read_text())['setups']}
policy=json.loads((B/'_00 Live profiles/ORB05-policy.json').read_text())
NY=ZoneInfo('America/New_York');UTC=timezone.utc
TODAY=datetime(2026,10,12,tzinfo=UTC)
def stamp(day,h,m=0,zone=UTC):
    return datetime(day.year,day.month,day.day,h,m,tzinfo=zone).timestamp()
def text(t):return datetime.fromtimestamp(t,UTC).isoformat()
def bars(symbol,tf):return data[symbol+'_'+str(tf)]
def slice_rates(symbol,tf,start,end):
    a=bars(symbol,tf);return a[(a['time']>=start)&(a['time']<end)]
def med(values):return float(np.median(values)) if len(values) else 0.
def body(bar):return float(abs(bar['close']-bar['open'])/(bar['high']-bar['low'])) if bar['high']>bar['low'] else 0.
def atr(symbol,tf,period,now):
    a=bars(symbol,tf);a=a[a['time']+tf*60<=now]
    assert len(a)>period
    tr=np.maximum(a['high'][1:]-a['low'][1:],np.maximum(abs(a['high'][1:]-a['close'][:-1]),abs(a['low'][1:]-a['close'][:-1])))
    return float(np.mean(tr[-period:]))
def historical_windows(symbol,minutes,hour,minute,zone,require_full=False):
    volumes=[]
    for lag in range(1,81):
        day=TODAY-timedelta(days=lag)
        if day.weekday()>=5:continue
        start=stamp(day,hour,minute,zone)
        a=slice_rates(symbol,1,start,start+minutes*60)
        if len(a)<(minutes if require_full else max(1,minutes//2)):continue
        vol=int(a['tick_volume'].sum())
        if vol>0:volumes.append(vol)
        if len(volumes)==20:break
    assert len(volumes)==20,'Insufficient opening-volume history'
    return med(volumes)
def first_tick(symbol,epoch):
    a=data[symbol+'_ticks'];i=np.searchsorted(a['time_msc'],int(epoch*1000),side='left')
    return a[i] if i<len(a) else None
def entry_attempt(symbol,p,when,direction,low,high,volatility,selective=False):
    tick=first_tick(symbol,when)
    if tick is None:return None,'no entry quote'
    width=high-low;spread=float(tick['ask']-tick['bid'])
    spreadmax=float(p['InpMaximumSpreadRangePercent'] if selective else p['InpMaxSpreadRangePercent'])
    if spread/width*100>spreadmax:return None,'spread too wide'
    quote=float(tick['ask'] if direction>0 else tick['bid'])
    buffer=float(p['InpStopBufferRange'])*width if selective else float(p['InpStopBufferATR'])*volatility
    info=meta['symbols'][symbol];ts=info['trade_tick_size']
    rounded=lambda x:math.floor(x/ts+.5)*ts
    stop=rounded(low-buffer if direction>0 else high+buffer)
    risk=direction*(quote-stop)
    maxstop=float(p['InpMaximumStopDailyATR'] if selective else p['InpMaximumStopATR'])*volatility
    if risk<=0 or risk>maxstop:return None,'stop-distance filter'
    if risk<info['trade_stops_level']*info['point']:return None,'broker stop minimum'
    target=rounded(quote+direction*.5*risk)
    # Deterministic quote delay; real broker acknowledgement/slippage is unknown.
    fill=first_tick(symbol,float(tick['time_msc'])/1000+.150)
    if fill is None:return None,'no delayed fill quote'
    price=float(fill['ask'] if direction>0 else fill['bid'])
    unit=risk*info['trade_contract_size'];step=info['volume_step']
    volume=max(info['volume_min'],min(info['volume_max'],math.ceil((100/unit-1e-12)/step)*step))
    return dict(side='Buy' if direction>0 else 'Sell',direction=direction,open_epoch=float(fill['time_msc'])/1000,
        entry=price,request_quote=quote,sl=stop,tp=target,initial_risk_distance=risk,volume=volume,
        planned_stop_usd=risk*info['trade_contract_size']*volume,delay_ms=150),None

def common(row):
    p=row['input_settings'];symbol=row['symbol'];zone=UTC if p['InpSessionZone']=='1' else NY
    start=stamp(TODAY,int(p['InpSessionHour']),int(p['InpSessionMinute']),zone)
    minutes=int(p['InpOpeningRangeMinutes']);end=start+minutes*60;cutoff=end+int(p['InpTradeWindowMinutes'])*60
    a=slice_rates(symbol,1,start,end);assert len(a)>=minutes//2
    high=float(a['high'].max());low=float(a['low'].min());width=high-low
    volume=float(a['tick_volume'].sum())
    baseline=historical_windows(symbol,minutes,int(p['InpSessionHour']),int(p['InpSessionMinute']),zone)
    rvol=volume/baseline
    tf=int(p['InpSignalTimeframe']);atf={16385:60,16388:240}.get(int(p['InpATRTimeframe']),int(p['InpATRTimeframe']));period=int(p['InpATRPeriod'])
    checks=[];ready=None;frozen=None;gate_readings=[]
    # Native retries its range gate on ticks/timer until ready. ATR only changes
    # at closed ATR-bar boundaries; this minute scan captures those updates.
    for now in np.arange(end,min(cutoff,datetime.fromisoformat(meta['snapshot_utc']).timestamp())+1,60):
        v=atr(symbol,atf,period,now);ratio=width/v
        gate_readings.append(dict(time=text(float(now)),atr=v,range_atr=ratio))
        if rvol>=float(p['InpMinOpeningRelativeVolume']) and float(p['InpMinRangeATR'])<=ratio<=float(p['InpMaxRangeATR']):ready=float(now);frozen=v;break
    result=dict(slug=row['slug'],label=row['label'],symbol=symbol,range_start=text(start),range_end=text(end),entry_cutoff=text(cutoff),
        high=high,low=low,range_width=width,opening_rvol=rvol,minimum_opening_rvol=float(p['InpMinOpeningRelativeVolume']),
        minimum_range_atr=float(p['InpMinRangeATR']),maximum_range_atr=float(p['InpMaxRangeATR']),
        smallest_observed_range_atr=min(g['range_atr'] for g in gate_readings),
        range_ready=text(ready) if ready else None,atr=frozen,checks=checks,trade=None)
    if ready is None:
        result['reason']='Opening-volume/range-size gate failed';return result
    allbars=bars(symbol,tf)
    for i,b in enumerate(allbars):
        now=int(b['time'])+tf*60
        if b['time']<end:continue
        if now>=cutoff or now>datetime.fromisoformat(meta['snapshot_utc']).timestamp():break
        if now<ready:continue
        prior=allbars[(allbars['time']>=int(b['time'])-(int(p['InpBarVolumeLookback'])+5)*tf*60)&(allbars['time']<b['time'])]
        rv=float(b['tick_volume'])/med(prior['tick_volume'][-int(p['InpBarVolumeLookback']):])
        bu=float(p['InpBreakoutBufferATR'])*frozen
        direction=1 if b['close']>high+bu and b['close']>b['open'] else -1 if b['close']<low-bu and b['close']<b['open'] else 0
        reasons=[]
        if body(b)<float(p['InpBreakoutBodyMinimum']):reasons.append('body too weak')
        if rv<float(p['InpMinBreakoutRelativeVolume']):reasons.append('breakout volume too low')
        if direction==0:reasons.append('no direction-matching close beyond buffered range')
        c=dict(bar_open=text(int(b['time'])),decision=text(now),close=float(b['close']),body_ratio=body(b),breakout_rvol=rv,direction=direction,reasons=reasons)
        checks.append(c)
        if reasons:continue
        trade,reason=entry_attempt(symbol,p,now,direction,low,high,frozen)
        if trade:result['trade']=trade;result['reason']='Qualifying breakout';break
        c['reasons'].append(reason)
    if result['trade'] is None:result['reason']='No completed candle passed every entry gate'
    return result

def rth(symbol,day):
    a=slice_rates(symbol,5,stamp(day,9,30,NY),stamp(day,16,0,NY))
    if len(a)<60:return None
    return float(a['high'].max()),float(a['low'].min()),float(a[-1]['close'])
def selective(row):
    p=row['input_settings'];s=row['symbol'];start=stamp(TODAY,9,30,NY);end=start+int(p['InpOpeningRangeMinutes'])*60
    cutoff=stamp(TODAY,int(p['InpEntryCutoffHour']),int(p['InpEntryCutoffMinute']),NY)
    a=slice_rates(s,1,start,end);assert len(a)==int(p['InpOpeningRangeMinutes'])
    hi=float(a['high'].max());lo=float(a['low'].min());width=hi-lo
    ranges=[]
    for lag in range(1,81):
        day=TODAY-timedelta(days=lag)
        if day.weekday()>=5:continue
        stats=rth(s,day)
        if stats is None:continue
        previous=None
        for delta in range(1,13):
            older=day-timedelta(days=delta)
            if older.weekday()<5:previous=rth(s,older)
            if previous:break
        if not previous:continue
        h,l,c=stats;ranges.append(max(h-l,abs(h-previous[2]),abs(l-previous[2])))
        if len(ranges)==20:break
    assert len(ranges)==20
    daily=med(ranges);opening=float(a['tick_volume'].sum())/historical_windows(s,int(p['InpOpeningRangeMinutes']),9,30,NY,True)
    ratio=width/daily
    result=dict(slug=row['slug'],label=row['label'],symbol=s,range_start=text(start),range_end=text(end),entry_cutoff=text(cutoff),
        high=hi,low=lo,range_width=width,daily_atr_proxy=daily,opening_rvol=opening,normalized_range=ratio,checks=[],trade=None)
    if not float(p['InpMinimumRangeDailyATR'])<=ratio<=float(p['InpMaximumRangeDailyATR']) or opening<float(p['InpMinimumOpeningRelativeVolume']):
        result['reason']='Opening-volume/range-size gate failed (native one-attempt range build)';return result
    tf=int(p['InpSignalTimeframe']);direction=age=0
    for b in slice_rates(s,tf,end,cutoff):
        now=int(b['time'])+tf*60
        if now>=cutoff or now>datetime.fromisoformat(meta['snapshot_utc']).timestamp():break
        c=dict(bar_open=text(int(b['time'])),decision=text(now),body_ratio=body(b),close=float(b['close']),reasons=[])
        result['checks'].append(c)
        if direction:
            age+=1;excursion=float(b['high']-hi if direction>0 else lo-b['low'])
            if age>int(p['InpMaximumRetestBars']) or excursion>float(p['InpMaximumPreRetestExcursionRange'])*width:
                c['reasons'].append('retest expired/excursion too large');direction=0;continue
            tolerance=float(p['InpRetestToleranceRange'])*width
            accepted=(b['low']<=hi+tolerance and b['close']>=hi and b['close']>b['open']) if direction>0 else (b['high']>=lo-tolerance and b['close']<=lo and b['close']<b['open'])
            if not accepted:c['reasons'].append('waiting for retest');continue
            d=direction;direction=0
            minute=datetime.fromtimestamp(now,NY).hour*60+datetime.fromtimestamp(now,NY).minute
            if p['InpUseTimeDirectionFilter']=='true':
                long_start=int(p['InpLongOnlyStartHour'])*60+int(p['InpLongOnlyStartMinute']);short_start=int(p['InpShortOnlyStartHour'])*60+int(p['InpShortOnlyStartMinute'])
                if (long_start<=minute<short_start and d<0) or (minute>=short_start and d>0):c['reasons'].append('time/direction gate');continue
            trade,reason=entry_attempt(s,p,now,d,lo,hi,daily,True)
            if trade:result['trade']=trade;result['reason']='Qualifying breakout and retest';break
            c['reasons'].append(reason);continue
        if body(b)<float(p['InpBreakoutBodyMinimum']):c['reasons'].append('body too weak');continue
        past=[];local=datetime.fromtimestamp(int(b['time']),NY)
        for lag in range(1,81):
            day=TODAY-timedelta(days=lag)
            if day.weekday()>=5:continue
            old=slice_rates(s,tf,stamp(day,local.hour,local.minute,NY),stamp(day,local.hour,local.minute,NY)+tf*60)
            if len(old)==1 and old[0]['tick_volume']>0:past.append(int(old[0]['tick_volume']))
            if len(past)==20:break
        assert len(past)==20
        rv=float(b['tick_volume'])/med(past);c['breakout_rvol']=rv
        if rv<float(p['InpMinimumBreakoutRelativeVolume']):c['reasons'].append('breakout volume too low');continue
        buffer=float(p['InpBreakoutBufferDailyATR'])*daily
        d=1 if b['close']>hi+buffer and b['close']>b['open'] else -1 if b['close']<lo-buffer and b['close']<b['open'] else 0
        if not d:c['reasons'].append('no direction-matching breakout');continue
        session=slice_rates(s,tf,start,now);vwap=float(np.sum((session['high']+session['low']+session['close'])/3*session['tick_volume'])/session['tick_volume'].sum());c['vwap']=vwap
        if p['InpRequireSessionVWAP']=='true' and ((d>0 and b['close']<=vwap) or (d<0 and b['close']>=vwap)):c['reasons'].append('VWAP gate');continue
        direction=d;age=0;c['reasons'].append('breakout armed; waits for retest')
    if result['trade'] is None:result['reason']='No eligible breakout/retest completed'
    return result

def manage(case):
    t=case['trade']
    if t is None:return
    p=plan[case['slug']]['input_settings'];s=case['symbol'];ticks=data[s+'_ticks'];ticks=ticks[ticks['time_msc']>=t['open_epoch']*1000]
    selective_flag=case['slug']=='us100-selective-orb-v3';zone=NY if selective_flag or p.get('InpSessionZone')=='0' else UTC
    flat=stamp(TODAY,int(p['InpFlatHour']),int(p['InpFlatMinute']),zone)
    d=t['direction'];tf=int(p['InpSignalTimeframe']);contract=meta['symbols'][s]['trade_contract_size'];sl=t['sl'];minimum=meta['symbols'][s]['trade_stops_level']*meta['symbols'][s]['point']
    last_bar=int(t['open_epoch'])//(tf*60);reason='OPEN';price=None;epoch=None
    for tick in ticks:
        now=float(tick['time_msc'])/1000;exit_price=float(tick['bid'] if d>0 else tick['ask'])
        if d*(exit_price-sl)<=0:reason='SL';price=exit_price;epoch=now;break
        if d*(exit_price-t['tp'])>=0:reason='TP';price=t['tp'];epoch=now;break
        if now>=flat:reason='TIME';price=exit_price;epoch=now;break
        current=int(now)//(tf*60)
        if current!=last_bar:
            last_bar=current;be=float(p['InpBreakEvenAtR'])
            if be>0 and abs(sl-t['entry'])>meta['symbols'][s]['point']:
                prior=slice_rates(s,tf,current*tf*60-tf*60,current*tf*60)
                if len(prior):
                    favor=float(prior[-1]['high']-t['entry'] if d>0 else t['entry']-prior[-1]['low'])
                    if favor>=be*t['initial_risk_distance'] and d*(exit_price-t['entry'])>minimum:sl=t['entry'];t['break_even_at']=text(now)
    if reason=='OPEN':
        tick=ticks[-1];epoch=float(tick['time_msc'])/1000;price=float(tick['bid'] if d>0 else tick['ask'])
    cash=(price-t['entry'])*d*contract*t['volume']
    t.update(status=reason,exit_or_mark_epoch=epoch,exit_or_mark_price=price,profit_usd=round(cash,2),return_pct=round(cash/100,4),
        commission_assumption=0,swap_assumption=0,broker_spread_included=True,closed=reason!='OPEN')

def main():
    cases=[]
    for slug in policy['slugs']:
        row=plan[slug];case=selective(row) if slug=='us100-selective-orb-v3' else common(row)
        manage(case);cases.append(case)
        print(case['label'],case['reason'],json.dumps(case['trade']),flush=True)
    closed=[c['trade'] for c in cases if c['trade'] and c['trade']['closed']];opened=[c['trade'] for c in cases if c['trade'] and not c['trade']['closed']]
    realized=sum(t['profit_usd'] for t in closed);floating=sum(t['profit_usd'] for t in opened)
    result=dict(date='2026-10-12',cutoff_utc=meta['snapshot_utc'],broker=meta['account']['server'],deposit_usd=10000,risk_percent=1,
        risk_basis='Separate 1% initial-$10k risk scenarios per EA; summed observed cash is an unrestricted overlay, not shared-equity/FTMO guard execution.',
        rr=.5,cases=cases,trades=len(closed)+len(opened),closed=len(closed),open=len(opened),realized=round(realized,2),floating=round(floating,2),
        aggregate_equity=round(10000+realized+floating,2),win_rate=100*sum(t['profit_usd']>0 for t in closed)/len(closed) if closed else None,
        method='Read-only connected broker bars/ticks; closed-bar rule reconstruction, not native MT5 Strategy Tester. Isolated native test rejected future end date for the incomplete current day.',
        assumptions=['Assumes each EA running before its opening window and no carried same-magic position. Does not reproduce live restart history or all-account blockers.',
            'Original filters retained. Bid/ask spread included. Deterministic 150ms quote delay; unknown broker rejections, acknowledgement and slippage not modelled.',
            'No same-day commission/swap charged in this raw Exness demo reconstruction. FTMO commissions, shared guards, risk taper, margin constraints are not applied.',
            '1% setting is not a guaranteed maximum loss; original lot rounding rounds up. All targets use 0.5R from order-request quote; actual fill can change realized R slightly.'],
        data_sha256=hashlib.sha256((R/'connected-bars-ticks.npz').read_bytes()).hexdigest(),no_live_changes=True)
    (R/'Results.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    rows=[];logs=[]
    for c in cases:
        t=c['trade'];pnl=f"${t['profit_usd']:+.2f}" if t else '—'
        rows.append('<tr><td>'+html.escape(c['label'])+'</td><td>'+('1' if t else '0')+'</td><td>'+('Sell' if t and t['direction']<0 else 'Buy' if t else '—')+'</td><td>'+(text(t['open_epoch'])[11:23]+' UTC' if t else '—')+'</td><td>'+(t['status'] if t else 'No trade')+'</td><td>'+pnl+'</td><td>'+html.escape(c['reason'])+'</td></tr>')
        logs.append('<details><summary>'+html.escape(c['label'])+' — range and every entry check</summary><pre>'+html.escape(json.dumps(c,indent=2))+'</pre></details>')
    report='''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>All five ORBs · 0.5R · 12 October</title><style>body{font:16px system-ui;background:#081b14;color:#eafff5;max-width:1450px;margin:30px auto;padding:20px}p{line-height:1.6;color:#bdd6cb}table{border-collapse:collapse;width:100%}td,th{padding:13px;text-align:left;border-bottom:1px solid #375848}details{margin:20px 0}pre{overflow:auto;max-height:600px}.wide{overflow:auto}</style><h1>Five ORBs at 0.5R — today, 12 October 2026</h1>'''
    report+='<p>'+html.escape(result['method'])+'</p><p>Cutoff: '+meta['snapshot_utc']+'. $10,000, 1% initial risk per EA. All original entry filters, stops and management retained. This is an unrestricted summed scenario, not a guarded FTMO portfolio.</p>'
    report+='<p>Closed trades: '+str(len(closed))+', open: '+str(len(opened))+'. Realized: $'+f'{realized:+.2f}'+', floating: $'+f'{floating:+.2f}'+'. Marked balance/equity: $'+f"{result['aggregate_equity']:,.2f}"+'.</p><div class="wide"><table><tr><th>EA</th><th>Trades</th><th>Direction</th><th>Entry</th><th>Status</th><th>P/L</th><th>Decision</th></tr>'+''.join(rows)+'</table></div><h2>Assumptions</h2><ul>'+''.join('<li>'+html.escape(a)+'</li>' for a in result['assumptions'])+'</ul><h2>Detailed gate audit and trades</h2>'+''.join(logs)+'</html>'
    (R/'Results.html').write_text(report,encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['cutoff_utc','trades','closed','open','realized','floating','aggregate_equity','win_rate']}))
if __name__=='__main__':main()
