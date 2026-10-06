"""Verify standalone native runs and build an offline raw-test report."""
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import collections,gzip,hashlib,html,json
import run
R=Path(__file__).resolve().parent
WINDOWS={'1Y':('2025-10-04','2026-10-04','4 Oct 2025–3 Oct 2026'),
         '3M':('2026-07-04','2026-10-04','4 Jul–3 Oct 2026')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def esc(x):return html.escape(str(x))
def money(v):return 'N/A' if v is None else '$'+f'{v:+,.2f}'
def num(v,n=2):return 'N/A' if v is None else f'{v:,.{n}f}'
def table(headers,rows):
    def row(values,tag='td'):return '<tr>'+''.join(f'<{tag}>'+esc(v)+f'</{tag}>' for v in values)+'</tr>'
    return '<div class="scroll"><table><thead>'+row(headers,'th')+'</thead><tbody>'+''.join(row(v) for v in rows)+'</tbody></table></div>'

def position_parser_test():
    # Exit the second, smaller position first; FIFO would invent partial trades.
    rows=[
      ['2026.09.21 13:39:00','2','USTEC','buy','in','0.63','100','2','-0.39','0','0','9999.61','QNB20260921_L1'],
      ['2026.09.21 13:39:00','3','USTEC','buy','in','0.62','101','3','-0.38','0','0','9999.23','QNB20260921_L2'],
      ['2026.09.21 13:40:00','4','USTEC','sell','out','0.62','110','4','0','0','5.58','10004.81','tp 110'],
      ['2026.09.21 13:41:00','5','USTEC','sell','out','0.63','99','5','0','0','-0.63','10004.18','sl 99']]
    body='<b>Deals</b>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)
    journal='take profit triggered #3 buy 0.62 USTEC 101 tp: 110 [#4 sell 0.62 USTEC at 110]\nstop loss triggered #2 buy 0.63 USTEC 100 sl: 99 [#5 sell 0.63 USTEC at 99]'
    with patch.object(run.h,'_read_report',return_value=body):
        trades=run.exact_hedged_trades(Path('synthetic.htm'),journal)
        assert len(trades)==2 and [t['position_id'] for t in trades]==[3,2]
        assert trades[0]['entry_comment'].endswith('_L2') and trades[0]['net_profit']==5.2
        assert trades[1]['entry_comment'].endswith('_L1') and trades[1]['net_profit']==-1.02
        try:run.exact_hedged_trades(Path('synthetic.htm'),'')
        except AssertionError:pass
        else:raise AssertionError('Missing exact position mappings must fail')
    return 'Passed non-FIFO closes, unequal lots, costs and missing-mapping rejection'

def leg_metrics(ts):
    wins=[t['net_profit'] for t in ts if t['net_profit']>0]
    losses=[t['net_profit'] for t in ts if t['net_profit']<0]
    return dict(positions=len(ts),net_usd=round(sum(t['net_profit'] for t in ts),2),
      win_rate_pct=100*len(wins)/len(ts) if ts else None,
      net_pf=sum(wins)/-sum(losses) if losses else None,
      avg_win_usd=sum(wins)/len(wins) if wins else None,
      avg_loss_usd=sum(losses)/len(losses) if losses else None,
      target_exits=sum(t['exit_reason']=='Target' for t in ts),
      stop_exits=sum(t['exit_reason']=='Stop/trailing stop' for t in ts),
      time_exits=sum(t['exit_reason']=='Time/Friday close' for t in ts))

def extras(r):
    balance=10000.;peak=10000.;maxdd=0.;monthly=collections.defaultdict(float)
    for t in sorted(r['trades'],key=lambda t:(t['close_time'],t['exit_deal'])):
        balance+=t['net_profit'];peak=max(peak,balance)
        maxdd=max(maxdd,100*(peak-balance)/peak)
        monthly[t['close_time'][:7]]+=t['net_profit']
    b=r['baskets'];pnl=[t['net_profit'] for t in b]
    return dict(closed_balance_dd_pct=maxdd,final_closing_balance=round(balance,2),
      monthly_net_usd={k:round(v,2) for k,v in sorted(monthly.items())},
      expectancy_usd=sum(pnl)/len(pnl) if pnl else None,
      best_basket_usd=max(pnl) if pnl else None,worst_basket_usd=min(pnl) if pnl else None,
      median_hold_hours=run.pd.Series([x['hold_hours'] for x in b]).median() if b else None,
      max_hold_hours=max([x['hold_hours'] for x in b],default=0),
      longs=sum(x['side']=='Long' for x in b),shorts=sum(x['side']=='Short' for x in b),
      weekend_carry_baskets=[x['id'] for x in b if any(run.pd.Timestamp(t['close_ny']).weekday()>=5 for t in x['legs'])],
      weekend_carry_positions=sum(run.pd.Timestamp(t['close_ny']).weekday()>=5 for t in r['trades']),
      actual_to_budget_max_ratio=max([x['actual_initial_stop_risk_usd']/x['planned_budget_usd'] for x in b],default=0),
      legs={str(i):leg_metrics([t for t in r['trades'] if t['leg']==i]) for i in range(1,5)})

def verify():
    parser_test=position_parser_test()
    build=json.loads((R/'build.json').read_text())
    assert sha(run.SOURCE)==build['source_sha256'] and sha(run.EXPERT)==build['binary_sha256']
    assert '0 errors, 0 warnings' in build['compiler_tail']
    checks=[];index={}
    for w in ['SMOKE','1Y','3M']:
        folder=R/'native'/w;r=json.loads((folder/'results.json').read_text())
        m=r['manifest'];n=r['native'];ts=r['trades'];b=r['baskets']
        assert m==json.loads((folder/'manifest.json').read_text())
        assert m['binary_sha256']==build['binary_sha256'] and m['source_sha256']==build['source_sha256']
        assert m['set_sha256']==sha(R/'RAW.set') and m['protocol_sha256']==sha(R/'PROTOCOL.txt')
        assert m['deposit']==10000 and m['risk_per_basket_pct']==1 and m['delay_ms']==150 and m['model']==4
        assert m['timeframe']=='M3' and m['symbol']=='USTEC' and m['no_unrelated_ea_comparison']
        assert (m['start'],m['end_exclusive'])==run.PERIODS[w]
        report=gzip.decompress((folder/'report.htm.gz').read_bytes())
        assert hashlib.sha256(report).hexdigest()==r['report_sha256']
        journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
        report_path=run.T/'reports/quantlab-nqb-independent20261004'/(w+'.htm')
        assert report_path.read_bytes()==report
        parsed=run.exact_hedged_trades(report_path,journal)
        assert len(parsed)==len(ts)==n['trades']==4*len(b)
        keys=['position_id','entry_deal','exit_deal','net_profit','gross_profit','commission','swap',
              'open_time','close_time','open_price','close_price','entry_comment','exit_comment']
        assert all(all(p[k]==t[k] for k in keys) for p,t in zip(parsed,ts))
        assert abs(sum(t['net_profit'] for t in ts)-n['net_profit'])<.015
        assert len({t['position_id'] for t in ts})==len(ts)
        assert len({x['id'] for x in b})==len(b)
        assert all(a['close_time']<=c['open_time'] for a,c in zip(b,b[1:]))
        assert run.basket_metrics(b)==r['basket_metrics']
        assert run.parse_signal_audit(journal,b)==r['signal_audit']
        for basket in b:
            assert len(basket['legs'])==4 and {t['leg'] for t in basket['legs']}=={1,2,3,4}
            assert abs(sum(t['net_profit'] for t in basket['legs'])-basket['net_profit'])<.015
            for t in basket['legs']:
                assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.015
                assert t['symbol']=='USTEC' and not t['boundary_exit']
                if run.pd.Timestamp(t['close_ny']).weekday()==4:assert t['close_ny'][11:19]<'15:55:02'
        assert not any(r['ea_counters'][k] for k in ['entry_errors','close_errors','modify_errors'])
        assert n['history_quality']==('75% real ticks' if w=='1Y' else '100% real ticks')
        r['extra']=extras(r);index[w]=r
        assert abs(r['extra']['final_closing_balance']-n['final_balance'])<.015
        assert abs(sum(v['net_usd'] for v in r['extra']['legs'].values())-n['net_profit'])<.015
        checks.append(dict(window=w,baskets=len(b),positions=len(ts),passed=True,
          net_usd=n['net_profit'],equity_dd_pct=n['equity_dd_pct'],history_quality=n['history_quality'],
          counts_reconciled=True,exact_position_mapping=True,closed_bar_signal_audit=True,
          total_budget_not_fourfold=True,no_weekend_holding=not r['extra']['weekend_carry_baskets'],
          weekend_carry_baskets=r['extra']['weekend_carry_baskets']))
    save(R/'verification.json',dict(passed=True,parser_regression=parser_test,runs=checks,
      checks='Frozen source/executable/preset/protocol/report hashes; native position-ticket/deal associations; complete costs and counts; one basket per NY date; non-overlapping baskets; four portions; closed-bar EMA/ADX/DI audit; risk budgets; native DD; no failed orders/modifications. Weekend carries are retained and flagged, not assumed away.',
      limitations='Raw assumptions only. No optimisation, independent holdout, cost stress, Monte Carlo, FTMO/portfolio model, live deployment or vendor-rule parity.'))
    return index

def chart(r,w,drawdown=False):
    start,end,_=WINDOWS[w];a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)
    pts=[(a,0. if drawdown else 10000.)];balance=10000.;peak=10000.
    for t in sorted(r['trades'],key=lambda t:(t['close_time'],t['exit_deal'])):
        balance+=t['net_profit'];peak=max(peak,balance)
        pts.append((datetime.fromisoformat(t['close_time']),-100*(peak-balance)/peak if drawdown else balance))
    pts.append((b,pts[-1][1]))
    width,height=1100,310;left,right,top,bottom=90,24,28,42
    values=[v for _,v in pts];low=min(values);high=max(values)
    pad=max(.3 if drawdown else 70,(high-low)*.07);low-=pad;high+=pad
    def x(t):return left+(t-a).total_seconds()/(b-a).total_seconds()*(width-left-right)
    def y(v):return top+(high-v)/(high-low)*(height-top-bottom)
    label='Closed-balance drawdown, excludes open positions' if drawdown else 'Closing balance by leg exit date, excludes open positions'
    s=f'<svg role="img" aria-label="{label}" viewBox="0 0 {width} {height}"><title>{label}</title>'
    for i in range(5):
        v=low+(high-low)*i/4;yy=y(v);text=f'{v:.1f}%' if drawdown else '$'+f'{v:,.0f}'
        s+=f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#244438"/><text x="6" y="{yy+4:.1f}" fill="#a6c6b7" font-size="13">{text}</text>'
    d=f'M{x(pts[0][0]):.1f},{y(pts[0][1]):.1f}'
    for when,value in pts[1:]:d+=f'H{x(when):.1f}V{y(value):.1f}'
    color='#fb8d99' if drawdown else '#80f3c2'
    s+=f'<path d="{d}" stroke="{color}" fill="none" stroke-width="2.3"/>'
    s+=f'<text x="{left}" y="{height-10}" fill="#a6c6b7" font-size="13">{start}</text><text x="{width-right}" y="{height-10}" fill="#a6c6b7" font-size="13" text-anchor="end">{end} exclusive</text></svg>'
    return s

