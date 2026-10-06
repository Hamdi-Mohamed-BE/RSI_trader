"""Reconcile frozen UK100 raw runs; render offline shared-account results."""
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import collections,gzip,hashlib,html,json
import run
R=run.R
WINDOWS={'1Y':('2025-10-04','2026-10-04','4 Oct 2025–3 Oct 2026'),
         '3M':('2026-07-04','2026-10-04','4 Jul–3 Oct 2026')}
COLORS={1:'#84f5c5',2:'#87b8ff',3:'#e7adfa'}
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def esc(v):return html.escape(str(v))
def num(v,n=2):return 'N/A' if v is None else f'{v:,.{n}f}'
def money(v):
    if v is None:return 'N/A'
    return ('−' if v<0 else '+' if v>0 else '')+'$'+f'{abs(v):,.2f}'
def table(head,rows):
    def row(v,tag='td'):return '<tr>'+''.join(f'<{tag}>'+esc(x)+f'</{tag}>' for x in v)+'</tr>'
    return '<div class="scroll"><table><thead>'+row(head,'th')+'</thead><tbody>'+''.join(row(r) for r in rows)+'</tbody></table></div>'
def parser_test():
    rows=[
      ['2026.09.07 10:00:00','2','UK100','buy','in','1','100','2','-0.50','0','0','9999.50','UKT20260907_M1'],
      ['2026.09.07 10:00:00','3','UK100','buy','in','2','100','3','-1.00','0','0','9998.50','UKT20260907_M2'],
      ['2026.09.07 11:00:00','4','UK100','sell','out','2','98','4','0','0','-4.00','9994.50','sl 98'],
      ['2026.09.07 12:00:00','5','UK100','sell','out','1','101','5','0','0','1.00','9995.50','tp 101']]
    body='<b>Deals</b>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in row)+'</tr>' for row in rows)
    log='\n'.join(f'UKT_DEAL_MAP deal={d} position={p} order={d} entry={e}' for d,p,e in [(2,100,0),(3,101,0),(4,101,1),(5,100,1)])
    with patch.object(run.h,'_read_report',return_value=body):
        ts,ledger=run.exact_trades(Path('fixture.htm'),log)
        assert [t['position_id'] for t in ts]==[101,100] and [t['net_profit'] for t in ts]==[-5,.5]
        assert len(ts)==2 and ledger[-1]['balance']==9995.5 and sum(x['cash_flow'] for x in ledger)==-4.5
        try:run.exact_trades(Path('fixture.htm'),'')
        except AssertionError:pass
        else:raise AssertionError('Missing position associations must fail')
    # UK clock transitions, used also to check actual accepted entries in native audits.
    for stamp,offset in [('2025-10-25T12:00:00',1),('2025-10-27T12:00:00',0),('2026-03-27T12:00:00',0),('2026-03-30T12:00:00',1)]:
        assert run.pd.Timestamp(stamp,tz='UTC').tz_convert('Europe/London').utcoffset().total_seconds()==offset*3600
    return 'Exact hedged non-FIFO position pairing, unequal lots, entry costs, native cash balance, missing-map rejection and London DST checks passed.'
def extras(r):
    peak=10000.;dd=0.;monthly=collections.defaultdict(float)
    for d in r['ledger']:
        peak=max(peak,d['balance']);dd=max(dd,100*(peak-d['balance'])/peak);monthly[d['time'][:7]]+=d['cash_flow']
    ts=r['trades']
    return dict(balance_dd_pct=dd,monthly_cash_flow={k:round(v,2) for k,v in sorted(monthly.items())},
      avg_hold_hours=sum(t['hold_hours'] for t in ts)/len(ts) if ts else None,
      median_hold_hours=float(run.pd.Series([t['hold_hours'] for t in ts]).median()) if ts else None,
      max_hold_hours=max((t['hold_hours'] for t in ts),default=0),
      longs=sum(t['side']=='Long' for t in ts),shorts=sum(t['side']=='Short' for t in ts),
      actual_stop_risk_to_budget_max=max((t['risk_audit']['actual_stop_cash']/t['risk_audit']['budget'] for t in ts),default=0))
