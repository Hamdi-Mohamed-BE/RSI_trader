"""Readable comparison of the immutable native tests, with full trade drill-down."""
from pathlib import Path
from datetime import datetime
import gzip,html,json,re,sys
R=Path(__file__).resolve().parent
def esc(v):return html.escape(str(v))
def f(v,places=2):return f'{v:,.{places}f}' if v is not None else '—'

def execution_audit(folder):
 # The tester and agent both emit each failure. Count unique request messages,
 # not raw keyword mentions, and distinguish stop updates from entry failures.
 path=folder/'journal.txt.gz'
 if not path.exists():return {'note':'Exact cached control; raw warning mentions retained below.'}
 journal=gzip.decompress(path.read_bytes()).decode('utf-8')
 out={}
 for label,reason in [('invalid_stops','Invalid stops'),('market_closed','Market closed')]:
  messages=sorted(set(re.findall(r'(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d\s+failed [^\r\n]*\['+re.escape(reason)+r'\])',journal,re.I)))
  out[label]={'unique_failed_requests':len(messages),'stop_modifications':sum('failed modify ' in x for x in messages),'other_requests':sum('failed modify ' not in x for x in messages),'examples':messages[:3]}
 return out
def table(headers,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def curve(trades,color):
 # Closed-trade balance only; native floating DD is shown separately in the metrics.
 if not trades:return '<p>No trades.</p>'
 start=datetime.fromisoformat(trades[0]['open_time']);end=datetime.fromisoformat(trades[-1]['close_time'])
 points=[(start,0.0)];value=0
 for t in trades:value+=t['net_profit']/100;points.append((datetime.fromisoformat(t['close_time']),value))
 low=min(0,min(v for t,v in points));high=max(0,max(v for t,v in points));span=max(1,high-low)
 coordinates=[]
 for t,v in points:coordinates.append(f'{50+860*(t-start).total_seconds()/max(1,(end-start).total_seconds()):.1f},{175-130*(v-low)/span:.1f}')
 zero=175-130*(0-low)/span
 return f'<svg viewBox="0 0 960 220" role="img" aria-label="Closed-balance return curve"><line x1="50" x2="910" y1="{zero}" y2="{zero}" stroke="#52655f" stroke-dasharray="4 4"/><polyline points="'+ ' '.join(coordinates)+f'" fill="none" stroke="{color}" stroke-width="2.5"/><text x="8" y="45">{high:.1f}%</text><text x="8" y="180">{low:.1f}%</text><text x="50" y="205">{start.date()}</text><text x="775" y="205">{end.date()}</text></svg>'
def main(full=False):
 data=json.loads((R/('FULL_RESULTS.json' if full else 'RESULTS.json')).read_text());results=data['results']
 assert len(results)==(10 if full else 6) and data['production_unchanged']
 labels={'DE30':'Germany / DAX (DE30)','USTEC':'Nasdaq (USTEC)'}
 rows=[]
 for result in results:
  m=result['metrics'];case=result['manifest'];pf=m['net_profit_factor']
  rows.append([esc(labels[case['symbol']]),esc(case['window']),esc(case['start'])+' → 2026-10-06',f"{m['return_pct']:+.2f}%",m['trades'],f(m['win_rate_pct'])+'%',f(pf),f(m['floating_equity_dd_pct'])+'%',f(m['sharpe_ratio']),f"{m['maximum_win_streak']} / {m['maximum_loss_streak']}"])
 header='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Nasdaq 5M → Germany: unchanged rules</title><style>
body{margin:0;background:#071511;color:#e6fff5;font:16px/1.65 system-ui}main{max-width:1330px;padding:34px 24px;margin:auto}h1{font-size:38px;line-height:1.15}h2{color:#6ef5c5}section{background:#10231c;border:1px solid #2e4c3e;border-radius:16px;padding:22px;margin:24px 0}p{color:#b7d5c5}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;text-align:left;border-bottom:1px solid #2e4c3e;white-space:nowrap}th{color:#67e8ba}.scroll{overflow-x:auto}.warning{background:#282613;border:1px solid #8a7128;padding:16px;border-radius:12px;color:#ffe59d}a{color:#72eed1}summary{cursor:pointer;color:#66edc0;margin:14px 0}svg{width:100%;background:#071511;border-radius:10px}svg text{font:12px system-ui;fill:#a5c7b5}.muted{font-size:13px;color:#a0b8aa}code{color:#79f3ce}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 monospace}
</style><main><h1>Current Nasdaq 5M momentum<br>Transferred to Germany — unchanged rules.</h1>
<p>Raw transfer test. Same production executable, same DI-enabled current preset, 1% of current equity per trade, $10,000 starting balance. Independent fresh-account runs; not an optimisation or combined portfolio. Live EAs, BATs and website settings are unchanged.</p>
<section><h2>Rules retained</h2><p>First 09:30–09:35 New York M5 candle: bullish above EMA12 → buy; bearish below EMA12 → sell. DI14 must agree with direction. Initial stop 0.60% of entry price; no fixed target. ATR14 × 6 trailing starts at +1R. No forced session exit or maximum hold; overnight/weekend holding is allowed. No adaptive portfolio/daily-stop overlay in these isolated comparisons.</p><div class="warning">This is the US-opening-time strategy on a German instrument, NOT a Frankfurt-opening strategy. Germany's morning opening time was not substituted or optimised. Planned 1% stop risk is not a guaranteed maximum: retained broker-volume rounding, minimum lots, costs, gaps and execution can exceed it.</div></section>
<section><h2>Side-by-side results</h2>'''
 doc=header+table(['Asset','Window','Exact dates (inclusive)','Net return','Trades','Net win rate','Net PF','Max relative equity DD','MT5 Sharpe','Win / loss streak'],rows)
 doc+='''<p class="muted">PF and win rate above are calculated from each complete position's net cash result, including entry/exit commissions and swaps; MT5's native Sharpe and maximum relative floating-equity drawdown are retained. Sharpe is the native tester statistic, not an independently calculated annualised daily-equity Sharpe. Test-end liquidation is included. Tables cover independently restarted tests, so the short windows are not slices of the annual account curve.</p><div class="warning">Recent-period conclusion: the unchanged New York-opening rules lost money on Germany in the 3-month, 6-month and 1-year tests. The recent 3- and 6-month German runs were 100% real ticks and both had PF below 1. Longer-run profits do not remove that recent weakness, and their mostly generated-tick history limits confidence. Germany's own opening session would be a separate research test.</div></section>
<section><h2>Dates and data quality</h2><p>3 months: 7 July–6 October 2026. 6 months: 7 April–6 October 2026. 1 year: 7 October 2025–6 October 2026.'''
 if full:
  doc+=' 3 years: 7 October 2023–6 October 2026. 5 years: 7 October 2021–6 October 2026.'
 doc+=''' End-exclusive: 7 October 2026 00:00 UTC / broker tester clock with zero offset. Native M5 test, model 4 (real ticks where available), 150ms execution delay, USD hedging account, tester leverage 1:2000; symbol-specific broker margin/volume rules still apply.</p><div class="warning">Local real-tick history starts January 2026. The 1-/3-/5-year runs contain older generated ticks, with most of the 3-/5-year histories generated: do NOT treat them as clean all-real-tick validations. Per-run warnings and native real-tick percentages below document the coverage. Overlapping windows are descriptive comparisons, not independent out-of-sample validation.</div><p>Exness labels its German DAX CFD <code>DE30</code>; that broker symbol is used here. <a href="https://get.exness.help/hc/en-us/articles/17854383867548-Indices" target="_blank" rel="noopener">Exness instrument specifications</a>. This is not a DAX futures test or another broker's DE40 feed.</p></section>'''
 audits={}
 for result in results:
  case=result['manifest'];m=result['metrics'];folder=R/'native'/(case['symbol']+'-'+case['window']);trades=json.loads((folder/'trades.json').read_text())
  subtitle=f"{labels[case['symbol']]} · {case['window']}"
  doc+='<section><h2>'+esc(subtitle)+'</h2>'+curve(trades,'#68f5c0' if case['symbol']=='DE30' else '#f4c262')
  doc+='<p class="muted">Curve: closed-trade balance return, not floating equity. Start $10,000. Net profit $'+f(m['net_profit'])+'. Median hold '+f(m['median_hold_hours'])+' hours. '+str(result['boundary_exits'])+' test-end liquidation(s).</p>'
  doc+='<p>Native history quality: '+esc(m['history_quality'])+'. Data classification: '+esc(result['data_quality'])+'.</p>'
  audit=execution_audit(folder);audits[case['symbol']+'-'+case['window']]=audit
  if result['warnings']['market_closed'] or result['warnings']['invalid_stops']:
   doc+='<p class="warning">Execution caveat: the unchanged EA attempted trailing-stop updates during broker-closed periods. Rejected updates leave the prior stop in place; the results include this behaviour. Deduplicated request counts and invalid-stop failures are documented below. Raw keyword counts are log mentions, not separate trades or unique failures.</p>'
  doc+='<details><summary>Execution warnings and tick coverage</summary><pre>'+esc(json.dumps(dict(unique_requests=audit,raw_log_keyword_mentions=result['warnings'],tick_notes=result['tick_notes']),indent=2))+'</pre></details>'
  trade_rows=[[t['number'],esc(t['open_time'].replace('T',' ')),esc(t['close_time'].replace('T',' ')),esc(t['side']),f(t['volume'],4),f(t['open_price']),f(t['close_price']),f(t['commission']),f(t['swap']),f(t['net_profit']),esc(t['exit_comment'])] for t in trades]
  doc+='<details><summary>Full trade breakdown — '+str(len(trades))+' trades</summary>'+table(['#','Entry (server UTC)','Exit','Side','Lots','Entry price','Exit price','Commission','Swap','Net $','Exit reason'],trade_rows)+'</details>'
  doc+='<details><summary>Frozen exact settings and source fingerprint</summary><pre>'+esc(json.dumps(case,indent=2))+'</pre></details></section>'
 doc+='<p class="muted">Research results, not a promise of future performance. Production source, compiled executable and preset hashes were checked unchanged at completion. No live deployment or parameter search performed.</p></main></html>'
 output=R/('FullPeriods.html' if full else 'Results.html')
 output.write_text(doc,encoding='utf-8')
 (R/('FullExecutionAudit.json' if full else 'ExecutionAudit.json')).write_text(json.dumps(audits,indent=2),encoding='utf-8')
 print('Created:',output)
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main('--full' in sys.argv)
