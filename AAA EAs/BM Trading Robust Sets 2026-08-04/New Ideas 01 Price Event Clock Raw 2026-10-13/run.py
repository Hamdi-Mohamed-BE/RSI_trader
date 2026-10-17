"""Unoptimised M1-sampled price-event model; supported API data only, no trading."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
END = int(pd.Timestamp('2026-10-13', tz='UTC').timestamp())
SYMBOLS = ['BTCUSD', 'XAUUSD', 'USTEC']
NAMES = {'BTCUSD':'BTC', 'XAUUSD':'Gold', 'USTEC':'US100', 'shared':'Shared three-asset account'}
STARTS = {'1y':'2025-10-13', '6m':'2026-04-13', '3m':'2026-07-13'}


def save(name, value):
    (ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


@dataclass
class Event:
    high: float = math.nan
    low: float = math.nan
    armed: int = 0

    def reset(self, price=None):
        self.high = self.low = math.nan if price is None else price
        self.armed = 0

    def update(self, price, delta):
        if not math.isfinite(self.high):
            self.reset(price)
            return None
        if self.armed == 1:
            self.low = min(self.low, price)
            if price >= self.low + delta:
                signal = (1,self.low)
                self.reset(price)
                return signal
        elif self.armed == -1:
            self.high = max(self.high, price)
            if price <= self.high - delta:
                signal = (-1,self.high)
                self.reset(price)
                return signal
        else:
            self.high, self.low = max(self.high,price), min(self.low,price)
            if price <= self.high - 2*delta:
                self.armed, self.low = 1, price
            elif price >= self.low + 2*delta:
                self.armed, self.high = -1, price
        return None


def wilder(values, period=14):
    out = np.full(len(values),np.nan)
    if len(values) >= period:
        out[period-1] = np.mean(values[:period])
        for i in range(period,len(values)):
            out[i] = ((period-1)*out[i-1] + values[i])/period
    return out


def prepare():
    meta = json.loads((ROOT/'DATA.json').read_text())
    data = {}
    for symbol in SYMBOLS:
        path = ROOT/f'{symbol}-M1.npz'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta['files'][symbol]['sha256']
        f = pd.DataFrame(np.load(path,allow_pickle=False)['rates'])
        assert np.all(np.diff(f.time)>0)
        assert ((f.high>=f[['open','close','low']].max(axis=1)) &
                (f.low<=f[['open','close','high']].min(axis=1))).all()
        f.index = pd.to_datetime(f.time,unit='s',utc=True)
        point = meta['files'][symbol]['specification']['point']
        f['used_spread'] = f.spread.where(f.spread>0).ffill()*point
        m5 = f.resample('5min').agg({'open':'first','high':'max','low':'min','close':'last','time':'count'})
        m5 = m5[m5.time==5]
        previous = m5.close.shift(1)
        tr = pd.concat([m5.high-m5.low,(m5.high-previous).abs(),(m5.low-previous).abs()],axis=1).max(axis=1)
        atr = pd.Series(wilder(tr.to_numpy()),index=m5.index+pd.Timedelta(minutes=5))
        days = pd.date_range('2025-08-01','2026-10-13',tz='UTC')
        frozen = atr.reindex(days,method='ffill')
        f['delta'] = frozen.reindex(f.index.floor('D')).to_numpy()
        meta['files'][symbol]['complete_m5_bars'] = len(m5)
        meta['files'][symbol]['zero_spread_rows'] = int((f.spread<=0).sum())
        meta['files'][symbol]['test_m1_bars'] = int(((f.time>=pd.Timestamp(STARTS['1y'],tz='UTC').timestamp()) & (f.time<END)).sum())
        data[symbol] = f[['time','open','high','low','close','used_spread','delta']].to_numpy()
    return data, meta


def intrabar_exit(position, bar, target_first=False):
    """Entry at minute OPEN; conservative known stop/target path ambiguity."""
    side,stop,target = position['side'],position['stop'],position['target']
    o,h,l,c,spread = bar[1:6]
    if side<0:
        o,h,l = o+spread,h+spread,l+spread
    sl = l<=stop if side>0 else h>=stop
    tp = h>=target if side>0 else l<=target
    if sl and tp:
        return (target,'TP',True) if target_first else (stop,'SL',True)
    if sl:
        return stop,'SL',False
    if tp:
        return target,'TP',False
    return None


def opening_exit(position, bar):
    quote = bar[1] + (bar[5] if position['side']<0 else 0)
    if position['side']*(quote-position['stop']) <= 0:
        return quote,'SL gap',False
    if position['side']*(quote-position['target']) >= 0:
        return position['target'],'TP gap',False
    return None


def metrics(trades, cash, equity, daily, days, initial=10000.):
    pnl = np.array([t['net_usd'] for t in trades])
    win = pnl[pnl>1e-8]; loss = pnl[pnl<-1e-8]
    sw=sl=mw=ml=0
    for p in pnl:
        sw = sw+1 if p>1e-8 else 0
        sl = sl+1 if p<-1e-8 else 0
        mw,ml = max(mw,sw),max(ml,sl)
    daily_returns = np.diff(np.r_[initial,daily])/np.r_[initial,daily[:-1]]
    daily_std = daily_returns.std(ddof=1) if len(daily_returns)>1 else 0.
    dd = lambda a: float(np.max(1-np.array(a)/np.maximum.accumulate(a))*100)
    eq_daily = np.array([daily[0]/initial-1]+[daily[i]/daily[i-1]-1 for i in range(1,len(daily))])
    return dict(trades=len(trades),wins=len(win),losses=len(loss),
                win_rate_pct=float(100*len(win)/len(pnl)) if len(pnl) else None,
                profit_factor=float(win.sum()/(-loss.sum())) if len(loss) else None,
                return_pct=float((cash[-1]/initial-1)*100), final_balance_usd=float(cash[-1]),
                max_closed_dd_pct=dd(cash),max_m1_close_equity_dd_pct=dd(equity),
                sharpe_daily_365=float(daily_returns.mean()/daily_std*math.sqrt(365)) if daily_std>0 else None,
                max_win_streak=mw,max_loss_streak=ml,average_trades_per_calendar_day=len(trades)/days,
                days_reaching_2pct_equity_profit=int((eq_daily>=.02).sum()),
                mean_daily_equity_return_pct=float(eq_daily.mean()*100),
                roundtrip_ambiguities=sum(t['ambiguous'] for t in trades),
                average_net_r=float(np.mean([t['net_r'] for t in trades])) if trades else None,
                financing_usd=float(sum(t['swap_usd'] for t in trades)),
                extra_cost_usd=float(sum(t['extra_cost_usd'] for t in trades)),
                average_hold_minutes=float(np.mean([(t['exit_epoch']-t['entry_epoch'])/60 for t in trades])) if trades else None,
                overnights=sum(t['rollovers']>0 for t in trades))


def simulate(data, meta, symbols, start, target_first=False, stress=False):
    start_epoch = int(pd.Timestamp(start,tz='UTC').timestamp())
    frames = {s:data[s][(data[s][:,0]>=start_epoch)&(data[s][:,0]<END)] for s in symbols}
    times = np.unique(np.concatenate([a[:,0] for a in frames.values()])).astype(np.int64)
    dense = {}
    for s,a in frames.items():
        b = np.full((len(times),7),np.nan)
        b[np.searchsorted(times,a[:,0])] = a
        dense[s] = b
    specs = {s:meta['files'][s]['specification'] for s in symbols}
    days = (END-start_epoch)//86400
    daily = np.full(days,10000.)
    events = {s:Event() for s in symbols}
    positions, pending, last_marks = {}, {}, {}
    balance, cash, eq = 10000., [10000.], [10000.]
    trades, skips, budget_log = [],Counter(),[]
    new_count = 0; day = None; spent = 0.; budget = 0.
    max_leverage = 0.
    clock = pd.date_range(start,'2026-10-12',tz='UTC')
    rollovers = []
    for d in clock:
        if d.weekday()<5:
            rollover = pd.Timestamp(d.strftime('%Y-%m-%d')+' 17:00',tz='America/New_York').tz_convert('UTC')
            rollovers.append((int(rollover.timestamp()),d.weekday()+1))
    ri = 0

    def finish(symbol, price, reason, epoch, ambiguous=False):
        nonlocal balance
        p = positions.pop(symbol)
        spec = specs[symbol]
        gross = p['side']*(price-p['entry'])*p['lots']*spec['trade_contract_size']
        balance += gross-p['extra_cost_usd']
        p.update(exit=float(price),exit_epoch=int(epoch),exit_sequence=len(trades),exit_reason=reason,
                 net_usd=float(gross-p['extra_cost_usd']+p['swap_usd']),
                 net_r=float((gross-p['extra_cost_usd']+p['swap_usd'])/p['initial_risk_usd']),
                 ambiguous=p['ambiguous'] or ambiguous)
        trades.append(p)
        events[symbol].reset()
        cash.append(balance)

    for i,tm in enumerate(times):
        new_day = tm//86400
        if new_day != day:
            if day is not None:
                budget_log.append(dict(utc_day=int(day),budget=budget,spent=spent,new_entries=new_count))
            day = new_day; budget = max(0.,balance*.02)
            spent = sum(p['initial_risk_usd'] for p in positions.values()); new_count = 0
            for event in events.values(): event.reset()
        # Apply financing before that minute's new entries, never to new positions.
        while ri<len(rollovers) and rollovers[ri][0] <= tm:
            rt,wd = rollovers[ri]
            for s,p in positions.items():
                if p['entry_epoch'] < rt:
                    p['rollovers'] += 1
                    if stress:
                        spec = specs[s]
                        assert spec['swap_mode']==1
                        rate = spec['swap_long'] if p['side']>0 else spec['swap_short']
                        swap = rate*spec['point']*spec['trade_contract_size']*p['lots']*(3 if wd==spec['swap_rollover3days'] else 1)
                        balance += swap; p['swap_usd'] += swap
                        cash.append(balance)
            ri += 1
        # Exits observable at minute OPEN are available for subsequent sizing.
        for s in symbols:
            b=dense[s][i]
            if not math.isfinite(b[0]):continue
            last_marks[s]=(float(b[1]),float(b[5]))
            if s in positions:
                out=opening_exit(positions[s],b)
                if out:finish(s,out[0],out[1],tm,out[2])
        # All entries use cash BEFORE any current-minute high/low exit.
        for s in symbols:
            b=dense[s][i]
            if s not in pending:continue
            q=pending[s]
            if tm<q['ready']:continue
            if not math.isfinite(b[0]):
                if tm>q['ready']+60:pending.pop(s);skips['stale next quote']+=1
                continue
            pending.pop(s)
            if tm>q['ready']+60:skips['stale next quote']+=1;continue
            if s in positions:skips['existing position']+=1;continue
            if new_count>=4:skips['four entries per day']+=1;continue
            spec=specs[s]; side=q['side']; entry=float(b[1]+(b[5] if side>0 else 0))
            stop=q['stop']; distance=side*(entry-stop)
            if distance<=0:skips['invalid stop after gap']+=1;continue
            risk_per_lot=distance*spec['trade_contract_size']
            lots=min(spec['volume_max'],math.floor((balance*.005/risk_per_lot+1e-12)/spec['volume_step'])*spec['volume_step'])
            if lots<spec['volume_min']:skips['below minimum lot']+=1;continue
            risk=lots*risk_per_lot
            if spent+risk>budget+1e-8:skips['shared daily risk budget']+=1;continue
            target=round((entry+side*1.5*distance)/spec['trade_tick_size'])*spec['trade_tick_size']
            positions[s]=dict(symbol=s,side=side,entry=entry,stop=float(stop),target=float(target),
                              entry_epoch=int(tm),signal_epoch=int(q['ready']),signal_extreme=float(q['extreme']),
                              delta=float(q['delta']),signal_spread=float(q['spread']),
                              lots=float(round(lots,8)),initial_risk_usd=float(risk),entry_balance=float(balance),
                              extra_cost_usd=float(lots*spec['trade_contract_size']*b[5] if stress else 0.),
                              swap_usd=0.,rollovers=0,ambiguous=False,
                              initial_notional_leverage=float(lots*spec['trade_contract_size']*entry/balance))
            spent += risk; new_count += 1
        # Intrabar exits are now considered, without reusing future profits at OPEN.
        for s in symbols:
            b=dense[s][i]
            if not math.isfinite(b[0]):continue
            if s in positions:
                out=intrabar_exit(positions[s],b,target_first)
                if out:finish(s,out[0],out[1],tm+60,out[2])
            last_marks[s]=(float(b[4]),float(b[5]))
            if s not in positions and s not in pending:
                if not math.isfinite(b[6]) or b[6]<=0 or not math.isfinite(b[5]):
                    skips['unknown ATR or spread']+=1;continue
                signal=events[s].update(float(b[4]),float(b[6]))
                if signal:
                    side,extreme=signal
                    stop=extreme-specs[s]['trade_tick_size'] if side>0 else extreme+b[5]+specs[s]['trade_tick_size']
                    pending[s]=dict(side=side,stop=stop,extreme=extreme,delta=b[6],spread=b[5],ready=int(tm+60))
        floating=0.; notional=0.
        for s,p in positions.items():
            mark,spread=last_marks[s]
            quote=mark+(spread if p['side']<0 else 0)
            floating += p['side']*(quote-p['entry'])*p['lots']*specs[s]['trade_contract_size']
            notional += p['lots']*specs[s]['trade_contract_size']*mark
        equity=balance+floating
        if equity>0:max_leverage=max(max_leverage,notional/equity)
        cash.append(balance);eq.append(equity)
        daily[int((tm-start_epoch)//86400)]=equity
    if day is not None:budget_log.append(dict(utc_day=int(day),budget=budget,spent=spent,new_entries=new_count))
    # End-exclusive close uses only quote OPEN, never future OHLC.
    for s in list(positions):
        after=data[s][(data[s][:,0]>=END)&(data[s][:,0]<=END+120)]
        assert len(after),f'No terminal close quote for {s}'
        b=after[0];p=positions[s]
        quote=b[1]+(b[5] if p['side']<0 else 0)
        finish(s,float(quote),'Study end',int(b[0]))
    cash.append(balance);eq.append(balance);daily[-1]=balance
    # A prior bar's intrabar exit and next bar's opening-gap exit can share a timestamp.
    # Preserve causal booking order instead of reordering the cash path by asset name.
    trades.sort(key=lambda t:(t['exit_epoch'],t['exit_sequence']))
    # Fill days with no quote with previous marked equity, not $10,000.
    observed={int((tm-start_epoch)//86400) for tm in times}
    for d in range(1,days):
        if d not in observed:daily[d]=daily[d-1]
    summary=metrics(trades,cash,eq,daily,days)
    summary.update(max_gross_notional_leverage=float(max_leverage),skipped_signals=dict(skips),
                   days=days,quote_minutes=len(times),positions_left_open=len(positions))
    return dict(summary=summary,trades=trades,daily_equity=[float(v) for v in daily],
                daily_risk_audit=budget_log,start=start,end_exclusive='2026-10-13',symbols=symbols,
                scenario='cost/financing stress' if stress else 'target-first sensitivity' if target_first else 'spread-inclusive baseline')


def report(r):
    n=lambda v,d=2:'N/A' if v is None else f'{v:,.{d}f}'
    def table(cases):
        rows=[]
        for name,p in cases:
            q=p['summary']
            vals=[name,q['trades'],n(q['win_rate_pct'])+'%',n(q['profit_factor']),n(q['return_pct'])+'%',
                  n(q['max_closed_dd_pct'])+'%',n(q['max_m1_close_equity_dd_pct'])+'%',n(q['sharpe_daily_365']),
                  f'{q["max_win_streak"]} / {q["max_loss_streak"]}',n(q['average_trades_per_calendar_day']),
                  n(q['mean_daily_equity_return_pct'])+'%',q['days_reaching_2pct_equity_profit']]
            rows.append('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in vals)+'</tr>')
        return '<div class="scroll"><table><tr>'+''.join(f'<th>{h}</th>' for h in [
            'Account','Trades','Win rate','PF','Return','Closed DD','M1-close equity DD','Sharpe','Win/loss streak','Trades/day','Mean daily return','Days ≥+2%'])+'</tr>'+''.join(rows)+'</table></div>'
    sections=[]
    for key in ['1y','6m','3m']:
        cases=r['periods'][key]
        curves=[]
        for symbol in SYMBOLS+['shared']:
            values=[10000.]+cases[symbol]['daily_equity'];lo,hi=min(values),max(values)
            span=max(hi-lo,100.)
            points=' '.join(f'{10+i*780/max(1,len(values)-1):.1f},{190-(v-lo)*160/span:.1f}' for i,v in enumerate(values))
            curves.append(f'<div class="box"><h3>{NAMES[symbol]}</h3><p>$10,000 → ${n(values[-1])}</p><svg viewBox="0 0 800 220" role="img" aria-label="Daily marked equity"><polyline points="{points}" fill="none" stroke="#67f6bd" stroke-width="2"/><text x="10" y="214" fill="#cae3d8">{STARTS[key]}</text><text x="660" y="214" fill="#cae3d8">2026-10-12</text></svg></div>')
        sections.append(f'<section id="{key}" {"hidden" if key!="1y" else ""}><h2>{STARTS[key]} → 2026-10-13 exclusive</h2>'+table([(NAMES[s],cases[s]) for s in SYMBOLS+['shared']])+f'<div class="curves">{"".join(curves)}</div></section>')
    sensitivity=table([('Shared baseline',r['periods']['1y']['shared']),
                       ('Shared target-first',r['ordering_sensitivity']),('Shared cost / financing stress',r['cost_stress'])])
    rules=json.loads((ROOT/'PROTOCOL.json').read_text())
    trade_rows=[]
    for t in r['periods']['1y']['shared']['trades']:
        vals=[datetime.fromtimestamp(t['entry_epoch'],timezone.utc).isoformat(),NAMES[t['symbol']],
              'Buy' if t['side']>0 else 'Sell',n(t['entry'],3),n(t['stop'],3),n(t['target'],3),
              n(t['lots']),datetime.fromtimestamp(t['exit_epoch'],timezone.utc).isoformat(),
              t['exit_reason'],n(t['net_r']),n(t['net_usd'])]
        trade_rows.append('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in vals)+'</tr>')
    rows=[]
    for symbol in SYMBOLS+['shared']:
        q=r['periods']['1y'][symbol]['summary']
        rows.append(f'<tr><td>{NAMES[symbol]}</td><td>{n(q["max_gross_notional_leverage"])}×</td><td>{q["overnights"]}</td><td>{n(q["average_hold_minutes"])}</td><td>{html.escape(json.dumps(q["skipped_signals"]))}</td></tr>')
    rulelist=''.join(f'<p><b>{html.escape(k.replace("_"," "))}:</b> {html.escape(str(v))}</p>' for k,v in rules.items())
    doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>New idea 01 · price-event clock</title><style>
    body{{background:#071b15;color:#e4f2eb;font:16px system-ui;max-width:1450px;margin:auto;padding:25px}}h1,h2,h3,a{{color:#67f6bd}}p{{line-height:1.6}}.notice{{background:#302b17;border:1px solid #a58c38;padding:18px;border-radius:12px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #2b5043;white-space:nowrap}}th{{color:#67f6bd}}.curves{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}.box{{padding:15px;border:1px solid #2b5043;border-radius:12px}}svg{{width:100%}}select{{background:#0d2a20;color:white;padding:12px;border:1px solid #67f6bd}}summary{{padding:20px 0;cursor:pointer}}
    </style></head><body><p>IDEA 1 OF 4 · RAW RESEARCH · NOT DEPLOYED</p><h1>Price-event clock — BTC, gold and US100</h1>
    <div class="notice">The earlier agreement was <b>2% daily risk budget, not 2% daily profit</b>. This first version risks 0.5% per position and targets 1.5R. These are invented mechanical rules motivated by intrinsic-time research, not a proven strategy.</div>
    <p>Independent $10,000 accounts for each asset plus one genuinely shared three-asset account. Recorded M1 spreads included; zero explicit Pro commission and zero swap assumed in baseline. Financing entitlement/history is unverified; cost sensitivity below is essential. No optimisation, BAT, website, running EA or account changes.</p>
    <p><label>Period <select id="period"><option value="1y">Last year</option><option value="6m">Last six months</option><option value="3m">Last three months</option></select></label></p>{''.join(sections)}
    <p>Equity curves use minute-sampled position marks rolled into daily equity. M1-close DD is not tick-perfect worst floating DD. Cash DD includes any booked financing in the stress case. Sharpe uses calendar-day marked-equity returns ×√365 including no-trade days. Each selected window restarts $10,000; standalone returns are never summed to create the shared case.</p>
    <h2>Execution / financing sensitivity · one-year shared account</h2>{sensitivity}
    <p>Target-first is a sensitivity bound for same-minute SL/TP conflicts, not a tradable optimistic result. Stress adds one observed entry spread round trip and today's swap rates retrospectively, assumed weekday NY17:00 rollover; this is not measured historical financing. Broker margin, historical stop restrictions, latency, real tick sequences and liquidity are not modeled.</p>
    <h2>Risk, frequency and coverage</h2><div class="scroll"><table><tr><th>Account</th><th>Maximum gross leverage</th><th>Rollover-held trades</th><th>Average hold minutes</th><th>Blocked/invalid signals</th></tr>{''.join(rows)}</table></div>
    <p>The daily rule reserves initial stop risk of carried positions, allows no more than four new entries and no more than 2% of day-start closed balance in total committed initial risk. It does not recycle realised profits or losses into extra daily allowance. It is <b>not</b> a hard 2% equity-loss guarantee; gaps, spread changes and carry profits can alter daily floating loss.</p>
    <details><summary>All shared-account trades · one year · UTC</summary><div class="scroll"><table><tr><th>Entry UTC</th><th>Asset</th><th>Side</th><th>Entry</th><th>SL</th><th>TP</th><th>Lots</th><th>Exit UTC</th><th>Reason</th><th>R</th><th>USD</th></tr>{''.join(trade_rows)}</table></div></details>
    <details><summary>Frozen rules and assumptions</summary>{rulelist}</details>
    <h2>Next steps — awaiting owner review</h2><p>Only price-event clock tested. Next: BTC liquidation exhaustion, US100 constituent-participation reversal, then gold option-expiry release. No claims of full pipeline/OOS success: a subsequent pipeline must hold out the final two calendar years.</p>
    <p><a href="https://arxiv.org/abs/2406.07354">Intrinsic-time research</a> · <a href="https://get.exness.help/hc/en-us/articles/360011745839-Does-Exness-charge-fees-on-orders-held-overnight">Broker overnight-fee reference</a> · <a href="PROTOCOL.json">Frozen protocol</a> · <a href="RESULTS.json">All results and trades</a> · <a href="DATA.json">Data provenance</a></p>
    </body><script>document.getElementById('period').addEventListener('change',e=>document.querySelectorAll('section').forEach(s=>s.hidden=s.id!==e.target.value));</script></html>'''
    (ROOT/'Results.html').write_text(doc,encoding='utf-8')


def main():
    data,meta=prepare()
    result=dict(protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest(),
                engine_sha256=hashlib.sha256((ROOT/'run.py').read_bytes()).hexdigest(),data=meta,periods={})
    for period,start in STARTS.items():
        result['periods'][period]={}
        for name,symbols in [(s,[s]) for s in SYMBOLS]+[('shared',SYMBOLS)]:
            p=simulate(data,meta,symbols,start)
            result['periods'][period][name]=p
            print(json.dumps({'period':period,'case':name,**p['summary']}),flush=True)
    result['ordering_sensitivity']=simulate(data,meta,SYMBOLS,STARTS['1y'],target_first=True)
    print(json.dumps({'case':'ordering_sensitivity',**result['ordering_sensitivity']['summary']}),flush=True)
    result['cost_stress']=simulate(data,meta,SYMBOLS,STARTS['1y'],stress=True)
    print(json.dumps({'case':'cost_stress',**result['cost_stress']['summary']}),flush=True)
    save('RESULTS.json',result)
    report(result)


if __name__=='__main__':main()