def verify():
    regression=parser_test();build=json.loads((R/'build.json').read_text());index={};checks=[]
    assert run.sha(run.SOURCE)==build['source_sha256'] and run.sha(run.EXPERT)==build['binary_sha256']
    assert '0 errors, 0 warnings' in build['compiler_tail']
    for w in ['SMOKE','1Y','3M']:
        folder=R/'native'/w;r=json.loads((folder/'results.json').read_text());m=r['manifest'];n=r['native']
        assert m==json.loads((folder/'manifest.json').read_text())
        assert m['source_sha256']==build['source_sha256'] and m['binary_sha256']==build['binary_sha256']
        assert m['set_sha256']==run.sha(R/'RAW.set') and m['protocol_sha256']==run.sha(R/'PROTOCOL.txt')
        assert m['shared_account'] and m['independent_assumptions'] and m['symbol']=='UK100' and m['timeframe']=='H1'
        assert m['deposit']==10000 and m['risk_percent_per_trade']==1 and m['maximum_slots']==3 and m['model']==4 and m['delay_ms']==150
        assert (m['start'],m['end_exclusive'])==run.PERIODS[w]
        rp=run.T/'reports/quantlab-uk-independent20261004'/(w+'.htm')
        assert hashlib.sha256(gzip.decompress((folder/'report.htm.gz').read_bytes())).hexdigest()==r['report_sha256']==run.sha(rp)
        journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
        ts,ledger=run.exact_trades(rp,journal);assert ledger==r['ledger']
        keys=['position_id','module','open_time','close_time','open_price','close_price','net_profit','commission','swap','entry_deal','exit_deal']
        assert len(ts)==len(r['trades'])==n['trades']
        assert all(all(a[k]==b[k] for k in keys) for a,b in zip(ts,r['trades']))
        audited=run.audit(ts,r['orders'],journal)
        for k,v in r['audit'].items():assert audited[k]==v
        assert run.metrics(ts)==r['net_metrics']
        for i in run.LABELS:assert run.metrics([t for t in ts if t['module']==i])==r['module_metrics'][str(i)]
        assert abs(sum(t['net_profit'] for t in ts)-n['net_profit'])<.015
        assert abs(ledger[-1]['balance']-n['final_balance'])<.015
        assert abs(sum(v['net_profit'] for v in r['module_metrics'].values())-n['net_profit'])<.015
        assert r['counters']['entry_errors']==r['counters']['close_errors']==0
        assert all(r['counters'][key]>0 for key in ('drop','monday','trend'))
        if w!='1Y':assert n['history_quality']=='100% real ticks'
        r['extra']=extras(r);r['verified_audit']=audited;index[w]=r
        checks.append(dict(window=w,reconciled=True,positions=len(ts),module_counts={i:r['module_metrics'][i]['trades'] for i in r['module_metrics']},
          max_concurrent_positions=audited['maximum_concurrent_positions'],pauses=audited['pauses'],history_quality=n['history_quality'],
          module_contributions_sum_to_native=True,no_order_errors=True))
    save(R/'verification.json',dict(reconciliation_passed=True,deployment_approved=False,full_pipeline_passed=False,
      regression=regression,runs=checks,notes='Frozen source/binary/preset/protocol/report hashes. Native exact position-ID pairing, complete costs, actual deal-timed balance, closed H1 conditions, London session/DST, module/day uniqueness, overlapping-position cap and every net losing-streak pause checked. One-cent account-currency risk audit tolerance; actual fills and costs retained.'))
    return index

