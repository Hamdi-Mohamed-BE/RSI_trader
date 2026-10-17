"""Report every grid outcome, including the final unfinished basket."""
import html
import run as r

ROOT=r.ROOT
def esc(x):return html.escape(str(x))
def f(x,d=2):return 'Not finite / no losses' if x is None else f'{x:,.{d}f}'
def utc(epoch):return r.n.pd.Timestamp(epoch,unit='s',tz='UTC').strftime('%Y-%m-%d %H:%M:%S')

def curves(q):
    trace=r.n.export_rows(ROOT/'native'/q['tag']/'trace.csv')
    a=int(trace[0]['epoch']);b=int(trace[-1]['epoch']);low=min(float(x['equity']) for x in trace);high=max(float(x['balance']) for x in trace)
    low=min(low,10000);high=max(high,max(float(x['equity']) for x in trace),10000);span=max(high-low,1)
    sampled=trace[::max(1,len(trace)//900)]
    if sampled[-1]!=trace[-1]:sampled.append(trace[-1])
    paths=[]
    for key,color in [('balance','#86edcb'),('equity','#ffbe74')]:
        points=' '.join(f'{62+890*(int(x["epoch"])-a)/max(b-a,1):.2f},{260-228*(float(x[key])-low)/span:.2f}' for x in sampled)
        paths.append('<polyline fill="none" stroke="'+color+'" stroke-width="1.8" points="'+points+'"/>')
    return '<svg viewBox="0 0 1000 320" role="img" aria-label="EURUSD grid account balance and floating equity by date"><text x="8" y="30">$'+f(high,0)+'</text><text x="8" y="263">$'+f(low,0)+'</text>'+''.join(paths)+'<text x="62" y="290">'+utc(a)[:10]+'</text><text x="855" y="290">'+utc(b)[:10]+'</text><text x="62" y="315" fill="#86edcb">Closed balance</text><text x="240" y="315" fill="#ffbe74">Floating equity</text></svg>'

def main():
    summary=r.n.read(ROOT/'SUMMARY.json');assert summary['completed']==2
    blocks=[];headline=[]
    for window,q in summary['results'].items():
        m=q['summary'];bs=m['baskets'];ps=m['positions'];natural=m['natural_baskets']
        headline.append('<tr><th>'+window+'</th><td>'+str(m['orders'])+'</td><td>'+str(bs['count'])+'</td><td>'+f(bs['win_rate'],1)+'%</td><td>'+f(bs['pf'])+'</td><td>'+f(m['return_pct'])+'%</td><td>'+f(m['equity_dd_pct'])+'%</td><td>'+f(m['sharpe_calendar_daily_equity'])+'</td></tr>')
        metrics=[('Final account balance',f(m['final_balance'])),('Net profit including forced closures',f(m['net_profit'])),
            ('Basket win / loss streak',str(bs['win_streak'])+' / '+str(bs['loss_streak'])),
            ('Individual-order win rate',f(ps['win_rate'],1)+'%'),('Individual-order PF',f(ps['pf'])),
            ('Natural target basket exits',str(natural['count'])),('Natural target exits: net cash',f(m['natural_net'])),
            ('Tester-end unfinished baskets',str(m['test_end_baskets'])),('Tester-end closure: net cash',f(m['test_end_net'])),
            ('Positions in terminal basket',str(m['terminal_orders'])),('Age of terminal basket (days)',f(m['terminal_duration_days'])),
            ('Longest basket duration (days)',f(m['max_basket_days'])),('Maximum concurrent positions',str(m['max_positions'])),
            ('Maximum simultaneous lots',f(m['max_lots'])),('Peak used margin USD (1:2000)',f(m['max_margin_usd'])),
            ('Worst account floating P/L USD',f(m['worst_floating_pnl'])),('Conservative equity drawdown USD',f(m['equity_dd_usd'])),
            ('Native MT5 equity DD',f(q['native']['equity_dd_pct'])+'% / $'+f(q['native']['equity_dd_usd'])),
            ('Tick-observer equity DD',f(q['instrumentation']['max_equity_dd_pct'])+'% / $'+f(q['instrumentation']['max_equity_dd_usd'])),
            ('Native closed-balance DD',f(m['balance_dd_pct'])+'%'),('Largest daily floating equity DD USD',f(m['max_daily_equity_dd_usd'])),
            ('Commission / swap / other fees USD',f(m['commission'])+' / '+f(m['swap'])+' / '+f(m['fee'])),
            ('Basket(s) with stopouts',str(m['stopout_baskets'])),('Rejected entry / close requests',str(int(q['instrumentation']['rejected_entries']))+' / '+str(int(q['instrumentation']['close_failures'])))]
        table=''.join('<tr><th>'+esc(k)+'</th><td>'+esc(v)+'</td></tr>' for k,v in metrics)
        rows=[]
        for b in q['baskets']:
            rows.append('<tr><td>'+str(b['id'])+'</td><td>'+b['side']+'</td><td>'+utc(b['open_epoch'])+'</td><td>'+utc(b['close_epoch'])+'</td><td>'+str(b['orders'])+'</td><td>'+f(b['total_lots'])+'</td><td>'+f(b['net'])+'</td><td>'+f(b['duration_days'])+'</td><td>'+b['reason']+'</td></tr>')
        folder='native/'+q['tag']
        blocks.append('<section class="window" data-window="'+window+'"><h2>'+('Last year' if window=='1y' else 'Three years')+' · '+esc(q['window'][0])+' → '+esc(q['window'][1])+' (end exclusive)</h2>'+curves(q)+
            '<div class="two"><table class="metrics">'+table+'</table><div><h3>History and interpretation</h3><p>'+esc(q['native']['history_quality'])+'. '+esc(' | '.join(q['tick_notes']))+'</p>'+
            '<p>The final basket was NOT closed by the $10 target. MT5 forcibly flattened it at the end of the requested test. Its full cost and loss remain in headline returns, PF and win rate. Without that liquidation its loss would remain floating; ignoring it would inflate results.</p>'+
            '<p>Basket win rate counts complete multi-order baskets, including terminal liquidations. Order win rate counts individual grid positions. They are different metrics. A basket system that normally exits only at a profit naturally reports a high basket win rate; this does not bound risk.</p>'+
            '<p>Balance/equity graph samples one-minute observations; drawdown maxima are measured separately on ticks. Native and before/after execution observer maxima can differ. The headline uses the higher observed DD, and preserves both values.</p>'+
            '<p>Daily DD is first available server-day tick-to-intraday peak-to-trough floating equity loss (UTC server), NOT a guaranteed daily loss limit. Sharpe uses sampled daily equity returns × √365, including no-trade calendar days and the final liquidation. No guard is added.</p>'+
            '<p><a href="'+folder+'/report.htm">Native MT5 report</a> · <a href="'+folder+'/inputs.set">Test settings</a> · <a href="'+folder+'/signals.csv">Signal audit CSV</a> · <a href="'+folder+'/deals.csv">All native deals CSV</a> · <a href="'+folder+'/results.json">Full basket/position details</a></p></div></div>'+
            '<details><summary>Every basket · '+str(len(q['baskets']))+' baskets</summary><div class="scroll"><table><thead><tr><th>ID</th><th>Side</th><th>Opened UTC</th><th>Closed UTC</th><th>Orders</th><th>Total lots</th><th>Net USD</th><th>Days held</th><th>Reason</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></details></section>')
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EURUSD EMA volume grid · raw reconstruction</title><style>
    :root{color-scheme:dark}*{box-sizing:border-box}body{background:#071912;color:#effbf6;font:15px/1.65 system-ui;margin:0}main{max-width:1450px;margin:auto;padding:32px 22px}h1{font-size:34px;line-height:1.2}h2{font-size:24px}p{color:#b4cdbf}a{color:#87f4cd}.notice{padding:18px;border:1px solid #987447;border-radius:12px;background:#292214}.eyebrow{color:#82e9c4;font-size:13px;letter-spacing:2px}nav{display:flex;gap:10px;margin:22px 0}button{padding:10px 16px;border:1px solid #49735f;color:#eafbf2;background:#173526;border-radius:8px;cursor:pointer}button.active{background:#82edc4;color:#092015}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #32513e;padding:10px;text-align:left;white-space:nowrap}thead{background:#153423}.metrics th{white-space:normal}.metrics{font-size:14px}.two{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin:20px 0}.window{margin:36px 0}.window svg{width:100%;max-height:430px}svg text{fill:#b4cdbf;font-size:13px}details{margin:22px 0;border:1px solid #32513e;padding:16px;border-radius:10px}summary{cursor:pointer}.hidden{display:none}.rules{max-width:1000px}@media(max-width:800px){.two{grid-template-columns:1fr}main{padding:22px 12px}h1{font-size:28px}.metrics{table-layout:fixed}.metrics td{white-space:normal;overflow-wrap:anywhere}}
    </style></head><body><main><div class="eyebrow">CALYX · TESTER ONLY · APPROVED RECONSTRUCTION</div><h1>EURUSD EMA5 + increasing-volume grid</h1>
    <p>One frozen parameter set, two independently funded raw tests. Starting balance $10,000; leverage 1:2000; native broker bid/ask, swaps, commission and 150ms execution delay. No optimisation or untouched-OOS claim.</p>
    <div class="notice">No stop-loss, no basket loss cap and no limit on grid depth. The approved 0.01 starting lot and +0.01 increments are NOT 1% risk sizing. High basket win rates can hide long-lived, much larger floating losses. This EA refuses live execution; no existing bots, BATs or website were changed.</div>
    <h2>Full-account results</h2><div class="scroll"><table><thead><tr><th>Window</th><th>Orders</th><th>Baskets</th><th>Basket win rate</th><th>Basket PF, net</th><th>Return</th><th>Max equity DD</th><th>Equity Sharpe</th></tr></thead><tbody>'''+''.join(headline)+'''</tbody></table></div>
    <p>Headline metrics include all positions and tester-end liquidations. Neither test is a shared portfolio or the original creator’s verified result.</p>
    <nav aria-label="Result period"><button class="active" data-period="1y">Last year</button><button data-period="3y">Three years</button><button data-period="all">Both</button></nav>'''+''.join(blocks)+'''
    <h2>Reconstructed rules</h2><div class="rules"><ol>
    <li>Completed M5 tick volumes must strictly increase: V[1] &gt; V[2] &gt; V[3]. Buy when the latest closed bar is above EMA5(close); sell below it. Both sides use increasing volume.</li>
    <li>One evaluation per newly completed candle. First fill occurs on the next available tick; stale pre-weekend bars are not used as fresh signals.</li>
    <li>One directional basket at a time. New same-side signals add only when the executable quote is at least 300 points from every existing entry. Absolute spacing permits additions in either price direction. On five-digit EURUSD this is 30 pips. Execution latency may change final fill spacing.</li>
    <li>Lots: 0.01, 0.02, 0.03, …, rounded down to broker step. No doubling formula or hidden maximum-order stop is invented.</li>
    <li>Close the entire basket at an estimated $10 net liquidation profit, reserving opening commission/fees again for expected exit costs. Market close slippage means realised cash need not equal exactly $10. No individual SL/TP, trailing or time exit.</li>
    <li>After the entire basket closes, seek the opposite side. An initial basket can start in either direction.</li>
    </ol><p>M5 timeframe, lot increment, cash target, completed-bar signal evaluation, absolute nearest-order spacing and forced alternation are explicit reconstruction choices, not recovered original code. Tick volume is broker tick activity, not consolidated FX traded volume.</p>
    <p>Implementation references: <a href="https://www.mql5.com/en/docs/indicators/ima">MetaQuotes EMA indicator</a>; <a href="https://www.mql5.com/en/docs/constants/environment_state/accountinformation">account equity, margin and stopout properties</a>. These references document implementation, not profitability.</p></div>
    <p><a href="EURUSD EMA Volume Grid Raw.mq5">Research source</a> · <a href="PLAN.json">Frozen plan</a> · <a href="PROTOCOL.txt">Research protocol</a> · <a href="SUMMARY.json">Full results</a> · <a href="VERIFICATION.json">Verification</a></p>
    </main><script>function select(p){document.querySelectorAll('[data-period]').forEach(b=>b.classList.toggle('active',b.dataset.period===p));document.querySelectorAll('[data-window]').forEach(x=>x.classList.toggle('hidden',p!=='all'&&x.dataset.window!==p));}document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>select(b.dataset.period)));select('1y');</script></body></html>'''
    (ROOT/'Results.html').write_text(page,encoding='utf-8')
    print('Report ready: 2/2 native grid windows')

if __name__=='__main__':main()
