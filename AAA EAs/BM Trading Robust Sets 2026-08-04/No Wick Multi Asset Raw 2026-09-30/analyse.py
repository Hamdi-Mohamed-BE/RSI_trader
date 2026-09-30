"""Deterministic post-processing of completed native runs, never starts MT5."""
from pathlib import Path
from datetime import datetime,timedelta
import json,gzip,math,html,re,hashlib
ROOT=Path(__file__).resolve().parent

def trade_statistics(trades,start,end,symbol):
    trades=sorted(trades,key=lambda t:t['close_time'])
    pnl=[t['net_profit'] for t in trades]
    wins=sum(x>0 for x in pnl);losses=sum(x<0 for x in pnl)
    pos=sum(x for x in pnl if x>0);neg=-sum(x for x in pnl if x<0)
    sequences=[];current=None;length=0
    for x in pnl:
        side='W' if x>0 else 'L' if x<0 else 'F'
        if side==current:length+=1
        else:
            if current is not None:sequences.append((current,length))
            current=side;length=1
    if current is not None:sequences.append((current,length))
    ws=[n for s,n in sequences if s=='W'];ls=[n for s,n in sequences if s=='L']
    a=datetime.strptime(start,'%Y.%m.%d').date();b=datetime.strptime(end,'%Y.%m.%d').date()
    days=(b-a).days
    sessions=days if symbol=='BTCUSD' else sum((a+timedelta(days=i)).weekday()<5 for i in range(days))
    n=len(pnl);p=wins/n if n else 0;z=1.959963984540054
    denom=1+z*z/n if n else 1
    centre=(p+z*z/(2*n))/denom if n else 0
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom if n else 0
    holds=[(datetime.fromisoformat(t['close_time'])-datetime.fromisoformat(t['open_time'])).total_seconds()/3600 for t in trades]
    return dict(trades=n,net_profit=round(sum(pnl),2),net_profit_factor=pos/neg if neg else None,
        net_win_rate_pct=100*p,wins=wins,losses=losses,flats=n-wins-losses,
        nominal_wilson95_pct=[100*(centre-radius),100*(centre+radius)] if n else None,
        trades_per_month=n/(days/30.4375),trades_per_day=n/max(1,sessions),day_denominator='calendar days' if symbol=='BTCUSD' else 'weekdays',
        avg_win_streak=sum(ws)/len(ws) if ws else 0,avg_loss_streak=sum(ls)/len(ls) if ls else 0,
        longest_win_streak=max(ws,default=0),longest_loss_streak=max(ls,default=0),
        average_net_trade=sum(pnl)/n if n else 0,commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),
        max_holding_hours=max(holds,default=0),overnight_trades=sum(t['open_time'][:10]!=t['close_time'][:10] for t in trades))

def collect():
    rows=[]
    for path in sorted((ROOT/'native').glob('nw-*/run.json')):
        r=json.loads(path.read_text())
        if not r.get('ok') or not r.get('audit',{}).get('ledger_reconciled'):continue
        trades=json.loads(gzip.decompress((path.parent/'trades.json.gz').read_bytes()))
        r['net']=trade_statistics(trades,r['start'],r['end_exclusive'],r['symbol'])
        r['artifact']=str(path.relative_to(ROOT)).replace('\\','/')
        signal_rows=set();roundup=set();stopouts=0
        with gzip.open(path.parent/'journal.txt.gz','rt',encoding='utf-8') as stream:
            for line in stream:
                if 'NW_SIGNAL ' in line:signal_rows.add(line.split('NW_SIGNAL ',1)[1].strip())
                if 'Risk sizing rounded ' in line:roundup.add(line.split('Risk sizing rounded ',1)[1].strip())
                if 'stop out' in line.lower() or 'stopout' in line.lower():stopouts+=1
        r['diagnostics']={
          'unique_order_signal_logs':len(signal_rows),
          'roundup_notice_lines':len(roundup),
          'stopout_log_lines':stopouts,
          'account_exhausted':r['metrics']['final_balance']<=0,
          'first_trade':min((t['open_time'] for t in trades),default=None),
          'last_trade':max((t['close_time'] for t in trades),default=None),
          'infrastructure_errors':r['journal_flags']['init_failed']+r['journal_flags']['critical']}
        rows.append(r)
    return rows