def chart(r,w,mode='balance'):
    start,end,_=WINDOWS[w];a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)
    width,height=1080,310;left,right,top,bottom=90,25,25,42
    paths=[];all_values=[]
    if mode=='modules':
        module={t['position_id']:t['module'] for t in r['trades']}
        for i in run.LABELS:
            pts=[(a,0.)];value=0.
            for d in r['ledger']:
                if module[d['position_id']]!=i:continue
                value+=d['cash_flow'];pts.append((datetime.fromisoformat(d['time']),value))
            pts.append((b,value));paths.append((COLORS[i],pts));all_values.extend(v for _,v in pts)
        label='Module cash-flow contributions in one shared account; not independent account curves'
    else:
        pts=[(a,0. if mode=='dd' else 10000.)];peak=10000.
        for d in r['ledger']:
            peak=max(peak,d['balance']);v=-100*(peak-d['balance'])/peak if mode=='dd' else d['balance']
            pts.append((datetime.fromisoformat(d['time']),v))
        pts.append((b,pts[-1][1]));paths=[('#fa909c' if mode=='dd' else '#84f5c5',pts)];all_values=[v for _,v in pts]
        label='Actual account-balance drawdown, not floating-equity DD' if mode=='dd' else 'Actual shared account balance by native deal time, including entry costs'
    low=min(all_values);high=max(all_values);pad=max(.3 if mode=='dd' else 65,(high-low)*.08);low-=pad;high+=pad
    def x(t):return left+(t-a).total_seconds()/(b-a).total_seconds()*(width-left-right)
    def y(v):return top+(high-v)/(high-low)*(height-top-bottom)
    svg=f'<svg role="img" aria-label="{label}" viewBox="0 0 {width} {height}"><title>{label}</title>'
    for i in range(5):
        v=low+(high-low)*i/4;yy=y(v);text=f'{v:.1f}%' if mode=='dd' else '$'+f'{v:,.0f}'
        svg+=f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#284b3b"/><text x="6" y="{yy+4:.1f}" font-size="13" fill="#adc5b6">{text}</text>'
    for color,pts in paths:
        d=f'M{x(pts[0][0]):.1f},{y(pts[0][1]):.1f}'
        for when,value in pts[1:]:d+=f'H{x(when):.1f}V{y(value):.1f}'
        svg+=f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.3"/>'
    svg+=f'<text x="{left}" y="{height-9}" font-size="13" fill="#adc5b6">{start}</text><text x="{width-right}" y="{height-9}" text-anchor="end" font-size="13" fill="#adc5b6">{end} exclusive</text></svg>'
    if mode=='modules':svg+='<div class="legend">'+''.join(f'<span style="color:{COLORS[i]}">● {run.LABELS[i]}</span>' for i in run.LABELS)+'</div>'
    return svg

