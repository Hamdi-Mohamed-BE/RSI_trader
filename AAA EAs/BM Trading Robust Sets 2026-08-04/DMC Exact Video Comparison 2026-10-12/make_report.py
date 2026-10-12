"""Transparent comparison from freshly matched native reports; no fabricated PF or win rate."""
from pathlib import Path
from datetime import datetime, timedelta
import gzip, hashlib, html, json, math, re, statistics

ROOT=Path(__file__).resolve().parent
LABELS={'OCT12_CUR':'Current DMC Gold','OCT12_FRX':'Fresh Reaction Gold',
        'OCT12_FRU':'Fresh Reaction US100','OCT12_BTCTRANSFER':'Fresh US100 rules on BTC (transfer only)',
        'OCT12_VIDEO':'New multi-timeframe reconstruction'}
ASSETS={'XAUUSD':'Gold','USTEC':'US100','BTCUSD':'BTC'}

def streaks(pnl):
    wins=losses=cw=cl=0
    for value in pnl:
        if value>0:cw+=1;cl=0;wins=max(wins,cw)
        elif value<0:cl+=1;cw=0;losses=max(losses,cl)
        else:cw=cl=0
    return wins,losses

def wilson(wins,n):
    if n==0:return [None,None]
    z=1.95996398454;p=wins/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    delta=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(100*(center-delta),2),round(100*(center+delta),2)]

