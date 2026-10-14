"""Frozen clock strategy, cost/neighborhood checks and joint null; no live writes."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
START,END='2020-01-01','2024-01-01'
ZONE='America/New_York'
WEEKDAYS=['Monday','Tuesday','Wednesday','Thursday','Friday']
TIMES=['10:00','10:05','10:10','10:15','10:20']


def save(name,value):
    (ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def load():
    meta=json.loads((ROOT/'DATA.json').read_text())
    path=ROOT/'US500-M1.npz'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['source_sha256']
    f=pd.DataFrame(np.load(path,allow_pickle=False)['rates'])
    # Match the microsecond unit of Timestamp/date_range. Otherwise pandas casts
    # and rebuilds the 1.3M-row lookup index for every six-row window.
    f.index=pd.DatetimeIndex(pd.to_datetime(f.time,unit='s',utc=True)).as_unit('us')
    assert f.index.is_unique and f.index.is_monotonic_increasing
    assert ((f.high>=f[['open','close','low']].max(axis=1)) &
            (f.low<=f[['open','close','high']].min(axis=1))).all()
    f['used_spread']=f.spread.where(f.spread>0).ffill()*meta['specification']['point']
    meta['zero_spread_rows']=int((f.spread<=0).sum())
    meta['unknown_initial_spread_rows']=int(f.used_spread.isna().sum())
    meta['median_positive_spread_points']=float(f.used_spread.median())
    return f,meta


def planned_entry(day,clock,zone=ZONE):
    return pd.Timestamp(f'{day} {clock}',tz=zone).tz_convert('UTC')


def window(f,day,clock,zone=ZONE):
    entry=planned_entry(day,clock,zone);exit=entry+pd.Timedelta(minutes=5)
    required=pd.date_range(entry,periods=6,freq='min')
    bars=f.reindex(required)
    if bars[['open','high','low','close']].isna().any().any():
        return dict(date=day,status='missing required quote-minute',entry_utc=entry.isoformat(),exit_utc=exit.isoformat())
    bid_entry,bid_exit=float(bars.open.iloc[0]),float(bars.open.iloc[-1])
    spread=float(bars.used_spread.iloc[0])
    gross=bid_exit-bid_entry
    return dict(date=day,status='available' if math.isfinite(spread) else 'unknown entry spread',
                entry_utc=entry.isoformat(),exit_utc=exit.isoformat(),
                entry_bid=bid_entry,entry_spread=spread if math.isfinite(spread) else None,
                entry_ask=bid_entry+spread if math.isfinite(spread) else None,exit_bid=bid_exit,
                gross_points=gross,net_points=gross-spread if math.isfinite(spread) else None,
                mae_points=min(0.,float(bars.low.iloc[:5].min())-bid_entry-spread,gross-spread) if math.isfinite(spread) else None,
                mfe_points=max(0.,float(bars.high.iloc[:5].max())-bid_entry-spread,gross-spread) if math.isfinite(spread) else None)


def summarize(records,cash_per_point,extra_cost=0.,gross=False,calendar_start=None,calendar_end=None):
    valid=[r for r in records if r.get('gross_points') is not None and (gross or r['net_points'] is not None)]
    if not valid:
        return dict(status='unavailable',scheduled=len(records),trades=None,win_rate_pct=None,
                    profit_factor=None,net_points=None,net_usd=None,return_pct=None,sharpe_daily_cash_252=None,
                    sharpe_weekly_trade_52=None,max_closed_dd_pct=None,max_win_streak=None,max_loss_streak=None)
    profits=np.array([(r['gross_points'] if gross else r['net_points'])-extra_cost for r in valid])*cash_per_point
    winners=profits[profits>1e-9];losers=profits[profits<-1e-9]
    zero=int((np.abs(profits)<=1e-9).sum())
    balances=np.r_[10000.,10000.+profits.cumsum()]
    if calendar_start and calendar_end:
        daily_index=pd.date_range(calendar_start,pd.Timestamp(calendar_end)-pd.Timedelta(days=1),freq='B')
    else:
        daily_index=pd.date_range(valid[0]['date'],valid[-1]['date'],freq='B')
    daily=np.zeros(len(daily_index))
    position={d.strftime('%Y-%m-%d'):i for i,d in enumerate(daily_index)}
    for r,p in zip(valid,profits):daily[position[r['date']]]+=p
    # A missing eligible trade cannot honestly be treated as a zero-return observation.
    unknown={r['date'] for r in records if r not in valid}
    daily=np.array([v for d,v in zip(daily_index,daily) if d.strftime('%Y-%m-%d') not in unknown])
    daily_std=daily.std(ddof=1) if len(daily)>1 else 0.
    trade_std=profits.std(ddof=1) if len(profits)>1 else 0.
    sw=sl=mw=ml=0
    for p in profits:
        sw=sw+1 if p>1e-9 else 0;sl=sl+1 if p<-1e-9 else 0
        mw,ml=max(mw,sw),max(ml,sl)
    z=1.959963984540054;n=len(profits);rate=len(winners)/n
    center=(rate+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
    return dict(status='available' if len(valid)==len(records) else 'partial eligible-session coverage',
                scheduled=len(records),trades=len(valid),missing=len(records)-len(valid),wins=len(winners),
                losses=len(losers),breakeven=zero,win_rate_pct=100*rate,win_rate_95pct_wilson=[100*(center-half),100*(center+half)],
                profit_factor=float(winners.sum()/(-losers.sum())) if len(losers) else None,
                net_points=float(profits.sum()/cash_per_point),net_usd=float(profits.sum()),
                return_pct=float(profits.sum()/10000*100),final_balance_usd=float(balances[-1]),
                mean_trade_points=float(profits.mean()/cash_per_point),
                mean_win_points=float(winners.mean()/cash_per_point) if len(winners) else None,
                mean_loss_points=float(losers.mean()/cash_per_point) if len(losers) else None,
                sharpe_daily_cash_252=float(daily.mean()/daily_std*math.sqrt(252)) if daily_std>0 else None,
                sharpe_weekly_trade_52=float(profits.mean()/trade_std*math.sqrt(52)) if trade_std>0 else None,
                daily_sharpe_observations=len(daily),max_closed_dd_pct=float((1-balances/np.maximum.accumulate(balances)).max()*100),
                max_win_streak=mw,max_loss_streak=ml,first_trade=valid[0]['date'],last_trade=valid[-1]['date'],
                extra_cost_points=extra_cost,executable=not gross)


def joint_null(day_windows):
    common=[d for d,ws in day_windows.items() if all(w['status']=='available' for w in ws)]
    weekdays=np.array([pd.Timestamp(d).weekday() for d in common])
    gross=np.array([[w['gross_points'] for w in day_windows[d]] for d in common])
    cost=np.array([[w['entry_spread'] for w in day_windows[d]] for d in common])
    rng=np.random.default_rng(20261014)
    signs=rng.choice(np.array([-1.,1.]),size=(5000,len(common)))
    all_scores=[];labels=[];observed=[];primary_scores=None;primary_observed=None;primary_n=None
    for wd in range(5):
        mask=weekdays==wd;g=gross[mask];c=cost[mask];n=len(g)
        for k,clock in enumerate(TIMES):
            x=g[:,k]-c[:,k]
            sd=x.std(ddof=1)
            actual=float(x.mean()/sd*math.sqrt(52)) if sd>0 else 0.
            # Random sign is shared for all same-day windows; friction stays negative.
            summed=signs[:,mask]@g[:,k]-c[:,k].sum()
            summed_sq=(g[:,k]**2+c[:,k]**2).sum()-2*(signs[:,mask]@(g[:,k]*c[:,k]))
            means=summed/n
            std=np.sqrt(np.maximum(0,(summed_sq-n*means**2)/(n-1)))
            scores=np.divide(means,std,out=np.zeros_like(means),where=std>0)*math.sqrt(52)
            all_scores.append(scores);labels.append(f'{WEEKDAYS[wd]} {clock}');observed.append(actual)
            if wd==3 and clock=='10:10':primary_scores=scores;primary_observed=actual;primary_n=n
    matrix=np.array(all_scores).T;maximum=matrix.max(axis=1)
    return dict(method='Joint same-day sign-flip null of gross changes, spreads always subtracted',
                simulations=5000,seed=20261014,neighborhood_configurations=25,
                common_days=len(common),matched_primary_trades=int(primary_n),
                matched_primary_weekly_sharpe=primary_observed,
                fixed_candidate_one_sided_p=float((1+(primary_scores>=primary_observed).sum())/5001),
                family_maximum_one_sided_p=float((1+(maximum>=primary_observed).sum())/5001),
                fake_family_best_sharpe_median=float(np.median(maximum)),
                fake_family_best_sharpe_95pct=float(np.quantile(maximum,.95)),
                primary_null_sharpes=primary_scores.tolist(),family_max_null_sharpes=maximum.tolist(),
                observed_matched_neighbors=dict(zip(labels,observed)),
                limitation='Tests 25 named neighbors, not the original unspecified 8500 configurations. Conditional sign symmetry is a null assumption; this is not proof of absence/presence of every market edge.')


def report(r):
    n=lambda v,d=2:'N/A' if v is None else f'{v:,.{d}f}'
    def row(name,q):
        vals=[name,q['trades'],n(q['win_rate_pct'])+'%',n(q['profit_factor']),n(q['net_points']),
              n(q['return_pct'])+'%',n(q['max_closed_dd_pct'])+'%',n(q['sharpe_daily_cash_252']),
              n(q['sharpe_weekly_trade_52']),f'{q["max_win_streak"]} / {q["max_loss_streak"]}']
        return '<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in vals)+'</tr>'
    headers='<tr>'+''.join(f'<th>{x}</th>' for x in ['Period / case','Trades','Win rate','PF','Net points','Return','Closed DD','Daily Sharpe','Trade Sharpe','Win/loss streak'])+'</tr>'
    yearly=''.join(row(str(y),r['yearly'][str(y)]) for y in range(2020,2024))
    costs=''.join(row(name,r['cases'][key]) for name,key in [('Gross / non-executable','gross'),('Recorded spread','baseline'),('Spread +0.60 point','cost_stress'),('Spread +1.10 points','severe_stress')])
    ledger=[]
    for t in r['primary_records']:
        vals=[t['date'],t['status'],t['entry_utc'],t['exit_utc'],n(t.get('entry_ask')),
              n(t.get('exit_bid')),n(t.get('entry_spread')),n(t.get('net_points')),
              n(t.get('mae_points')),n(t.get('mfe_points'))]
        ledger.append('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in vals)+'</tr>')
    neighborhood=[]
    for wd in range(5):
        cells=[]
        for clock in TIMES:
            q=r['neighbors'][f'{WEEKDAYS[wd]} {clock}']
            style=' class="primary"' if wd==3 and clock=='10:10' else ''
            cells.append(f'<td{style}>PF {n(q["profit_factor"])}<br>Sharpe {n(q["sharpe_daily_cash_252"])}<br>Win {n(q["win_rate_pct"])}%<br>{q["trades"]} trades</td>')
        neighborhood.append(f'<tr><th>{WEEKDAYS[wd]}</th>{"".join(cells)}</tr>')
    points=[10000.];dates=[]
    for t in r['primary_records']:
        if t.get('net_points') is not None:
            points.append(points[-1]+t['net_points']*r['cash_per_point']);dates.append(t['date'])
    lo,hi=min(points),max(points);span=max(hi-lo,1.)
    curve=' '.join(f'{20+i*960/max(1,len(points)-1):.1f},{250-(v-lo)*200/span:.1f}' for i,v in enumerate(points))
    q=r['cases']['baseline'];null=r['null_test']
    warn=('All four years have price data. ' if all(r['data']['yearly_bars'][str(y)] for y in range(2020,2024)) else 'Some requested years have no source prices. ')
    warn+=f'{q["trades"]} of {q["scheduled"]} scheduled Thursday windows are cost-assessable; {q["missing"]} are unavailable.'
    doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>US500 Thursday five-minute raw test</title><style>
    body{{font:16px system-ui;background:#081a16;color:#e6f1ea;max-width:1450px;margin:auto;padding:28px}}h1,h2,a{{color:#74f1bf}}p{{line-height:1.6}}.notice{{background:#302e1b;border:1px solid #a89243;border-radius:12px;padding:18px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #2c5043;white-space:nowrap}}th{{color:#74f1bf}}.primary{{background:#183e30;border:1px solid #74f1bf}}svg{{width:100%;background:#0d241c}}summary{{cursor:pointer;padding:20px 0}}.box{{border:1px solid #2c5043;padding:16px;border-radius:12px}}
    </style></head><body><p>RAW REPRODUCTION · RESEARCH ONLY · NO DEPLOYMENT</p><h1>Thursday 10:10 → 10:15 · US500</h1><p>2020-01-01 → 2024-01-01 exclusive, New York time with DST. Buy one fixed US500 CFD lot at 10:10, sell at 10:15, no stop or target. Dollar conversion: ${n(r['cash_per_point'])}/index point; $10,000 reference starting balance.</p>
    <div class="notice">This is the user-approved MT5 S&P 500 CFD equivalent, <b>not CME ES futures</b>. No original ES statistics, contract rolls or claimed 8,500-search results are reproduced. No stop-defined percentage risk or 1.5R target has been added.<br>{warn}</div>
    <h2>Year-by-year · recorded-spread case</h2><div class="scroll"><table>{headers}{yearly}{row('Combined 2020–2023',q)}</table></div>
    <p>Win-rate 95% Wilson interval: {n(q['win_rate_95pct_wilson'][0])}%–{n(q['win_rate_95pct_wilson'][1])}%. Mean net trade: {n(q['mean_trade_points'],4)} index points. Longest winning/losing streak: {q['max_win_streak']} / {q['max_loss_streak']}.</p>
    <h2>Closed balance · fixed one CFD lot</h2><svg viewBox="0 0 1000 290" role="img" aria-label="Chronological closed-balance curve"><polyline points="{curve}" fill="none" stroke="#74f1bf" stroke-width="3"/><text x="20" y="280" fill="#bedacc">2020</text><text x="900" y="280" fill="#bedacc">2023</text></svg><p>$10,000 → ${n(q['final_balance_usd'])}. Closed DD is not floating DD. Intratrade M1 excursions are shown in the ledger, not used for risk sizing.</p>
    <h2>Costs · all years</h2><div class="scroll"><table>{headers}{costs}</table></div><p>The extra 0.60-point case models two ES ticks <b>total</b> (0.50 points) plus a hypothetical 0.10-point commission equivalent; 1.10 points models two ES ticks <b>per side</b>. These are price-friction assumptions, not actual CFD fees. Historical recorded M1 spread is not tick-level bid/ask execution. Primary assumes zero explicit Pro commission and excludes latency and execution rejection modeling.</p>
    <h2>Does it survive next door?</h2><p>Every cell: same five-minute long hold, no fitting. Highlighted cell remains the externally specified primary regardless of this table's ranking.</p><div class="scroll"><table><tr><th>Weekday</th>{''.join(f'<th>{clock} NY</th>' for clock in TIMES)}</tr>{''.join(neighborhood)}</table></div>
    <h2>Time-zone ambiguity</h2><p>Thursday 10:10 Chicago = 11:10 New York. Its separate sensitivity result is not substituted for the primary.</p><div class="scroll"><table>{headers}{row('10:10 Chicago',r['chicago_sensitivity'])}</table></div>
    <h2>Does it beat a zero-direction null?</h2><div class="box"><p>5,000 fake markets, shared random sign per day across all five time windows, preserving within-day correlation. Positive spreads are subtracted even when the price move is sign-flipped.</p><p>Matched primary: {null['matched_primary_trades']} Thursday trades; weekly trade Sharpe {n(null['matched_primary_weekly_sharpe'])}. One-sided candidate p: {n(null['fixed_candidate_one_sided_p'],4)}. Neighborhood-maximum p: {n(null['family_maximum_one_sided_p'],4)}. Median best fake-neighborhood Sharpe: {n(null['fake_family_best_sharpe_median'])}; 95th percentile: {n(null['fake_family_best_sharpe_95pct'])}.</p><p><b>This uses 25 predeclared neighboring rules, not 8,500.</b> It assumes conditional sign symmetry; it does not recreate the video's undocumented strategy grid, market-scrambling method or prior selection. No definitive full-search-adjusted edge claim is made.</p></div>
    <h2>Lookahead and OOS checks</h2><p>Fills use entry/exit minute <b>OPEN</b> quotes, never the day's close, a future indicator, or the entry minute's later close. Highs/lows are only post-trade descriptive excursions. 2024–2025 is not queried for results: the requested 2020–2023 window is a retrospective reproduction, not claimed untouched OOS or a full pipeline pass.</p>
    <details><summary>Every scheduled Thursday · UTC fills</summary><div class="scroll"><table><tr><th>Date</th><th>Status</th><th>Entry UTC</th><th>Exit UTC</th><th>Entry ask</th><th>Exit bid</th><th>Spread</th><th>Net points</th><th>MAE points</th><th>MFE points</th></tr>{''.join(ledger)}</table></div></details>
    <p>Source: {r['data']['rows']:,} broker M1 bars, {html.escape(r['data']['server'])}, {html.escape(r['data']['first'])} to {html.escape(r['data']['last'])}. No price interpolation or future backfill.</p>
    <p><a href="RESULTS.json">Full results / null simulations</a> · <a href="PROTOCOL.json">Frozen rules</a> · <a href="DATA.json">Source receipt</a> · <a href="https://www.cmegroup.com/education/courses/introduction-to-futures/tick-movements-understanding-how-they-work">CME tick-size reference</a></p></body></html>'''
    (ROOT/'Results.html').write_text(doc,encoding='utf-8')


def main():
    f,meta=load();days=[d.strftime('%Y-%m-%d') for d in pd.date_range(START,'2023-12-31',freq='B')]
    print('Source validated; evaluating frozen clock windows.',flush=True)
    day_windows={d:[window(f,d,t) for t in TIMES] for d in days}
    records=[ws[2] for d,ws in day_windows.items() if pd.Timestamp(d).weekday()==3]
    cpp=meta['specification']['trade_contract_size']
    cases={key:summarize(records,cpp,cost,gross,START,END) for key,cost,gross in
           [('gross',0.,True),('baseline',0.,False),('cost_stress',.60,False),('severe_stress',1.10,False)]}
    neighbors={f'{WEEKDAYS[wd]} {clock}':summarize([ws[k] for d,ws in day_windows.items() if pd.Timestamp(d).weekday()==wd],cpp,calendar_start=START,calendar_end=END)
               for wd in range(5) for k,clock in enumerate(TIMES)}
    chicago=[window(f,d,'10:10','America/Chicago') for d in days if pd.Timestamp(d).weekday()==3]
    r=dict(data=meta,cash_per_point=cpp,cases=cases,primary_records=records,neighbors=neighbors,
           yearly={str(y):summarize([t for t in records if t['date'].startswith(str(y))],cpp,calendar_start=f'{y}-01-01',calendar_end=f'{y+1}-01-01') for y in range(2020,2024)},
           chicago_sensitivity=summarize(chicago,cpp,calendar_start=START,calendar_end=END),chicago_records=chicago,
           null_test=joint_null(day_windows),
           protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest(),
           engine_sha256=hashlib.sha256((ROOT/'run.py').read_bytes()).hexdigest())
    save('RESULTS.json',r);report(r)
    print(json.dumps({k:r[k] for k in ['cases','yearly','chicago_sensitivity']},indent=2))
    print(json.dumps({k:v for k,v in r['null_test'].items() if 'sharpes' not in k and 'neighbors' not in k},indent=2))


if __name__=='__main__':main()