def render(index):
    parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QuantLab idea 3 · Independent UK100 trio</title><style>',
      ':root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#07140e;color:#eef9f1;font:15px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:42px 24px}h1{font-size:clamp(32px,5vw,60px);line-height:1.1;max-width:1000px}h2{font-size:25px}h3{font-size:19px}p{color:#b6d0be}.tag{color:#8af3c5;font:12px/1.8 ui-monospace,monospace;letter-spacing:.12em}.notice{padding:18px 22px;border:1px solid #827c36;background:#262c18;border-radius:14px;color:#ffe6a1}section{padding:25px;background:#0b2016;border:1px solid #284b3b;border-radius:16px;margin:24px 0}.scroll{overflow-x:auto}table{border-collapse:collapse;white-space:nowrap;width:100%;font-size:13px}th,td{padding:12px;text-align:right;border-bottom:1px solid #284b3b}th{background:#143122;color:#a4f2c8}th:first-child,td:first-child{text-align:left}.rules td{white-space:normal;text-align:left}.rules td:first-child{min-width:180px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.muted{font-size:13px;color:#a0bdaa}a{color:#8af3c5}nav,.legend{display:flex;flex-wrap:wrap;gap:18px}svg{width:100%;height:auto;display:block;margin:18px 0}.legend{font-size:13px}details{margin:20px 0;padding-top:18px;border-top:1px solid #284b3b}summary{cursor:pointer;font-weight:650;color:#b0f5d2}li{margin:8px 0}@media(max-width:850px){main{padding:25px 14px}section{padding:18px}.grid{grid-template-columns:1fr}}</style></head><body><main>',
      '<p class="tag">CALYX · IDEA 03 · STANDALONE RAW TEST · SHARED ACCOUNT</p><h1>UK100.<br>Drop, Monday dip, trend pullback.</h1>',
      '<p>Three H1 modules in one Exness UK100 CFD simulation. One shared $10,000 account; 1% planned equity risk EACH entry, up to three simultaneous positions. No additive independent-account overlay.</p>',
      '<div class="notice">Independent prototype inspired by the public concept—not QuantLab’s executable or a verified recreation of its exact rules. Detailed conditions are subscription-only. Every numerical signal, exit, session and pause setting here is our frozen assumption. No unrelated existing EA comparison.</div>',
      '<nav><a href="#summary">Results</a><a href="#rules">Exact rules</a><a href="#year">One year</a><a href="#quarter">Three months</a><a href="#verification">Verification</a></nav>',
      '<section id="summary"><h2>Combined shared-account results</h2>']
    summary=[]
    for w in WINDOWS:
        r=index[w];s=r['net_metrics'];n=r['native'];a=r['verified_audit']
        summary.append(dict(window=w,start=WINDOWS[w][0],end_exclusive=WINDOWS[w][1],**s,equity_dd_pct=n['equity_dd_pct'],
          native_sharpe=n['sharpe_ratio'],history_quality=n['history_quality'],max_concurrent=a['maximum_concurrent_positions'],pauses=a['pauses']))
    parts.append(table(['Window','Return','Net P&L','Trades','Net WR','Net PF','Max equity DD','MT5 Sharpe','Max W / L streak','Pauses','Ticks'],
      [[WINDOWS[s['window']][2],num(s['return_pct'])+'%',money(s['net_profit']),s['trades'],num(s['win_rate_pct'],1)+'%',num(s['net_pf'],3),
        num(s['equity_dd_pct'])+'%',num(s['native_sharpe']),f"{s['max_win_streak']} / {s['max_loss_streak']}",s['pauses'],s['history_quality']] for s in summary]))
    verdict='The full trio is weak annually and fails badly in the recent quarter. Do not deploy this frozen version. Post-drop recovery is the most interesting annual module, but its quarterly sample is only six trades and approximately flat.'
    parts.append('<p>'+verdict+'</p><p class="muted">Net metrics include entry/exit costs and swaps. Drawdown is native floating-equity DD. MT5 Sharpe is reproduced as reported, not an independently annualised daily-return Sharpe. No optimisation or passed full pipeline.</p></section>')
    parts.append('<section id="rules"><h2>Exact independent starting rules</h2><div class="rules">')
    rules=[
      ['Public concept','UK100 H1: recovery after a sharp decline, Monday dip buying, two-way trend pullbacks and defence against losing streaks. Numerical vendor rules are not disclosed publicly.'],
      ['Drop recovery · long','Before the signal candle: 24-bar highest high minus previous close ≥3 × previous ATR14, and previous RSI2 ≤10. Signal H1 must be bullish and close above previous H1 high.'],
      ['Monday dip · long','London entry day Monday. Previous H1 close ≤most recent completed broker-Friday D1 close −0.5 × previous ATR14. Signal bullish, closes above previous H1 high.'],
      ['Trend pullback · both sides','Long: EMA50 >EMA200, EMA50 rising; previous close ≤previous EMA20, signal bullish and closes >current closed EMA20. Short: reverse inequalities and a bearish signal body. No ADX/DI or anchored VWAP.'],
      ['Entry window','First tick of a new H1 bar, using only closed candles. Entries Monday–Friday 08:00 inclusive–16:00 exclusive London. UK daylight-saving conversion.'],
      ['Risk and limits','1% of current equity PER entry; one position per module, one new entry per module per London date, three slots in the same account. Separate 1% budgets may stack; this is not a 1% portfolio cap. Hedging allowed.'],
      ['Stops and targets','SL2 × signal ATR14 from requested executable quote, tick aligned and widened only for broker limits. TP1R for Drop/Monday; TP2R for Trend. Actual delayed fills retained; no trailing/break-even/grid.'],
      ['Timed exit','Close survivors after 48 hours at the next broker-permitted tick. Overnight/weekend holds allowed. A timed exit cannot guarantee closure while market permission/ticks are unavailable.'],
      ['Shared loss brake','Three consecutive net losing completed positions across all modules →pause NEW entries for 24 clock hours and reset loss counter. Winner/flat resets streak. Existing positions retain stops, targets and timed exits.'],
      ['Cash sizing','Broker OrderCalcProfit, lots rounded DOWN. Under-minimum lots skipped. Logged post-fill risk estimates have account-currency cent rounding; execution, FX conversion, fees and gaps can exceed the requested budget.'],
      ['Native experiment','Exness-MT5Trial16 UK100 H1, every tick model4, 150ms delay, $10,000 USD, 1:2000 leverage, native costs. One preset, fresh-flat independent date windows. Tester-only; no live deployment.']]
    parts.append(table(['Component','Rule / qualification'],rules))
    parts.append('</div><p><a href="https://api-quantlab.com/algorithmen/uk100-premium" target="_blank" rel="noopener">QuantLab public description</a> · <a href="https://api-quantlab.com/algorithmen/uk100-premium/analyse" target="_blank" rel="noopener">Public deep-dive preview</a>. Vendor headline figures cover an undisclosed different period/preset and are not a comparable control.</p></section>')
    for w in WINDOWS:
        r=index[w];s=r['net_metrics'];n=r['native'];e=r['extra'];a=r['verified_audit'];id_='year' if w=='1Y' else 'quarter'
        parts.append(f'<section id="{id_}"><p class="tag">{w} · {WINDOWS[w][2].upper()}</p><h2>Shared account and module contributions</h2>')
        parts.append(table(['Final account balance','Expectancy / trade','Average win','Average loss','Avg / median / max holding','Long / short','Max simultaneous','Overnight / weekend holds','End closes'],
          [[money(n['final_balance']),money(s['expectancy_usd']),money(s['avg_win_usd']),money(s['avg_loss_usd']),
            num(e['avg_hold_hours'])+' / '+num(e['median_hold_hours'])+' / '+num(e['max_hold_hours'])+' h',f"{e['longs']} / {e['shorts']}",
            a['maximum_concurrent_positions'],f"{a['overnight_positions']} / {a['weekend_positions']}",a['end_liquidations']]]))
        parts.append('<div class="grid"><div><h3>Actual shared account balance</h3><p class="muted">Native deal-timed cash flow, including commissions charged on entry. Excludes floating P&amp;L.</p>'+chart(r,w)+'</div><div><h3>Account-balance drawdown</h3><p class="muted">Maximum '+num(e['balance_dd_pct'])+'%. Native floating-equity drawdown is measured separately above.</p>'+chart(r,w,'dd')+'</div></div>')
        parts.append('<h3>Module contributions—not standalone backtests</h3>')
        parts.append(table(['Module','Trades','Net P&L','Contribution / initial capital','Net WR','Net PF','Max W / L streak','Avg win','Avg loss','Expectancy / trade'],
          [[run.LABELS[i],r['module_metrics'][str(i)]['trades'],money(r['module_metrics'][str(i)]['net_profit']),
            num(r['module_metrics'][str(i)]['return_pct'])+'%',num(r['module_metrics'][str(i)]['win_rate_pct'],1)+'%',
            num(r['module_metrics'][str(i)]['net_pf'],3),f"{r['module_metrics'][str(i)]['max_win_streak']} / {r['module_metrics'][str(i)]['max_loss_streak']}",
            money(r['module_metrics'][str(i)]['avg_win_usd']),money(r['module_metrics'][str(i)]['avg_loss_usd']),
            money(r['module_metrics'][str(i)]['expectancy_usd'])] for i in run.LABELS]))
        parts.append('<p class="muted">Every module uses the same changing account equity and shared loss-pause state. Removing a module would change sizes and later entry availability; these contributions do not predict a standalone module’s result.</p>'+chart(r,w,'modules'))
        parts.append('<h3>Monthly native cash flow</h3>'+table(['Month UTC','Cash flow including entry costs'],[[k,money(v)] for k,v in e['monthly_cash_flow'].items()]))
        parts.append(table(['Commission','Swap','Pause activations','Blocked H1 entry checks','Min-lot skips','Entry / close errors','Max post-fill requested risk excess'],
          [[money(r['commission']),money(r['swap']),a['pauses'],r['counters']['blocked_bars'],r['counters']['minlot_skips'],
            f"{r['counters']['entry_errors']} / {r['counters']['close_errors']}",money(a['maximum_requested_risk_excess_usd'])]]))
        parts.append(f'<details><summary>All {s["trades"]} complete positions · exact entry/exit breakdown</summary>')
        parts.append(table(['#','Module','Side','Entry London','Exit London','Lots','Entry','Exit','Initial SL','Initial TP','Actual initial RR','Net P&L','Hours','Exit'],
          [[t['number'],t['module_name'],t['side'],t['open_london'],t['close_london'],num(t['volume']),
            num(t['open_price']),num(t['close_price']),num(t['initial_sl']),num(t['initial_tp']),num(t['actual_initial_rr'],3),
            money(t['net_profit']),num(t['hold_hours']),t['exit_reason']] for t in r['trades']]))
        parts.append(f'<p><a href="native/{w}/trades.csv">All trades CSV</a> · <a href="native/{w}/results.json">Native measurements, signal proofs and exact inputs</a> · <a href="native/{w}/ledger.json">Actual account cash ledger</a></p></details></section>')
    smoke=index['SMOKE']
    parts.append('<section id="verification"><h2>Checks and limitations</h2><ul>'
      '<li>Compiler: zero errors and warnings. September preflight: '+str(smoke['native']['trades'])+' trades with all three modules active, exact position/cost reconciliation and net loss-brake audit.</li>'
      '<li>Every deal is associated with native DEAL_POSITION_ID, including simultaneous hedged positions. No same-symbol FIFO attribution. Counts, full net costs and actual cash balances reconcile; regression covers out-of-order closes and unequal volumes.</li>'
      '<li>Accepted logs verify the closed H1 predicates, prior-Friday reference, London timing/DST, risk budgets, one entry per module/day, at most three positions and every actual 24-hour pause. No assumed fills or erased losing trades.</li>'
      '<li>Annual data: '+esc(index['1Y']['native']['history_quality'])+'. Quarterly data: '+esc(index['3M']['native']['history_quality'])+'. Generated earlier ticks are not equivalent to full recorded-tick validation.</li>'
      '<li>One-year and quarterly accounts each start flat with $10,000. They need not produce identical dollar results for overlapping trades. Overlapping samples are not independent validation.</li>'
      '<li>Native tester uses available broker specifications and session permissions, not a full historic exchange microstructure reconstruction. Elapsed holds can exceed 48h when closure is unavailable. No test-end positions were removed from results.</li>'
      '<li>Rounding the one-lot profit estimate and post-fill account-currency conversion can yield a sub-cent budget discrepancy; audit tolerance is $0.011, not an unexplained risk override. Fees, swaps and delayed/gap fills can exceed planned cash risk further.</li>'
      '<li>No tuning, independent holdout, bootstrap, Monte Carlo, cost stress or full pipeline. No FTMO guards or other portfolio EAs included. Native Sharpe is reported, not independently annualised.</li>'
      '<li>No active MT5 terminal, production EA, installer/BAT, website, trading permission or Git remote changed. Await review before XAUUSD 3x Speed Q4 Turn.</li></ul>'
      '<p><a href="PROTOCOL.txt">Frozen protocol</a> · <a href="RAW.set">Preset</a> · <a href="verification.json">Verification</a> · <a href="summary.json">Summary</a> · <a href="RESULTS.json">Full raw data</a></p></section></main></body></html>')
    page=''.join(parts);assert page.count('<svg')==6
    (R/'Results.html').write_text(page,encoding='utf-8');save(R/'summary.json',summary)
    print(json.dumps(dict(report=str(R/'Results.html'),summary=summary,verdict=verdict),indent=2))
if __name__=='__main__':render(verify())

