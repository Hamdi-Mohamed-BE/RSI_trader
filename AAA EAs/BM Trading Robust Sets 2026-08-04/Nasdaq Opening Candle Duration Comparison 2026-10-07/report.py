"""Verify complete native outputs and produce a self-contained offline report."""
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
import gzip, hashlib, html, json, math, re, sys
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(s): return html.unescape(re.sub('<[^>]+>','',s)).replace('\xa0',' ').strip()
def numeric(s): return float(re.search(r'[-+]?\d[\d ]*(?:\.\d+)?',s.replace('%','')).group().replace(' ',''))
def metric(text,label):
    match=re.search(r'>\s*'+re.escape(label)+r':\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>',text,re.S|re.I)
    assert match, label
    return clean(match.group(1))
def fmt(x,n=2): return 'N/A' if x is None else f'{x:.{n}f}'
def row(values): return '<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in values)+'</tr>'
def table(headers,rows): return '<div class="scroll"><table><thead>'+row(headers)+'</thead><tbody>'+''.join(row(x) for x in rows)+'</tbody></table></div>'

def verify(result):
    manifest=result['manifest']; name=manifest['name']; folder=R/'native'/name
    report_bytes=gzip.decompress((folder/'report.htm.gz').read_bytes())
    assert hashlib.sha256(report_bytes).hexdigest()==result['report_sha256']
    text=report_bytes.decode('utf-16')
    assert manifest['preset_sha256']==sha(R.parent/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set')
    assert manifest['protocol_sha256']==sha(R/'PROTOCOL.txt')
    expected_binary=R.parent/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5' if manifest['production'] else R/'OpeningDuration.ex5'
    assert manifest['binary_sha256']==sha(expected_binary)
    trades=result['trades']; n=len(trades); amounts=[t['net_profit'] for t in trades]
    assert int(numeric(metric(text,'Total Trades')))==n
    assert abs(sum(amounts)-numeric(metric(text,'Total Net Profit')))<.03
    assert abs(sum(amounts)-result['summary']['net'])<.015
    assert abs(numeric(metric(text,'Equity Drawdown Relative'))-result['summary']['floating_dd'])<.0001
    s=result['summary']; positive=sum(x for x in amounts if x>0); negative=-sum(x for x in amounts if x<0)
    assert s['wins']==sum(x>0 for x in amounts) and s['losses']==sum(x<0 for x in amounts)
    assert s['flats']==sum(x==0 for x in amounts) and s['trades']==n
    assert abs(s['win_rate']-100*s['wins']/n)<1e-9 if n else s['win_rate'] is None
    assert abs(s['pf']-positive/negative)<1e-9 if negative else s['pf'] is None
    assert abs(s['return_pct']-sum(amounts)/100)<1e-9
    dates=[]; previous=None
    for t in trades:
        op=pd.Timestamp(t['open_time'],tz='UTC'); cl=pd.Timestamp(t['close_time'],tz='UTC')
        ny=op.tz_convert('America/New_York')
        assert ny.strftime('%H:%M')==f"09:{30+manifest['minutes']:02d}"
        assert op>=pd.Timestamp(manifest['start'],tz='UTC') and cl<pd.Timestamp(manifest['end_exclusive'],tz='UTC')
        assert previous is None or previous<=op
        previous=cl; dates.append(ny.date())
        assert t['initial_tp']==0
        assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.02
    assert len(dates)==len(set(dates))
    daily={d:0. for d in pd.date_range(manifest['start'],pd.Timestamp(manifest['end_exclusive'])-pd.Timedelta(days=1))}
    for t in trades: daily[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
    balance=10000.; returns=[]
    for value in daily.values(): returns.append(value/balance); balance+=value
    sharpe=float(np.mean(returns)/np.std(returns,ddof=1)*np.sqrt(365)) if np.std(returns,ddof=1)>0 else None
    assert abs(sharpe-s['daily_realized_sharpe'])<1e-9 if sharpe is not None else s['daily_realized_sharpe'] is None
    if not manifest['production']:
        checks=json.loads((folder/'checks.json').read_text())
        assert len(checks)==result['signal_checks']>0
        # Agent and terminal journals mirror the same native print records.
        checks=list({json.dumps(c,sort_keys=True):c for c in checks}.values())
        for c in checks:
            at=pd.Timestamp(c['at']); candle=pd.Timestamp(c['signal_time']); indicator=pd.Timestamp(c['indicator_time'])
            assert candle+pd.Timedelta(minutes=manifest['minutes'])<=at
            assert indicator+pd.Timedelta(minutes=5)<=at
            assert indicator.minute%5==0
            assert c['side']==(1 if c['close']>c['ema'] else -1 if c['close']<c['ema'] else 0)
        for t in trades:
            matched=[c for c in checks if pd.Timestamp(c['at'])<=pd.Timestamp(t['open_time'])<=pd.Timestamp(c['at'])+pd.Timedelta(seconds=5)]
            assert len(matched)==1 and matched[0]['di_pass']
            assert matched[0]['side']==(1 if t['side']=='Long' else -1)
    return dict(name=name,positions=n,passed=True,checks=['source/preset/report hashes','native cash and count parity','net PF and wins','native floating DD','NY DST and entry timing','one position and entry per NY day','no TP','cost reconciliation','independent daily-realized Sharpe','completed-M5 indicator timing' if not manifest['production'] else 'exact production binary'])

PALETTE={5:'#ffffff',1:'#4fe4b5',3:'#ffcf74',10:'#8baaff',15:'#f48ec8'}
def chart(rows,start,end):
    w=1150; height=350; left=85; right=25; top=24; bottom=60
    span=(pd.Timestamp(end)-pd.Timestamp(start)).total_seconds()
    all_balances=[10000.]
    curves=[]
    for r in rows:
        balance=10000.; points=[(0.,balance)]
        for t in sorted(r['trades'],key=lambda t:t['close_time']):
            sec=(pd.Timestamp(t['close_time'])-pd.Timestamp(start)).total_seconds()
            points.extend([(sec,balance),(sec,balance+t['net_profit'])]); balance+=t['net_profit']
        points.append((span,balance)); all_balances.extend(x[1] for x in points); curves.append((r,points))
    lo=min(all_balances); hi=max(all_balances); padding=max(80,(hi-lo)*.08); lo-=padding; hi+=padding
    x=lambda sec:left+sec/span*(w-left-right)
    y=lambda value:top+(hi-value)/(hi-lo)*(height-top-bottom)
    parts=[f'<svg role="img" aria-label="Realized closing-balance comparison" viewBox="0 0 {w} {height}">']
    for value in np.linspace(lo,hi,5):
        parts.append(f'<path d="M{left},{y(value):.1f}H{w-right}" stroke="#254239"/><text x="{left-8}" y="{y(value)+4:.1f}" text-anchor="end">${value:,.0f}</text>')
    for f in [0,.25,.5,.75,1]:
        date=(pd.Timestamp(start)+pd.Timedelta(seconds=span*f)).strftime('%d %b %y')
        parts.append(f'<text x="{x(span*f):.1f}" y="{height-bottom+24}" text-anchor="middle">{date}</text>')
    for r,points in curves:
        minute=r['manifest']['minutes']; coordinates=' '.join(f'{x(a):.2f},{y(b):.2f}' for a,b in points)
        parts.append(f'<polyline points="{coordinates}" fill="none" stroke="{PALETTE[minute]}" stroke-width="{2.8 if minute==5 else 1.8}"/>')
    parts.append('</svg>')
    legend=' '.join(f'<span class="legend" style="color:{PALETTE[r["manifest"]["minutes"]]}">M{r["manifest"]["minutes"]}'+(' current' if r['manifest']['minutes']==5 else '')+'</span>' for r in rows)
    return ''.join(parts)+'<p>'+legend+'</p>'

def main():
    results=json.loads((R/'RESULTS.json').read_text()); assert len(results)==15
    build=json.loads((R/'BUILD.json').read_text())
    assert build['adapter_source']==sha(R/'OpeningDuration.mq5')
    assert build['adapter_binary']==sha(R/'OpeningDuration.ex5')
    assert build['production_source']==sha(R.parent/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.mq5')
    assert build['production_binary']==sha(R.parent/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5')
    assert len(set((r['manifest']['window'],r['manifest']['minutes']) for r in results))==15
    baseline=next(r for r in results if r['manifest']['window']=='3m' and r['manifest']['minutes']==5)
    original_inputs=baseline['manifest']['inputs']
    for result in results:
        expected=dict(original_inputs)
        if not result['manifest']['production']: expected['InpOpeningCandleTimeframe']=str(result['manifest']['minutes'])
        assert result['manifest']['inputs']==expected,'Other strategy settings changed'
        for key in ['symbol','indicator_timeframe','deposit','risk_percent','model','delay_ms','preset_sha256','protocol_sha256']:
            assert result['manifest'][key]==baseline['manifest'][key]
    checks=[verify(r) for r in results]
    parity=json.loads((R/'BASELINE-PARITY.json').read_text()); assert parity['passed']
    a=json.loads((R/'native/3m-M5-PRODUCTION/results.json').read_text()); b=json.loads((R/'native/3m-M5/results.json').read_text())
    for first,second in zip(a['trades'],b['trades']):
        assert {k:v for k,v in first.items() if k not in ['ea','source']}=={k:v for k,v in second.items() if k not in ['ea','source']}
    assert len(a['trades'])==len(b['trades'])
    save(R/'VERIFICATION.json',dict(passed=True,baseline_parity=parity,runs=checks,verified_positions=sum(c['positions'] for c in checks)))
    body='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nasdaq opening-candle duration comparison</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#07130f;color:#effbf5;font:15px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:32px 22px}h1{font-size:clamp(32px,5vw,60px);line-height:1.1;max-width:1100px}h2{font-size:27px}p{color:#aec9bc}section{background:#0a1c15;border:1px solid #28493a;border-radius:18px;padding:24px;margin:24px 0}.notice{border-color:#837139;background:#242817;color:#ffe8a7}.tag{color:#7df0bd;letter-spacing:.16em;font-size:12px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}td{padding:11px;border-bottom:1px solid #244335;text-align:right}td:first-child{text-align:left}thead{color:#85f0c0;background:#11291d}svg{width:100%;height:auto;display:block}svg text{fill:#9ab8a8;font:12px system-ui}.legend{display:inline-block;margin:0 16px 0 0}a{color:#8bf2be}details{border-top:1px solid #28493a;padding:12px 0}summary{cursor:pointer;color:#9afbc9}.baseline{color:#fff}code{overflow-wrap:anywhere}li{margin:8px 0}.note{font-size:13px}nav a{margin-right:22px}</style></head><body><main>
<p class="tag">CALYX · RESEARCH ONLY · 7 OCTOBER 2026</p><h1>Nasdaq momentum.<br>Change only the first candle.</h1>
<p>First 09:30 New York candle: 1, 3, 5 (current BAT default), 10 or 15 minutes. EMA12, DI14 and ATR14 trailing stay on M5. Exness USTEC CFD · $10,000 per fresh-window run · selected 1% equity stop risk.</p>
<section class="notice"><h2>Controlled comparison—not a live change</h2><p>All variants retain the deployed 0.60%-of-price initial stop, no TP, 6×ATR trail from +1R, DI agreement, overnight/weekend holding and one-position limit. Only the opening-candle duration changes. The M5 adapter matched the byte-identical production binary trade for trade over the full three-month window before other variants were accepted.</p><p>Earlier-than-09:35 entries use the latest completed M5 indicators, not the still-forming 09:30 M5 candle. These are retrospective tests, not untouched out-of-sample validation. Short-window win rates and streaks are unstable; no version is promoted automatically.</p></section>
<nav><a href="#3m">3 months</a><a href="#6m">6 months</a><a href="#1y">1 year</a><a href="VERIFICATION.json">Verification</a><a href="PROTOCOL.txt">Frozen rules</a></nav>
'''
    summary_rows=[]
    for window,label in [('3m','Last 3 months'),('6m','Last 6 months'),('1y','Last year')]:
        rows=sorted([r for r in results if r['manifest']['window']==window],key=lambda r:r['manifest']['minutes'])
        current=next(r for r in rows if r['manifest']['minutes']==5); start=current['manifest']['start']; end=current['manifest']['end_exclusive']
        last=(pd.Timestamp(end)-pd.Timedelta(days=1)).strftime('%d %B %Y'); first=pd.Timestamp(start).strftime('%d %B %Y')
        table_rows=[]
        for r in rows:
            m=r['manifest']['minutes']; s=r['summary']; delta=s['return_pct']-current['summary']['return_pct']
            values=[f'M{m}'+(' — CURRENT' if m==5 else ''),f'09:{30+m:02d}',s['trades'],f"{fmt(s['win_rate'],1)}%",fmt(s['pf']),f"{s['return_pct']:+.2f}%",f'{delta:+.2f} pp',f"{s['floating_dd']:.2f}%",fmt(s['daily_realized_sharpe']),f"{s['max_win_streak']} / {s['max_loss_streak']}",s['boundary_exits'],r['native']['history_quality']]
            table_rows.append(values); summary_rows.append(dict(window=window,minutes=m,**s,return_difference_pp=delta,history_quality=r['native']['history_quality']))
        body+=f'<section id="{window}"><h2>{label}</h2><p>{first}–{last} inclusive. Every version starts flat at $10,000; these are fresh-window runs, not slices from the annual test.</p>'
        body+=table(['Opening candle','Entry NY','Trades','Net win rate','Net PF','Return','vs M5','Max floating DD','Daily realized Sharpe','Max W / L streak','End-close trades','History quality'],table_rows)
        body+=chart(rows,start,end)+'<p class="note">Graph shows realized closing balance, not floating equity; maximum floating drawdown comes separately from the native MT5 report. All curves use actual dates. Entry-time gaps can occur while a prior trade is still open.</p>'
        for r in rows:
            m=r['manifest']['minutes']; s=r['summary']; name=r['manifest']['name']
            body+=f'<details><summary>M{m} trade breakdown · {s["trades"]} trades · net ${s["net"]:+,.2f}</summary><p>Commission ${s["commission"]:,.2f}; swap ${s["swap"]:,.2f}. Test-end liquidations: {s["boundary_exits"]}, net ${s["boundary_net"]:+,.2f}. Native MT5 Sharpe: {r["native"]["sharpe_ratio"]}; headline daily-realized Sharpe uses a consistent calendar-day convention.</p>'
            ledger=[]
            for t in r['trades']:
                exit='TEST-END liquidation' if t['boundary_exit'] else 'Stop / trailing' if t['exit_comment'].lower().startswith('sl') else t['exit_comment']
                ledger.append([t['number'],t['side'],t['open_ny'],t['close_ny'],t['volume'],f"{t['open_price']:,.2f}",f"{t['initial_sl']:,.2f}",f"{t['net_profit']:+,.2f}",f"{t['hold_hours']:.2f}",exit])
            body+=table(['#','Side','Entry New York','Exit New York','Lots','Entry','Initial SL','Net $','Hours','Exit'],ledger)
            body+=f'<p><a href="native/{name}/trades.csv">Trade CSV</a> · <a href="native/{name}/manifest.json">Exact settings and fingerprints</a></p></details>'
        body+='</section>'
    body+='''<section><h2>Limits and interpretation</h2><ul>
<li>No EMA/DI/ATR retuning, added body-direction filter, TP, ADX threshold, optimization or portfolio overlay. Indicator and trailing timeframe remains M5 in every variant.</li>
<li>Original management code is retained, including M5-bar extremes in its trailing calculation. For M1/M3 entries inside a developing M5 bar, that bar can include prices printed before entry; these are already-known prices, not future data. This experiment does not rewrite that production behavior.</li>
<li>Native MT5 Every Tick Based on Real Ticks, 150 ms delay, historical bid/ask, commission and swap. Any older generated or unavailable real-tick history is reflected in each report's history-quality field and tick notes. The one-year window includes history older than the 2026 real-tick cache.</li>
<li>Net PF, win rate and streaks group entire positions after commission and swap. Daily-realized Sharpe uses all calendar days and sqrt(365); it is not the risk of intraday floating equity.</li>
<li>Production upward/minimum-lot sizing is unchanged; selected 1% is not a guaranteed maximum loss. Initial stop distance is 0.60% of price, not 0.60% of account balance.</li>
<li>Test-end liquidation is included to avoid hiding open P&amp;L, but is not a normal strategy exit. Boundary counts and P&amp;L are shown in every trade breakdown.</li>
<li>Current rules were deployed on 28 September 2026. Most of these retrospective windows predate selection; they cannot establish a newly untouched out-of-sample edge. Choosing the best of these five requires later validation.</li>
<li>The three date windows overlap. They are separately simulated with fresh balances, not three statistically independent confirmations. Different entry durations can also change later trade availability when a prior position stays open.</li>
<li>Live MT5, BATs, website, production source and compiled binary remained unchanged. FTMO guard/adaptive 0.25× risk scaling and other portfolio EAs are not part of this standalone comparison.</li>
</ul><p><a href="RESULTS.json">Full native results</a> · <a href="SUMMARY.json">Comparison summaries</a> · <a href="BASELINE-PARITY.json">Production parity</a> · <a href="VERIFICATION.json">Independent reconciliation</a></p></section></main></body></html>'''
    (R/'Results.html').write_text(body,encoding='utf-8'); save(R/'SUMMARY.json',summary_rows)
    parser=HTMLParser(); parser.feed(body); assert body.count('<svg ')==3 and body.count('<details>')==15
    save(R/'HTML-QA.json',dict(parsed=True,charts=3,trade_breakdowns=15,tables=body.count('<table>'),bytes=len(body.encode())))
    print(json.dumps(dict(report=str(R/'Results.html'),summaries=summary_rows,verified_positions=sum(c['positions'] for c in checks)),indent=2),flush=True)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='verify':
        completed=json.loads((R/'RESULTS.json').read_text())
        audit=[verify(r) for r in completed]
        print(json.dumps(dict(passed=True,runs=len(audit),positions=sum(c['positions'] for c in audit),names=[c['name'] for c in audit]),indent=2))
    else: main()
