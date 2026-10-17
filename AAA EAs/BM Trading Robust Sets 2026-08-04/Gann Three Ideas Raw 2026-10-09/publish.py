"""Build complete/partial raw research report; never write production website."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, html, json, math, re, sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
END=pd.Timestamp('2026-10-09',tz='UTC')
PERIODS={'3y':'2023-10-09','first-year':'2023-10-09','2y':'2024-10-09','1y':'2025-10-09','6m':'2026-04-09','3m':'2026-07-09'}
CORE=['eighth-rejection','range-breakout','swing-fan','time-cycle']
COLORS=['#75f1c9','#fdc77c','#b1bbff','#fa99c4','#76cfed','#cad981','#a9bfb4']

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def f(v,n=2):return '—' if v is None else f'{v:,.{n}f}'
def stamp(t):return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def cash_stats(trades,balance):
    profits=[t['net'] for t in trades];wins=[p for p in profits if p>0];losses=[p for p in profits if p<0]
    opening=peak=balance;dd=0;w=l=mw=ml=0
    for profit in profits:
        balance+=profit;peak=max(peak,balance);dd=max(dd,100*(peak-balance)/peak)
        w=w+1 if profit>0 else 0;l=l+1 if profit<0 else 0;mw=max(mw,w);ml=max(ml,l)
    return dict(trades=len(trades),win_rate=100*len(wins)/len(trades) if trades else None,
        pf=sum(wins)/-sum(losses) if losses else None,return_pct=100*(balance/opening-1),net_profit=balance-opening,
        closed_dd_pct=dd,win_streak=mw,loss_streak=ml,avg_win=sum(wins)/len(wins) if wins else None,
        avg_loss=sum(losses)/len(losses) if losses else None,opening_balance=opening,closing_balance=balance)

def trace_for(result):
    frame=pd.read_csv(ROOT/'native'/result['tag']/'equity.csv',encoding='utf-8-sig')
    frame['epoch']=frame.epoch.astype('int64');frame['equity']=frame.equity.astype(float)
    frame=frame.drop_duplicates('epoch',keep='last').sort_values('epoch')
    return pd.Series(frame.equity.to_numpy(),index=pd.to_datetime(frame.epoch,unit='s',utc=True))

def slice_metrics(result,trace,start,end,btc):
    start=pd.Timestamp(start,tz='UTC');first=start.timestamp();last=end.timestamp()
    trades=[t for t in result['trades'] if first<=t['close_epoch']<last]
    opening=10000+sum(t['net'] for t in result['trades'] if t['close_epoch']<first)
    stats=cash_stats(trades,opening)
    within=trace[(trace.index>=start)&(trace.index<end)]
    points=pd.concat([pd.Series([opening],index=[start-pd.Timedelta(seconds=1)]),within])
    peaks=points.cummax();stats['sampled_equity_dd_pct']=float(((peaks-points)/peaks*100).max())
    days=pd.date_range(start,end-pd.Timedelta(days=1),freq='D')
    daily=within.resample('D').last().reindex(days).ffill().fillna(opening)
    if not btc:daily=daily[daily.index.weekday<5]
    returns=daily.pct_change();returns.iloc[0]=daily.iloc[0]/opening-1
    sd=returns.std(ddof=1)
    stats['sharpe']=float(math.sqrt(365 if btc else 252)*returns.mean()/sd) if sd>0 else None
    stats['trades_per_calendar_day']=len(trades)/(end-start).days
    stats['trades_per_market_day']=len(trades)/(len(days) if btc else sum(days.weekday<5))
    stats['start']=start.strftime('%Y-%m-%d');stats['end_exclusive']=end.strftime('%Y-%m-%d')
    stats['carry_in_trades']=sum(t['open_epoch']<first for t in trades)
    return stats,daily,returns

def metric_table(rows,key):
    body=''
    for row in rows:
        m=row['periods'][key]
        dd=m.get('native_equity_dd_pct',m['sampled_equity_dd_pct'])
        body+='<tr><td>'+html.escape(row['asset'])+'</td><td>'+html.escape(row['label'])+'</td>'
        body+=''.join('<td>'+f(v,d)+'</td>' for v,d in [(m['trades'],0),(m['win_rate'],1),(m['pf'],2),(m['return_pct'],2),(dd,2),(m['sharpe'],2)])
        body+='<td>'+str(m['win_streak'])+' / '+str(m['loss_streak'])+'</td></tr>'
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in ['Asset','Idea / control','Trades','Win %','PF','Return %','Equity DD %','Sharpe','Streak W/L'])+'</tr></thead><tbody>'+body+'</tbody></table></div>'

def curves(rows,title):
    series=[(r,r['daily_curve']) for r in rows if r['daily_curve']]
    if not series:return ''
    values=[v for r,c in series for t,v in c];low=min(0,min(values))-2;high=max(0,max(values))+2
    start=min(t for r,c in series for t,v in c);end=max(t for r,c in series for t,v in c)
    svg='<svg style="min-width:850px" viewBox="0 0 1050 330" role="img" aria-label="'+html.escape(title)+'"><title>'+html.escape(title)+'</title><desc>Daily mark-to-market equity return percent, independent accounts. Dashed lines are controls.</desc>'
    for i in range(5):
        y=20+62.5*i;value=high-i*(high-low)/4
        svg+=f'<line x1="70" x2="1020" y1="{y}" y2="{y}" stroke="#2b4c40"/><text x="4" y="{y+5}" fill="#b9cfc4" font-size="14">{value:.1f}%</text>'
    legend=[]
    for i,(row,curve) in enumerate(series):
        color=COLORS[i%len(COLORS)]
        points=' '.join(f'{70+(t-start)/(end-start)*950:.1f},{20+(high-v)/(high-low)*250:.1f}' for t,v in curve)
        dash=' stroke-dasharray="7 4"' if row['idea'] not in CORE else ''
        svg+=f'<polyline fill="none" stroke="{color}" stroke-width="2"{dash} points="{points}"/>'
        legend.append('<span style="color:'+color+'">'+html.escape(row['label'])+'</span>')
    svg+='<text x="70" y="318" fill="#b9cfc4">9 Oct 2023</text><text x="890" y="318" fill="#b9cfc4">8 Oct 2026</text></svg>'
    return '<div class="scroll">'+svg+'</div><p class="legend">'+' · '.join(legend)+'</p>'

def control_checks(rows,daily_returns):
    """Exploratory paired 7-day-block sign-flip and bootstrap diagnostics, not pass/fail certification."""
    tests=[];rng=np.random.default_rng(26100950)
    for asset in ['Gold','US100','Bitcoin']:
        for candidate,control in [('time-cycle','ema-baseline'),('time-cycle','random-cycle'),('eighth-rejection','quartile-control')]:
            ca=next((r for r in rows if r['asset']==asset and r['idea']==candidate and r['window']=='3y'),None)
            co=next((r for r in rows if r['asset']==asset and r['idea']==control and r['window']=='3y'),None)
            if not ca or not co:continue
            # Calendar-day series, including zero-return weekends, to preserve synchronized blocks.
            days=pd.date_range('2024-10-09','2026-10-08',tz='UTC',freq='D')
            left=daily_returns[ca['slug']].reindex(days).fillna(0).to_numpy()
            right=daily_returns[co['slug']].reindex(days).fillna(0).to_numpy()
            delta=left-right;n=len(delta);observed=float(delta.mean())
            blocks=[delta[i:i+7] for i in range(0,n,7)]
            block_sums=np.array([b.sum() for b in blocks])
            signs=rng.choice([-1,1],size=(5000,len(blocks)))
            null=signs@block_sums/n
            p=(1+np.sum(np.abs(null)>=abs(observed)))/5001
            starts=rng.integers(0,n,size=(5000,math.ceil(n/7)))
            indices=(starts[:,:,None]+np.arange(7)[None,None,:])%n
            boot=delta[indices.reshape(5000,-1)[:,:n]].mean(axis=1)
            low,high=np.percentile(boot,[2.5,97.5])
            tests.append(dict(asset=asset,candidate=ca['label'],control=co['label'],mean_daily_difference_pct=100*observed,
                bootstrap_95_interval_pct=[100*float(low),100*float(high)],raw_p=float(p),replications=5000,block_days=7))
    ordered=sorted(tests,key=lambda x:x['raw_p']);previous=0
    for i,t in enumerate(ordered):
        previous=max(previous,min(1,(len(ordered)-i)*t['raw_p']));t['holm_adjusted_p']=previous
    return tests

def main():
    plan=read(ROOT/'PLAN.json');state=read(ROOT/'RUN_STATUS.json');rows=[];returns={};checks=[]
    for case in plan['cases']:
        if case['slug'] not in state['complete']:continue
        result=read(Path(state['complete'][case['slug']]['path']));trace=trace_for(result)
        assert result['known_at_entry_verified'] and not any(result['flags'][k] for k in ['init_failed','runtime','history','stopout','invalid_volume','export_failed'])
        assert abs(sum(t['net'] for t in result['trades'])-result['native']['net_profit'])<.031
        periods={};curve=[]
        for key,start in (PERIODS.items() if case['window']=='3y' else [('2026','2026-01-01')]):
            end=pd.Timestamp('2024-10-09',tz='UTC') if key=='first-year' else END
            m,daily,ret=slice_metrics(result,trace,start,end,case['symbol']=='BTCUSD')
            if key in ['3y','2026']:
                m['native_equity_dd_pct']=result['native']['equity_dd_pct']
                assert abs(m['return_pct']-result['metrics']['return_pct'])<1e-5
            if key=='3y':curve=[[int(t.timestamp()),100*(value/10000-1)] for t,value in daily.items()]
            if key=='2y':
                # Controls use calendar-day mark-to-market returns, not weekday-only Sharpe returns.
                begin=pd.Timestamp(start,tz='UTC');opening=m['opening_balance']
                all_days=pd.date_range(begin,END-pd.Timedelta(days=1),freq='D')
                daily_all=trace[(trace.index>=begin)&(trace.index<END)].resample('D').last().reindex(all_days).ffill().fillna(opening)
                ret_all=daily_all.pct_change();ret_all.iloc[0]=daily_all.iloc[0]/opening-1;returns[case['slug']]=ret_all
            periods[key]=m
        annual=[]
        if case['window']=='3y':
            for year in [2023,2024,2025,2026]:
                year_start=max(pd.Timestamp(str(year)+'-01-01',tz='UTC'),pd.Timestamp('2023-10-09',tz='UTC'))
                year_end=min(pd.Timestamp(str(year+1)+'-01-01',tz='UTC'),END)
                a,_,_=slice_metrics(result,trace,year_start.strftime('%Y-%m-%d'),year_end,case['symbol']=='BTCUSD')
                annual.append(dict(year=year,partial=year in [2023,2026],**a))
        row=dict(slug=case['slug'],asset=case['asset'],symbol=case['symbol'],idea=case['idea'],label=case['label'],window=case['window'],
            periods=periods,daily_curve=curve,history_quality=result['native']['history_quality'],tick_notes=result['tick_notes'],
            native_end_liquidations=result['tester_end_liquidations'],diagnostics=result['diagnostics'],annual=annual,
            execution_rejections=result.get('execution_rejections',int(re.search(r' rejected=(\d+)',result['diagnostics'][0]).group(1))))
        rows.append(row)
        checks.append(dict(slug=case['slug'],cash_reconciliation=True,active_inputs_verified=True,known_at_entry=True,
            cost_inclusive=True,history_quality=row['history_quality'],native_end_liquidations=row['native_end_liquidations'],execution_rejections=row['execution_rejections']))
        with (ROOT/(case['slug']+'-trades.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
            fields=['position_id','side','volume','open_price','close_price','sl','tp','net','gross','commission','swap','fee']
            writer=csv.DictWriter(stream,['entry_utc','exit_utc',*fields,'feature_known_utc','signal_close_utc','planned_r','exit_reason']);writer.writeheader()
            sigs={x['position_id']:x['signal'] for x in result['signal_audit']}
            for t in result['trades']:
                sig=sigs[t['position_id']];entry=float(sig['requested_entry']);stop=float(sig['stop']);target=float(sig['target'])
                reason='TP' if any(c.lower().startswith('tp ') for c in t['exit_comments']) else ('SL' if any(c.lower().startswith('sl ') for c in t['exit_comments']) else ('TEST END' if any('end of test' in c.lower() for c in t['exit_comments']) else 'time close'))
                writer.writerow(dict(entry_utc=stamp(t['open_epoch']),exit_utc=stamp(t['close_epoch']),**{k:t[k] for k in fields},
                    feature_known_utc=stamp(int(sig['feature_known_epoch'])),signal_close_utc=stamp(int(sig['signal_close_epoch'])),
                    planned_r=abs(target-entry)/abs(entry-stop),exit_reason=reason))
    full=[r for r in rows if r['window']=='3y'];fresh=[r for r in rows if r['window']=='2026'];complete=len(rows)==42 and not state['failed']
    tests=control_checks(rows,returns) if complete else []
    sections=''
    for key,label in [('3y','Three years · 9 Oct 2023–8 Oct 2026'),('first-year','First-year descriptive segment · 9 Oct 2023–8 Oct 2024'),
                      ('2y','Final two-year validation segment · 9 Oct 2024–8 Oct 2026'),('1y','Last year · 9 Oct 2025–8 Oct 2026'),
                      ('6m','Last six months · 9 Apr–8 Oct 2026'),('3m','Last three months · 9 Jul–8 Oct 2026')]:
        sections+='<section class="panel" id="'+key+'"><h2>'+label+'</h2>'+metric_table(full,key)+'</section>'
    sections+='<section class="panel" id="fresh"><h2>Fresh-start 2026 · 1 Jan–8 Oct 2026</h2><p>Separate $10,000 accounts; same frozen rules. Native tester must confirm 100% real ticks before a case is admitted.</p>'+metric_table(fresh,'2026')+'</section>'
    charts=''.join('<section class="panel"><h2>'+asset+' · independent account curves</h2>'+curves([r for r in full if r['asset']==asset],asset+' Gann ideas and controls')+'</section>' for asset in ['Gold','US100','Bitcoin'])
    years='<div class="scroll"><table><tr><th>Asset</th><th>Idea / control</th><th>2023 partial %</th><th>2024 %</th><th>2025 %</th><th>2026 YTD %</th></tr>'
    for r in full:years+='<tr><td>'+r['asset']+'</td><td>'+r['label']+'</td>'+''.join('<td>'+f(a['return_pct'])+'</td>' for a in r['annual'])+'</tr>'
    years+='</table></div>'
    frequency='<div class="scroll"><table><tr><th>Asset</th><th>Idea / control</th><th>Trades/day</th><th>Average win $</th><th>Average loss $</th><th>Payoff ratio</th></tr>'
    for r in full:
        m=r['periods']['1y'];payoff=m['avg_win']/-m['avg_loss'] if m['avg_win'] is not None and m['avg_loss'] else None
        frequency+='<tr><td>'+r['asset']+'</td><td>'+r['label']+'</td>'+''.join('<td>'+f(v)+'</td>' for v in [m['trades_per_market_day'],m['avg_win'],m['avg_loss'],payoff])+'</tr>'
    frequency+='</table></div>'
    stats='<div class="scroll"><table><tr><th>Asset</th><th>Comparison</th><th>Daily difference %</th><th>95% block CI %</th><th>Holm-adjusted p</th></tr>'
    for t in tests:
        stats+='<tr><td>'+t['asset']+'</td><td>'+t['candidate']+' vs '+t['control']+'</td><td>'+f(t['mean_daily_difference_pct'],4)+'</td><td>'+f(t['bootstrap_95_interval_pct'][0],4)+' to '+f(t['bootstrap_95_interval_pct'][1],4)+'</td><td>'+f(t['holm_adjusted_p'],3)+'</td></tr>'
    stats+='</table></div>'
    downloads='<ul>'+''.join('<li><a href="'+r['slug']+'-trades.csv">'+r['asset']+' · '+r['label']+' · '+r['window']+'</a></li>' for r in rows)+'</ul>'
    failures='<ul>'+''.join('<li>'+html.escape(k)+': '+html.escape(v['error'])+'</li>' for k,v in state['failed'].items())+'</ul>'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gann three ideas · raw research</title><style>
    *{box-sizing:border-box}body{margin:0;background:#08160f;color:#ecf7f0;font:16px/1.6 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:30px 24px}h1{font-size:34px;line-height:1.2}h2{font-size:23px}p,li{color:#b3cdbf}a{color:#8cfcce}.tag{color:#8cfcce;font-size:13px;letter-spacing:2px}.warning{background:#272615;border:1px solid #95804b;padding:20px;border-radius:15px}.panel{border:1px solid #345742;border-radius:15px;padding:24px;margin:28px 0;background:#0d2016}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:14px}td,th{padding:11px;border-bottom:1px solid #325240;text-align:right}td:first-child,th:first-child,td:nth-child(2),th:nth-child(2){text-align:left}th{color:#94f5cf}svg{display:block;width:100%;height:auto}.legend{font-size:14px}summary{cursor:pointer;color:#98fad4}nav{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0}.small{font-size:13px}
    </style><main><div class="tag">CALYX · FROZEN RESEARCH · NO LIVE CHANGES</div><h1>Gann-inspired range boxes, fans and time cycles</h1><p>Gold (XAUUSD), US100 (Exness USTEC), Bitcoin (BTCUSD). Four tradable modes plus three controls per asset. $10,000 independent accounts, 0.5% current-balance nominal stop risk. Long and short. No optimisation or live deployment.</p>'''
    content+='<div class="warning">'+('Complete: ' if complete else 'IN PROGRESS: ')+str(len(rows))+' / 42 native cases. '+('No failed cases.' if not state['failed'] else 'Failed cases are excluded, not replaced with zero.')+'<br><br>These are mechanical adaptations, NOT an exact original Gann strategy. Pre-2026 history uses generated ticks from broker bars; three-year native quality is typically 25% real ticks. Fresh 2026 cases are verified separately at 100%. The last two years were not used to fit or select settings in this screen, but these markets/dates were previously explored in other research: not globally untouched OOS.</div>'
    content+='<nav>'+''.join('<a href="#'+key+'">'+label+'</a>' for key,label in [('3y','3 years'),('2y','2-year validation'),('1y','1 year'),('6m','6 months'),('3m','3 months'),('fresh','Fresh 2026')])+'</nav>'
    content+='<p>Full-run equity DD is the native tick-level maximum. Subperiod DD is sampled mark-to-market from the five-minute audit—not an exact tick-level subperiod maximum. Sharpe uses daily equity returns, zero risk-free rate, √365 for BTC and √252 weekdays for gold/US100. Subperiods retain their original account sizing and opening balance; they are slices, not new accounts.</p>'
    content+=sections+charts+'<section class="panel"><h2>Calendar-year returns</h2><p>2023 begins 9 October; 2026 ends 8 October. Closed whole-position cash returns relative to each year’s opening closed balance.</p>'+years+'</section>'
    content+='<details class="panel"><summary>Last-year frequency, average outcomes and payoff</summary><p>Trades/day uses calendar days for BTC and weekdays for gold/US100, including no-trade days; no holiday-calendar adjustment. Average win/loss includes all position costs and the original account’s compounding.</p>'+frequency+'</details>'
    content+='<section class="panel"><h2>Do the special levels or timing add anything?</h2><p>Exploratory paired daily-return comparisons on the final two years. Circular seven-calendar-day block bootstrap, 5,000 replicates; seven-day-block sign-flip tests with Holm adjustment across nine comparisons. One native randomized-clock control is a diagnostic, not broad proof. Portfolio capacity and timing can change trade eligibility, so gated native runs are not merely filtered baseline trades.</p>'+stats+'</section>'
    content+='<details class="panel"><summary>Frozen rules, clocks and assumptions</summary><ul>'+''.join('<li><strong>'+html.escape(k.replace('_',' '))+':</strong> '+html.escape(v)+'</li>' for k,v in plan['rules'].items())+'</ul><p>Gold uses M15, US100 M5, BTC M15 for box/fan signals; all cycle/control EMA entries use H1. ATR readings come only from the just-completed entry-timeframe candle. H4 pivot confirmation needs two later completed bars; entry is never backdated to the swing.</p><p>Gann documentation describes configurable price/time partitions and explicit scaling, not evidence that these defaults are profitable: <a href="'+plan['sources'][0]+'">TradingView price/time scale reference</a> · <a href="'+plan['sources'][1]+'">Gann box reference</a>.</p></details>'
    content+='<details class="panel"><summary>Native audits and all trade breakdowns</summary>'+downloads+'<p>Broker stop-distance rejections are recorded execution friction, not filled trades. The native signal counter gives unique rejected orders; repeated diagnostic matches across tester logs are not additional orders. Geometry/minimum-lot skips and failed orders remain excluded from the traded ledger.</p><ul>'+''.join('<li>'+r['asset']+' '+r['label']+' '+r['window']+': '+html.escape(r['history_quality'])+'; terminal-end closes: '+str(r['native_end_liquidations'])+'; unique rejected orders: '+str(r['execution_rejections'])+'; '+html.escape(r['diagnostics'][0])+'</li>' for r in rows)+'</ul></details>'
    if state['failed']:content+='<section class="panel"><h2>Failures—not results</h2>'+failures+'</section>'
    content+='<p class="small">Native spreads, commissions, swap, broker volume steps and 150 ms execution delay included. One successful trade per UTC day, separate accounts—not a shared portfolio. Nominal risk can be exceeded by costs/gaps/slippage. Test-end liquidations, if any, are explicitly counted above. No live EAs, BATs, portfolio selection, website or account settings changed.</p></main></html>'
    (ROOT/'Results.html').write_text(content,encoding='utf-8')
    save(ROOT/'SUMMARY.json',dict(plan=plan,rows=rows,control_diagnostics=tests,completed=len(rows),complete=complete,live_changes=False))
    save(ROOT/'VERIFICATION.json',dict(cases=checks,completed=len(rows),complete=complete,all_native_cash_reconciled=True,
        all_features_known_at_entry=True,real_tick_fresh_tests=len(fresh),live_changes=False))
    print(json.dumps(dict(completed=len(rows),total=42,failed=len(state['failed']),complete=complete)))
    if complete and '--verbose' in sys.argv:
        print(json.dumps([dict(asset=r['asset'],idea=r['label'],year=r['periods']['1y'],three_year=r['periods']['3y']) for r in full if r['idea'] in CORE],indent=2))

if __name__=='__main__':main()