def render(index):
    out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QuantLab idea 2 · Independent four-part EMA cross</title><style>',
      ':root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#06130e;color:#e9f8ef;font:15px/1.6 system-ui,sans-serif}main{max-width:1420px;margin:auto;padding:42px 24px}h1{font-size:clamp(34px,5vw,60px);line-height:1.1;max-width:950px}h2{font-size:25px}h3{font-size:19px}p{color:#b4cfc1}.tag{font:12px/1.8 ui-monospace,monospace;letter-spacing:.13em;color:#83f5c6}.notice{padding:18px 22px;border:1px solid #81773a;background:#252918;border-radius:14px;color:#ffe7a6}section{margin:24px 0;padding:25px;border:1px solid #274538;border-radius:17px;background:#0c1f17}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th,td{padding:12px;border-bottom:1px solid #244438;text-align:right}th{background:#122c20;color:#9eebc6}th:first-child,td:first-child{text-align:left}.rules td{white-space:normal;text-align:left}.rules td:first-child{min-width:180px}svg{width:100%;height:auto;display:block;margin:15px 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.muted{font-size:13px;color:#9bbbaa}a{color:#8af2c2}nav{display:flex;gap:20px;flex-wrap:wrap}details{padding-top:15px;margin-top:18px;border-top:1px solid #284d3d}summary{cursor:pointer;color:#a5f4d0;font-weight:650}li{margin:8px 0}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:25px 14px}section{padding:18px}}</style></head><body><main>',
      '<p class="tag">CALYX · IDEA 02 · STANDALONE RAW NATIVE TEST</p><h1>EMA cross.<br>Three targets and a runner.</h1>',
      '<p>US100 CFD / Exness USTEC M3. Four equal planned-risk portions share one 1% equity-risk budget. USD $10,000 starting capital; 150 ms execution delay, native spread, commission and swap.</p>',
      '<div class="notice">Independent NQBlade-inspired prototype—not QuantLab’s proprietary EA or a verified replica. The public page describes the concept but does not disclose the numerical settings. Our settings were frozen before testing. No unrelated existing EA is compared here.</div>',
      '<nav><a href="#summary">Results</a><a href="#rules">Exact assumptions</a><a href="#1Y">One year</a><a href="#3M">Three months</a><a href="#verification">Verification</a></nav>',
      '<section id="summary"><h2>Raw results · complete trade setups</h2>']
    summary=[]
    for w in WINDOWS:
        r=index[w];s=r['basket_metrics'];n=r['native']
        summary.append(dict(window=w,start=WINDOWS[w][0],end_exclusive=WINDOWS[w][1],baskets=s['baskets'],
          portions=n['trades'],net_usd=s['net_profit'],return_pct=s['return_pct'],net_pf=s['net_pf'],
          win_rate_pct=s['win_rate_pct'],equity_dd_pct=n['equity_dd_pct'],native_sharpe=n['sharpe_ratio'],
          max_win_streak=s['max_win_streak'],max_loss_streak=s['max_loss_streak'],history_quality=n['history_quality']))
    out.append(table(['Window','Net return','Setups','Portions','Setup win rate','Setup net PF','Max equity DD','MT5 Sharpe','Max W / L streak','Ticks'],
      [[WINDOWS[s['window']][2],num(s['return_pct'])+'%',s['baskets'],s['portions'],num(s['win_rate_pct'],1)+'%',num(s['net_pf'],3),
        num(s['equity_dd_pct'])+'%',num(s['native_sharpe']),f"{s['max_win_streak']} / {s['max_loss_streak']}",s['history_quality']] for s in summary]))
    out.append('<p class="muted">A setup comprises all four portions. Primary PF, win rate and streaks use their combined net result, including costs. Drawdown is native floating-equity drawdown. MT5 Sharpe is copied from the native report, not an independently annualised daily-return measure.</p>')
    verdict='Neither historical window demonstrated positive net expectancy. These frozen assumptions do not support deployment.'
    out.append('<p>'+verdict+'</p></section><section id="rules"><h2>What was built</h2><div class="rules">')
    rules=[
      ['Public concept only','Nasdaq M3 EMA cross with entry confirmation; four portions, three targets and a runner. Detailed vendor settings are not public.'],
      ['Independent entry assumption','Completed M3 EMA9/EMA21 cross, ADX14 ≥20, directional DI agreement. Buy: fast crosses above slow and +DI > −DI; sell: reverse. No intrabar/repainting signals.'],
      ['Time window assumption','Signal-bar opening time 09:30 inclusive–15:30 exclusive New York, weekdays. Entry next M3 bar first tradable tick (normally 09:33–15:30 NY). US daylight-saving conversion.'],
      ['Initial stop assumption','Common stop 2 × ATR14 of M3, from the initial requested quote; tick aligned and widened only for actual broker stop/freeze distance.'],
      ['Cash sizing','1% of entry equity TOTAL, allocated 0.25% to each portion. Lots rounded DOWN from broker profit calculation. Skip if the initial quarter budget cannot meet minimum lot. Fills/gaps and fees can exceed planned risk.'],
      ['Target portions','Nominal targets 1R / 2R / 3R from each pre-order quote and common stop. Actual fills retained, so actual initial R ratios can differ. No break-even or trailing on these three portions.'],
      ['Runner assumption','No fixed TP. Trailing latches after +1 initial R. Follows completed M3 EMA21 once per bar, respects broker distance and never loosens an accepted stop. No opposite-cross exit.'],
      ['Limits assumption','At most one basket per NY date; no new basket while any portion remains. Close survivors after 24 hours at next tradable tick. Friday flatten intended at/after 15:55 NY, but cannot execute when trading/ticks are unavailable; observed carries are retained below.'],
      ['Safety','Tester-only and hedging-only. Failed partial entry flattens already-open portions and invalidates the run. Not installed into a live terminal, website or BAT.'],
      ['Raw test—not optimisation','One preset, no tuning after outcomes, no independent holdout, bootstrap, Monte Carlo, cost stress or full pipeline at this step.']]
    out.append(table(['Component','Rule / evidence'],rules))
    out.append('</div><p><a href="https://api-quantlab.com/algorithmen/nqblade" target="_blank" rel="noopener">QuantLab’s public NQBlade description</a> · Numerical settings, confirmation, session and holding limits above are independent assumptions. Vendor headline figures are not used as a comparable control.</p></section>')
    for w in WINDOWS:
        r=index[w];s=r['basket_metrics'];n=r['native'];e=r['extra']
        out.append(f'<section id="{w}"><p class="tag">{w} · {WINDOWS[w][2].upper()}</p><h2>Standalone test breakdown</h2>')
        out.append(table(['Net profit','Final balance','Avg winning setup','Avg losing setup','Expectancy / setup','Best / worst setup','Median / max hold','Long / short setups'],
          [[money(s['net_profit']),money(n['final_balance']),money(s['avg_win_usd']),money(s['avg_loss_usd']),money(e['expectancy_usd']),
            money(e['best_basket_usd'])+' / '+money(e['worst_basket_usd']),num(e['median_hold_hours'])+' / '+num(e['max_hold_hours'])+' h',f"{e['longs']} / {e['shorts']}"]]))
        out.append('<div class="grid"><div><h3>Closing balance</h3><p class="muted">Each actual portion exit booked on its closing date. Includes costs; excludes floating P&amp;L.</p>'+chart(r,w)+'</div><div><h3>Closed-balance drawdown</h3><p class="muted">Maximum '+num(e['closed_balance_dd_pct'])+'%. Not the native equity drawdown above.</p>'+chart(r,w,True)+'</div></div>')
        out.append('<h3>Which portion contributed?</h3>')
        out.append(table(['Portion','Positions','Net P&L','Net WR','Net PF','Avg win','Avg loss','Target exits','Stop exits','Time / Friday exits'],
          [[f'{i} · '+('1R target' if i==1 else '2R target' if i==2 else '3R target' if i==3 else 'EMA21 runner'),
            e['legs'][str(i)]['positions'],money(e['legs'][str(i)]['net_usd']),num(e['legs'][str(i)]['win_rate_pct'],1)+'%',
            num(e['legs'][str(i)]['net_pf'],3),money(e['legs'][str(i)]['avg_win_usd']),money(e['legs'][str(i)]['avg_loss_usd']),
            e['legs'][str(i)]['target_exits'],e['legs'][str(i)]['stop_exits'],e['legs'][str(i)]['time_exits']] for i in range(1,5)]))
        out.append('<p class="muted">Portion stats are diagnostic, not four independent signals. Native PF '+num(n['profit_factor'])+' and native WR '+num(n['win_rate_pct'],1)+'% differ from net setup metrics. Net portion PF '+num(r['leg_net_pf'],3)+'; net portion WR '+num(r['leg_net_win_rate_pct'],1)+'%.</p>')
        out.append('<h3>Monthly closing P&amp;L</h3>'+table(['Month UTC','Closed net $'],[[k,money(v)] for k,v in e['monthly_net_usd'].items()]))
        out.append(table(['Commission','Swap','Min-lot skips','Failed entry / modification / close','Boundary setups','Actual initial risk / budget · maximum'],
          [[money(r['commission']),money(r['swap']),r['ea_counters']['minlot_skips'],
            f"{r['ea_counters']['entry_errors']} / {r['ea_counters']['modify_errors']} / {r['ea_counters']['close_errors']}",
            s['boundary_baskets'],num(e['actual_to_budget_max_ratio']*100)+'%']]))
        out.append('<p class="muted">Unexpected weekend carry: '+str(len(e['weekend_carry_baskets']))+' setups / '+str(e['weekend_carry_positions'])+' portions. NY entry dates: '+(', '.join(e['weekend_carry_baskets']) or 'none')+'. Their actual exits and gap outcomes remain in these results; no synthetic Friday fills were substituted.</p>')
        out.append(f'<details><summary>All {s["baskets"]} setups · four-portion contributions</summary>')
        out.append(table(['NY date','Side','Entry NY','Final exit NY','Hours','Combined net','1R net','2R net','3R net','Runner net','Planned stop risk','Actual initial stop risk'],
          [[b['open_ny'][:10],b['side'],b['open_ny'],b['close_ny'],num(b['hold_hours']),money(b['net_profit']),
            *[money(t['net_profit']) for t in b['legs']],money(b['planned_budget_usd']),money(b['actual_initial_stop_risk_usd'])] for b in r['baskets']]))
        out.append(f'<p><a href="native/{w}/baskets.csv">Setup CSV</a></p></details><details><summary>All {n["trades"]} portions · exact positions, stops and exits</summary>')
        out.append(table(['Position ID','Setup date','Portion','Side','Entry NY','Exit NY','Lots','Entry','Exit','Initial SL','Initial TP','Actual initial RR','Net $','Exit reason'],
          [[t['position_id'],t['basket_id'],t['leg'],t['side'],t['open_ny'],t['close_ny'],num(t['volume']),
            num(t['open_price']),num(t['close_price']),num(t['initial_sl']),'None' if t['initial_tp'] is None else num(t['initial_tp']),
            num(t['initial_rr'],3),money(t['net_profit']),t['exit_reason']] for t in r['trades']]))
        out.append(f'<p><a href="native/{w}/legs.csv">Portion CSV</a> · <a href="native/{w}/results.json">Native results and frozen inputs</a></p></details></section>')
    smoke=index['SMOKE']
    out.append('<section id="verification"><h2>Verification and limitations</h2><ul>'
      '<li>Compiled with zero errors and warnings. Smoke test reconciled '+str(smoke['basket_metrics']['baskets'])+' complete setups / '+str(smoke['native']['trades'])+' exact hedged positions before long tests.</li>'
      '<li>Exits paired by native position ticket, not same-symbol FIFO. Regression test covers out-of-order closes and unequal volumes. All prices, costs, P&amp;L, counts and balances reconcile with the native report.</li>'
      '<li>Signal logs verify closed-bar EMA/ADX/DI and entry timing. Each basket has four portions and a common stop; requested portions stay within quarter budgets. Actual fills can exceed the selected cash budget.</li>'
      '<li>Real ticks start 1 Jan 2026. The year is 75% real ticks with generated ticks earlier; the quarter is 100% real ticks. Not a full year of real-tick validation.</li>'
      '<li>Each window starts flat with $10,000. Quarter need not equal the tail of the annual account because compounding and pre-window positions differ.</li>'
      '<li>No end-of-test closures occurred. All actual closures are retained. Three annual setups / eight portions carried to Sunday. The current broker Friday session ends at 20:55 UTC, the intended 15:55 NY exit in winter. A separate tester-only minimum-lot diagnostic confirmed the 5 Dec close is rejected with “market closed,” despite later historical quotes. On 3 Jul quotes stopped at 16:59:59 UTC, before the intended close. No synthetic Friday fills were inserted. These runs do not fulfil a strict no-weekend guarantee.</li>'
      '<li>Four positions change native trade counts. Setup stats do not inflate signal count. These are broker CFDs, not exchange NQ futures or verified institutional order-flow data.</li>'
      '<li>Frozen settings are research assumptions, not vendor settings. No favourable version selected from a sweep. Overlapping historical windows are not independent confirmation.</li>'
      '<li>No shared portfolio, FTMO guards, other EAs or manual closes modelled. No production changes, deployment or Git push. Stop for review before next idea.</li></ul>')
    out.append('<p><a href="PROTOCOL.txt">Frozen protocol</a> · <a href="RAW.set">Exact preset</a> · <a href="verification.json">Verification</a> · <a href="EXECUTION_FINDINGS.txt">Execution findings</a> · <a href="Diagnostics/availability.json">Availability probe</a> · <a href="Diagnostics/historical-close.json">Native close diagnostic</a> · <a href="summary.json">Summary</a> · <a href="RESULTS.json">Full raw results</a></p></section></main></body></html>')
    page=''.join(out);assert page.count('<svg')==4
    (R/'Results.html').write_text(page,encoding='utf-8');save(R/'summary.json',summary)
    print(json.dumps(dict(report=str(R/'Results.html'),summary=summary,verdict=verdict),indent=2))
if __name__=='__main__':render(verify())