def derived(row,trades):
    trades=sorted(trades,key=lambda t:(t['close_time'],t['number']))
    pnl=[t['net_profit'] for t in trades]
    net=round(sum(pnl),2)
    assert abs(net-row['metrics']['net_profit'])<0.11,(row['case'],net,row['metrics']['net_profit'])
    gain=sum(x for x in pnl if x>0);loss=-sum(x for x in pnl if x<0)
    win_count=sum(x>0 for x in pnl);loss_count=sum(x<0 for x in pnl)
    n=len(pnl);ws,ls=streaks(pnl)
    initial=row['metrics']['initial_balance'];balance=peak=initial;dd=0;curve=[initial]
    daily={};modules={}
    for t in trades:
        balance+=t['net_profit'];peak=max(peak,balance);dd=max(dd,(peak-balance)/peak*100)
        curve.append(round(balance,2))
        day=t['close_time'][:10];daily[day]=daily.get(day,0)+t['net_profit']
        comment=t['entry_comment'];module=modules.setdefault(comment,{'trades':0,'net_profit':0,'wins':0})
        module['trades']+=1;module['net_profit']+=t['net_profit'];module['wins']+=t['net_profit']>0
    start=datetime.strptime(row['start'],'%Y.%m.%d').date();end=datetime.strptime(row['end_exclusive'],'%Y.%m.%d').date()
    days=[];day=start
    while day<end:
        if row['symbol']=='BTCUSD' or day.weekday()<5:days.append(day)
        day+=timedelta(days=1)
    account=initial;returns=[]
    for day in days:
        cash=daily.get(day.isoformat(),0)
        returns.append(cash/account if account>0 else 0)
        account+=cash
    std=statistics.stdev(returns) if len(returns)>1 else 0
    sharpe=statistics.fmean(returns)/std*math.sqrt(365 if row['symbol']=='BTCUSD' else 252) if std>0 else None
    journal=gzip.decompress((ROOT/'native'/row['case']/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
    rejections=sorted(set(re.findall(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}[^\r\n]*ENTRY_REJECT[^\r\n]*)',journal)))
    counts=sorted(set(re.findall(r'DMC_MODULE_COUNTS trend=\d+ scalp=\d+ retest=\d+',journal)))
    for module in modules.values():
        module['net_profit']=round(module['net_profit'],2)
        module['win_rate_pct']=round(module['wins']/module['trades']*100,2)
    modification_failures=sorted(set(re.findall(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}[^\r\n]*failed modify[^\r\n]*)',journal)))
    return {'net_profit':net,'return_pct':round(net/initial*100,2),'trades':n,
            'profit_factor':round(gain/loss,3) if loss>0 else None,
            'profit_factor_note':'No net losing positions; PF undefined' if n>0 and loss==0 else 'No trades' if n==0 else '',
            'win_rate_pct':round(win_count/n*100,2) if n else None,'win_rate_wilson95_pct':wilson(win_count,n),
            'wins':win_count,'losses':loss_count,'flats':n-win_count-loss_count,
            'max_win_streak':ws,'max_loss_streak':ls,'max_closed_position_dd_pct':round(dd,2),
            'native_equity_dd_pct':row['metrics']['max_drawdown_pct'],
            'daily_closed_sharpe':round(sharpe,2) if sharpe is not None else None,
            'native_sharpe':row['metrics']['sharpe_ratio'],
            'native_pf':row['metrics']['profit_factor'],'native_win_rate_pct':row['metrics']['win_rate_pct'],
            'native_history_quality':row['metrics']['history_quality'],'trades_per_trading_day':round(n/len(days),2) if days else 0,
            'average_win_usd':round(gain/win_count,2) if win_count else None,
            'average_loss_usd':round(loss/loss_count,2) if loss_count else None,
            'average_trade_usd':round(net/n,2) if n else None,
            'commission_usd':round(sum(t['commission'] for t in trades),2),
            'swap_usd':round(sum(t['swap'] for t in trades),2),
            'entry_rejection_log_lines':rejections,'failed_stop_modification_unique_log_lines':len(modification_failures),
            'execution_note':'Native logs include market-closure order/BE modification failures; rejected requests are not assumed filled.',
            'native_logged_module_counts':counts,
            'modules':modules,'closed_curve':curve}

def fmt(value,digits=2):return '—' if value is None else f'{value:.{digits}f}'

def main():
    rows=[]
    for path in sorted((ROOT/'native').glob('dmcv-*/run.json')):
        native=json.loads(path.read_text())
        if not native.get('ok'):continue
        trades=json.loads(path.with_name('trades.json').read_text())
        assert len(trades)==native['metrics']['trades']
        rows.append({'case':native['case'],'label':LABELS[native['config']],'asset':ASSETS[native['symbol']],
                     'symbol':native['symbol'],'config':native['config'],'period':native['period'],'start':native['start'],
                     'end_exclusive':native['end_exclusive'],'native':native,'metrics':derived(native,trades)})
    periods=['3y','1y','6m','3m'];assets=['Gold','US100','BTC']
    rows.sort(key=lambda r:(periods.index(r['period']),assets.index(r['asset']),r['config']=='OCT12_VIDEO',r['label']))
    complete=len(rows)==28
    payload={'complete':complete,'completed_cases':len(rows),'expected_cases':28,
             'plan':json.loads((ROOT/'PLAN.json').read_text()),'build':json.loads((ROOT/'BUILD.json').read_text()),'rows':rows}
    (ROOT/'COMPARISON.json').write_text(json.dumps(payload,indent=2,allow_nan=False))
    parts=[]
    for row in rows:
        m=row['metrics'];new=row['config']=='OCT12_VIDEO'
        pf=fmt(m['profit_factor']) if m['profit_factor'] is not None else ('Undefined (no losses)' if m['trades'] else '—')
        css='new' if new else ''
        details=html.escape(json.dumps({k:v for k,v in m.items() if k!='closed_curve'},indent=2))
        parts.append(f"""<tr data-period="{row['period']}" data-asset="{row['asset']}" class="{css}"><td>{row['asset']}</td><td>{html.escape(row['label'])}</td><td>{m['trades']}</td><td>{m['return_pct']:+.2f}%</td><td>{pf}</td><td>{fmt(m['win_rate_pct'])}%</td><td>{m['native_equity_dd_pct']:.2f}%</td><td>{fmt(m['daily_closed_sharpe'])}</td><td>{m['max_win_streak']} / {m['max_loss_streak']}</td><td>{m['trades_per_trading_day']:.2f}</td><td>{html.escape(m['native_history_quality'])}</td></tr>
<tr data-period="{row['period']}" data-asset="{row['asset']}"><td colspan="11"><details><summary>Native evidence, costs, module breakdown and closed cash curve</summary><div class="curve" data-curve="{html.escape(json.dumps(m['closed_curve']))}"></div><pre>{details}</pre><a href="native/{row['case']}/trades.json">Trade-by-trade JSON</a> · <a href="native/{row['case']}/run.json">Native run checks</a></details></td></tr>""")
    page="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DMC Video Reconstruction — Native Comparison</title><style>
body{font:15px system-ui;background:#071914;color:#eafff3;max-width:1580px;margin:24px auto;padding:22px}p,li{line-height:1.6;color:#bcd3ca}h1{font-size:30px}.notice{border:1px solid #a68543;padding:16px;border-radius:14px;background:#242415}button,select{background:#12372b;color:#eafff3;border:1px solid #507b66;border-radius:9px;padding:10px;margin:4px}button.active{background:#8fe9bd;color:#05120c}.wide{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;border-bottom:1px solid #294e3d;padding:11px;white-space:nowrap}.new{background:#103126}details{margin:4px 0}pre{white-space:pre-wrap;max-height:600px;overflow:auto;font-size:13px}a{color:#9aefc2}.curve svg{width:100%;height:150px}#window{color:#9aefc2}summary{color:#bdd4c7;cursor:pointer}.hidden{display:none}
</style></head><body><h1>New multi-timeframe DMC vs existing DMCs</h1>
<p>Research-only reconstruction of <a href="https://www.youtube.com/watch?v=t9Bssop4uqo">Dumb Money Hunter’s DMC video</a>. Separate native MT5 tests, Exness-MT5Trial16 demo, $10,000 initial balance, 1% current-equity risk, 150ms execution delay. Live bots, BATs and portfolio membership were not changed.</p>
<div class="notice"><strong>Not the creator’s exact discretionary system.</strong> The video maps higher-timeframe levels and trades lower-timeframe reactions. Pivot strength, stops, entry confirmation, break-even and numerical settings were supplied by the approved reconstruction. One frozen configuration, no optimisation. Recent tests are separate fresh-$10k runs, not slices of the three-year result. Native real ticks begin 1 January 2026; older history uses generated ticks. This is not untouched OOS or completed pipeline validation.</div>
<p><strong>Completion: COMPLETE_TEXT</strong></p><div id="controls"><button data-p="3y" class="active">3 years</button><button data-p="1y">1 year</button><button data-p="6m">6 months</button><button data-p="3m">3 months</button><select id="asset"><option>All assets</option><option>Gold</option><option>US100</option><option>BTC</option></select></div><p id="window"></p>
<div class="wide"><table><thead><tr><th>Asset</th><th>EA / rules</th><th>Trades</th><th>Return</th><th>Net position PF</th><th>Net win rate</th><th>Max equity DD</th><th>Daily Sharpe</th><th>Win / loss streak</th><th>Trades/day</th><th>History quality</th></tr></thead><tbody>ROWS</tbody></table></div>
<h2>How the reconstruction works</h2><ul>
<li>Confirmed body pivots: two closed bars each side. W1/D1/H4 mapped zones and H1 trend-start proxies; no forming candle is used.</li>
<li>M15 trend-following rejection at H1 zones when D1/H1 structure agrees; counter-trend rejection scalps at W1/D1/H4 zones; M15 break/retest of the latest confirmed pivot, with eight-bar expiry.</li>
<li>Stop beyond zone and signal-bar extreme plus 0.1 M15 ATR(14). Nearest mapped level is the target; skip room below 0.25R. No fixed RR target or target optimisation.</li>
<li>Break-even at +0.5 initial R, broker permitting. No guarantee of a cost-free exit. One position at a time, all sessions, no daily trade cap or forced time exit.</li>
<li>Used zones rearm after price closes through the far edge. Daily/H1 structure uses completed-close breaks of already confirmed pivots.</li></ul>
<h2>Comparison limits and definitions</h2><p>Existing Gold controls retain their exact Asia settings, fixed 22.5/30 price-unit stops, 3R targets and Dynamic 50/20. US100 retains its New York configuration, 1.5 H1 ATR stop, 2R target and Dynamic 50/20. BTC has no active DMC: its control is an explicit transfer of the US100 rules, not a deployed bot. The new model differs in entry frequency, session, stops and exits; this tests a new strategy rather than attributing performance to one isolated filter.</p>
<p>Returns reconcile to native final balance. Net position PF, win rate and streaks use completed positions including opening/closing commissions and swap; PF is undefined when there are no net losses. MT5’s native deal-based PF is retained in the details and can differ. DD is native measured peak-to-trough equity DD. Daily Sharpe uses closed-position net returns on all weekdays for Gold/US100 (252 scaling) and all calendar days for BTC (365); it is not MT5’s native Sharpe or a floating-equity Sharpe. Streaks break on a flat trade. Trades/day divides by every eligible calendar/weekday in the window, including no-trade days.</p>
<p>Bid/ask execution, commission and swap are from native tester reports. New sizing floors lots; original controls retain upward rounding and can exceed nominal 1% slightly. Rejected-order logs remain visible, rather than assumed filled. Closed cash curves book each position’s costs at exit; they are not measured intraday equity curves. Historical last-bar forced test exits, if present, remain labelled in trade details. No extra cost stress, Monte Carlo or full promotion pipeline has been completed for this raw study.</p>
<script>const windows={"3y":"2023-10-12 → 2026-10-12","1y":"2025-10-12 → 2026-10-12","6m":"2026-04-12 → 2026-10-12","3m":"2026-07-12 → 2026-10-12"};let period="3y";function update(){const asset=document.querySelector('#asset').value;document.querySelectorAll('tr[data-period]').forEach(t=>t.classList.toggle('hidden',t.dataset.period!==period||(asset!=='All assets'&&t.dataset.asset!==asset)));document.querySelector('#window').textContent=windows[period]+" (end exclusive), separate native test for every row";document.querySelectorAll('button[data-p]').forEach(b=>b.classList.toggle('active',b.dataset.p===period));}document.querySelectorAll('button[data-p]').forEach(b=>b.onclick=()=>{period=b.dataset.p;update()});document.querySelector('#asset').onchange=update;document.querySelectorAll('[data-curve]').forEach(d=>{const v=JSON.parse(d.dataset.curve),lo=Math.min(...v),hi=Math.max(...v),r=Math.max(hi-lo,1),pts=v.map((x,i)=>(i/Math.max(v.length-1,1)*1000).toFixed(2)+','+(145-(x-lo)/r*135).toFixed(2)).join(' ');d.innerHTML='<svg viewBox="0 0 1000 150" preserveAspectRatio="none"><polyline points="'+pts+'" fill="none" stroke="#8fe9bd" stroke-width="2"/></svg>';});update();</script></body></html>"""
    page=page.replace('ROWS','\n'.join(parts)).replace('COMPLETE_TEXT',f'{len(rows)} / 28 native cases'+(' — all finished' if complete else ' — partial; runs in progress'))
    (ROOT/'Results.html').write_text(page,encoding='utf-8')
    for row in rows:
        if row['period']=='3y':print(row['asset'],row['label'],json.dumps({k:v for k,v in row['metrics'].items() if k in ['return_pct','trades','profit_factor','win_rate_pct','native_equity_dd_pct','daily_closed_sharpe','max_win_streak','max_loss_streak']}))
    print(f'Report: {len(rows)} / 28 native cases')

if __name__=='__main__':main()