def raw_gate(symbol,variant,lookup,policy):
    reasons=[]
    for period in ('3y','5y'):
        r=lookup.get((symbol,variant,period));c=lookup.get((symbol,variant.replace('S','C'),period))
        if not r or not c:reasons.append(period+' incomplete');continue
        x=r['net']
        if x['net_profit']<=0:reasons.append(period+' net loss')
        if x['net_profit_factor'] is None or x['net_profit_factor']<policy['min_pf']:reasons.append(period+' net PF below '+str(policy['min_pf']))
        if x['trades']<policy['min_trades']:reasons.append(period+' insufficient trades')
        if x['net_profit']<=c['net']['net_profit']:reasons.append(period+' not better than control return')
    return dict(status='INCOMPLETE' if any('incomplete' in r for r in reasons) else 'FAIL' if reasons else 'RAW_PASS_REVIEW_REQUIRED',reasons=reasons)

def fmt(v,d=2):return 'n/a' if v is None else f'{v:.{d}f}'
def table(headers,rows):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table>'

def plot_summary(config,lookup):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    import numpy as np
    periods=config['main_periods'];matrix=config['matrix']
    data=np.array([[lookup[(s,v,p)]['net']['net_profit_factor'] or 0 for p in periods] for s,v in matrix])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
    fig,ax=plt.subplots(figsize=(10.5,8.3),facecolor='#101b24');ax.set_facecolor('#101b24')
    im=ax.imshow(data,cmap='RdYlGn',norm=TwoSlopeNorm(vmin=0,vcenter=1,vmax=2),aspect='auto')
    ax.set_xticks(range(len(periods)),['6 months','1 year','3 years','5 years'],color='white')
    ax.set_yticks(range(len(matrix)),[(('US100 CFD' if s=='USTEC' else s)+' M'+v[1:]) for s,v in matrix],color='white')
    ax.tick_params(length=0,pad=9);ax.xaxis.tick_top()
    for i,(s,v) in enumerate(matrix):
        for j,p in enumerate(periods):
            x=lookup[(s,v,p)]['net'];value=x['net_profit_factor']
            ax.text(j,i,f'{fmt(value)}  |  {x["net_win_rate_pct"]:.0f}%\nn={x["trades"]:,}',ha='center',va='center',color='#14232a',fontsize=10)
    ax.set_xticks(np.arange(-.5,len(periods),1),minor=True);ax.set_yticks(np.arange(-.5,len(matrix),1),minor=True)
    ax.grid(which='minor',color='#101b24',linewidth=2);ax.tick_params(which='minor',length=0)
    fig.suptitle('No-wick retest: net profit factor | net win rate',color='white',fontsize=17,y=.97)
    fig.text(.5,.915,'Native MT5 · $10,000 · 1% target risk · 1:1 target · no optimization',ha='center',color='#b7d1db',fontsize=10)
    fig.text(.5,.045,'Older windows include generated ticks. Lots round up; long-window losses may exhaust capital.\nA green cell is not validation: the raw gate also requires both long windows and control comparisons.',ha='center',color='#b7d1db',fontsize=9)
    for spine in ax.spines.values():spine.set_visible(False)
    fig.subplots_adjust(left=.23,right=.97,top=.86,bottom=.10)
    fig.savefig(ROOT/'comparison.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)

def main():
    config=json.loads((ROOT/'run-config.json').read_text());rows=collect()
    lookup={(r['symbol'],r['variant'],r['period']):r for r in rows}
    gates=[dict(symbol=s,variant=v,**raw_gate(s,v,lookup,config['gate'])) for s,v in config['matrix']]
    planned={(s,v,p) for s,v in config['matrix'] for p in config['main_periods']}|{(s,v.replace('S','C'),p) for s,v in config['matrix'] for p in config['control_periods']}
    missing=sorted(planned-set(lookup));complete=not missing
    if complete:plot_summary(config,lookup)
    out={'complete':complete,'planned_runs':len(planned),'completed_runs':len(planned&set(lookup)),
         'missing':missing,'gates':gates,'runs':rows,'source_sha256':hashlib.sha256((ROOT/config['source']).read_bytes()).hexdigest()}
    (ROOT/'ANALYSIS.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    conclusions=[]
    if complete:
        passed=sum(g['status']=='RAW_PASS_REVIEW_REQUIRED' for g in gates)
        annual=[lookup[(s,v,'1y')] for s,v in config['matrix']]
        best=max(annual,key=lambda r:r['net']['net_profit_factor'] or 0)
        wr=[r['net']['net_win_rate_pct'] for r in annual]
        conclusions=[f'{passed}/{len(gates)} versions passed the frozen raw screen.',
          f'One-year net win rates range from {min(wr):.1f}% to {max(wr):.1f}%, not approximately 90%.',
          f'Highest one-year net PF: {best["symbol"]} M{best["variant"][1:]} at {fmt(best["net"]["net_profit_factor"])}, return {best["metrics"]["return_pct"]:+.2f}%. This is a retrospective comparison, not a validated selection.',
          'No optimization or live deployment was performed.']
    sections=['<h2>Conclusion</h2><ul>'+''.join('<li>'+html.escape(c)+'</li>' for c in conclusions)+'</ul><img src="comparison.png" alt="Net profit factor and net win rate for every raw market and period">'] if complete else []
    markdown=['# Strict no-wick retest — native results','',f'Completed {out["completed_runs"]}/{len(planned)} planned runs. Smoke run reported separately, not in the screen.','',
      'Frozen raw rules; no optimization. Each asset/timeframe is tested separately: $10,000, 1% equity target risk, lots rounded UP, fixed 1:1. These are not combined-portfolio results. All P/L, win rates and PF below are NET of recorded commission and swap; native bid/ask spread is already in fill prices. Native return and max relative equity DD; broker: Exness-MT5Trial16. Cutoff 2026-09-30 exclusive.','',
      'US100 = USTEC CFD, not NQ futures. “No wick” and swing rules differ from the September-25 related test. Timeframes for gold/BTC were both declared before testing; do not treat the best retrospectively as validated.','',
      'No position time exit: some trades can last overnight/weekends. Pending expiry is 20 wall-clock timeframe durations. BTC frequency uses calendar days; others use weekdays. Overlapping windows are not independent tests.','']
    if conclusions:markdown+=['## Conclusion','']+['- '+c for c in conclusions]+['']
    headers=['Asset / TF','Return','Net PF','Net win','Eq DD','Trades','/month','/day','Avg W/L streak','Max W/L streak']
    for period in config['main_periods']:
        body=[]
        for s,v in config['matrix']:
            r=lookup.get((s,v,period))
            if not r:continue
            x=r['net'];m=r['metrics']
            body.append([s+' M'+v[1:],f'{m["return_pct"]:+.2f}%',fmt(x['net_profit_factor']),fmt(x['net_win_rate_pct'],1)+'%',fmt(m['max_relative_equity_dd_pct'])+'%',x['trades'],fmt(x['trades_per_month']),fmt(x['trades_per_day']),fmt(x['avg_win_streak'],1)+' / '+fmt(x['avg_loss_streak'],1),str(x['longest_win_streak'])+' / '+str(x['longest_loss_streak'])])
        sections.append('<h2>'+period+'</h2>'+table(headers,body))
        markdown+=['## '+period,'','| '+' | '.join(headers)+' |','|'+'---|'*len(headers)]+['| '+' | '.join(map(str,r))+' |' for r in body]+['']
    gatebody=[[g['symbol']+' M'+g['variant'][1:],g['status'],'; '.join(g['reasons']) or 'Raw screen only; needs user review'] for g in gates]
    sections.append('<h2>Frozen raw screen</h2>'+table(['Asset / TF','Result','Reason'],gatebody))
    markdown+=['## Frozen raw screen','','| Asset / TF | Result | Reason |','|---|---|---|']+['| '+' | '.join(r)+' |' for r in gatebody]+['']
    controls=[]
    for s,v in config['matrix']:
        for p in config['control_periods']:
            r=lookup.get((s,v.replace('S','C'),p))
            if not r:continue
            x=r['net'];m=r['metrics'];controls.append([s+' M'+v[1:],p,f'{m["return_pct"]:+.2f}%',fmt(x['net_profit_factor']),fmt(x['net_win_rate_pct'],1)+'%',fmt(m['max_relative_equity_dd_pct'])+'%',x['trades'],fmt(x['trades_per_month']),fmt(x['trades_per_day']),str(x['longest_win_streak'])+'/'+str(x['longest_loss_streak'])])
    ch=['Any-candle control','Period','Return','Net PF','Net win','Eq DD','Trades','/month','/day','Max W/L']
    sections.append('<h2>Any-candle controls</h2>'+table(ch,controls))
    markdown+=['## Any-candle controls','','| '+' | '.join(ch)+' |','|'+'---|'*len(ch)]+['| '+' | '.join(map(str,r))+' |' for r in controls]+['']
    quality=[]
    for r in rows:
        if r['period']=='smoke':continue
        x=r['net'];d=r['diagnostics'];quality.append([r['symbol']+' '+r['variant'],r['period'],r['metrics']['history_quality'],', '.join(r['real_tick_lines']),fmt(x['commission']),fmt(x['swap']),fmt(x['max_holding_hours'],1),r['journal_flags']['rejected'],d['unique_order_signal_logs'],d['last_trade'],'YES' if d['account_exhausted'] else 'no'])
    qh=['Run','Period','Reported quality','Real-tick start note','Commission $','Swap $','Max hold hours','Rejection log lines','Unique placement logs','Last closed trade','Balance exhausted']
    sections.append('<h2>Data and execution diagnostics</h2>'+table(qh,quality))
    markdown+=['## Data and execution diagnostics','','| '+' | '.join(qh)+' |','|'+'---|'*len(qh)]+['| '+' | '.join(map(str,r))+' |' for r in quality]+['']
    caveat='Older history may use generated ticks, even when Model 4 was requested. The quality/start notes below are per run. Rejection log lines can repeat between terminal and agent journals, including repeated cancellation attempts while a market is closed; expiry can be delayed until cancellation is accepted. Round-up sizing/minimum lots may exceed 1% and magnify drawdown. Some long-window accounts exhaust their balance before the end date: their trade frequencies use the entire requested window, and they do not represent continuous five-year trading. Positions may remain open overnight or over weekends; this is not a strictly flat-at-close day-trading system. These are historical simulations, not expected future returns or proof of a 90% win rate. A control comparison does not establish causality; markets, timeframes and overlapping samples create selection bias. No live deployment.'
    markdown+=['## Limitations','',caveat,'','[MetaTrader tick-generation documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).','',
      'Detailed ledgers, cost-aware metrics, nominal Wilson intervals (independence assumption), holding times and build identities: ANALYSIS.json. Broker costs are specific to this account/history, not generic FTMO costs.','']
    (ROOT/'REPORT.md').write_text('\n'.join(markdown),encoding='utf-8')
    style='body{background:#101b24;color:#e4edf5;font:15px system-ui;margin:36px}h1,h2{color:#8fffd3}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0 38px}th,td{border-bottom:1px solid #304353;text-align:right;padding:9px}td:first-child,th:first-child{text-align:left}th{color:#8fffd3}p{max-width:1050px;line-height:1.6}.warn{background:#45351f;padding:18px;border-radius:8px}a{color:#90d4ff}img{max-width:100%}'
    page='<html><head><meta charset="utf-8"><title>No-wick multi-asset test</title><style>'+style+'</style></head><body><h1>No-wick retest · raw multi-asset test</h1><p>'+str(out['completed_runs'])+'/72 native runs · $10,000 per separate simulation · 1% target risk · 1:1 target · cutoff September 30, 2026</p><p class="warn">'+html.escape(caveat)+'</p><p>Research only; not a combined portfolio. Trend = EMA50/200 with close agreement; strict flat wick; last causally confirmed 2+2 pivot; one setup at a time. Gold/BTC M5 & M15; US100 CFD M5; seven forex majors M15. See RULES.md for all assumptions.</p>'+''.join(sections)+'<p><a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation">Official tick-generation limitations</a></p></body></html>'
    (ROOT/'REPORT.html').write_text(page,encoding='utf-8')
    print(json.dumps({'complete':complete,'completed':out['completed_runs'],'planned':len(planned),'gates':gates},indent=2))
if __name__=='__main__':main()
