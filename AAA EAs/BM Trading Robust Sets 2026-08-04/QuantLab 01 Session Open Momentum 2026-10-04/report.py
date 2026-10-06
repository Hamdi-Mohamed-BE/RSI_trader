"""Verify ten frozen native tests and produce the first-idea offline report."""
from pathlib import Path
import csv,gzip,hashlib,html,json,math,re
from datetime import datetime
R=Path(__file__).resolve().parent
LABELS={'CURRENT':'Current · DI ON','CURRENT_NO_DI':'Current · DI OFF','OLD':'Old · DI ON',
        'VIDEO_LITERAL':'Video reconstruction · literal','VIDEO_SYMMETRIC':'Video reconstruction · symmetric'}
COLORS={'CURRENT':'#79f2c4','CURRENT_NO_DI':'#75aaff','OLD':'#c4a2ee','VIDEO_LITERAL':'#ffe184','VIDEO_SYMMETRIC':'#ff96aa'}
ORDER=list(LABELS)
WINDOWS={'1Y':('2025-10-04','2026-10-04','4 Oct 2025–3 Oct 2026'),
         '3M':('2026-07-04','2026-10-04','4 Jul–3 Oct 2026')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def money(x):return f'{x:+,.2f}'
def esc(x):return html.escape(str(x))
def cells(xs):return '<tr>'+''.join('<td>'+esc(x)+'</td>' for x in xs)+'</tr>'
def table(head,rows):return '<div class="scroll"><table><thead>'+cells(head)+'</thead><tbody>'+''.join(cells(x) for x in rows)+'</tbody></table></div>'
def streaks(ts):
    w=l=mw=ml=0
    for t in sorted(ts,key=lambda t:t['close_time']):
        if t['net_profit']>0:w+=1;l=0
        elif t['net_profit']<0:l+=1;w=0
        else:w=l=0
        mw=max(mw,w);ml=max(ml,l)
    return mw,ml
def extra(r):
    ts=r['trades'];wins=[t['net_profit'] for t in ts if t['net_profit']>0];losses=[t['net_profit'] for t in ts if t['net_profit']<0]
    mw,ml=streaks(ts)
    return dict(max_win_streak=mw,max_loss_streak=ml,avg_win_usd=sum(wins)/len(wins) if wins else None,
                avg_loss_usd=sum(losses)/len(losses) if losses else None,
                avg_hold_hours=sum(t['hold_hours'] for t in ts)/len(ts) if ts else 0,
                boundary_net_usd=sum(t['net_profit'] for t in ts if t['boundary_exit']),
                overnight_positions=sum(t['open_ny'][:10]!=t['close_ny'][:10] for t in ts))
def chart(rows,window):
    """Calendar-aligned closing balances only. Never label this floating equity."""
    start,end,_=WINDOWS[window];a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)
    width,height=1100,310;left,right,top,bottom=88,25,25,45
    ys=[10000.]
    paths=[]
    for r in rows:
        balance=10000.;pts=[(a,balance)]
        for t in sorted(r['trades'],key=lambda t:t['close_time']):
            balance+=t['net_profit'];pts.append((datetime.fromisoformat(t['close_time']),balance));ys.append(balance)
        pts.append((b,balance));paths.append((r['manifest']['version'],pts))
    low=min(ys);high=max(ys);pad=max(80.,(high-low)*.08);low-=pad;high+=pad
    def x(t):return left+(t-a).total_seconds()/(b-a).total_seconds()*(width-left-right)
    def y(v):return top+(high-v)/(high-low)*(height-top-bottom)
    s=f'<svg role="img" aria-label="Closed-balance comparison by date; not floating equity" viewBox="0 0 {width} {height}">'
    for i in range(5):
        val=low+(high-low)*i/4;yy=y(val)
        s+=f'<line x1="{left}" y1="{yy:.2f}" x2="{width-right}" y2="{yy:.2f}" stroke="#254b3c"/><text x="8" y="{yy+4:.2f}" fill="#a9c6b8" font-size="13">${val:,.0f}</text>'
    for key,pts in paths:
        d=f'M{x(pts[0][0]):.2f},{y(pts[0][1]):.2f}'
        for when,value in pts[1:]:d+=f'H{x(when):.2f}V{y(value):.2f}'
        s+=f'<path d="{d}" fill="none" stroke="{COLORS[key]}" stroke-width="2.2"/>'
    s+=f'<text x="{left}" y="{height-12}" fill="#a9c6b8" font-size="13">{start}</text><text x="{width-right}" y="{height-12}" fill="#a9c6b8" font-size="13" text-anchor="end">{end} exclusive</text></svg>'
    s+='<div class="legend">'+''.join(f'<span style="color:{COLORS[r["manifest"]["version"]]}">● {esc(LABELS[r["manifest"]["version"]])}</span>' for r in rows)+'</div>'
    return s
def verify(rows):
    assert len(rows)==10
    index={(r['manifest']['window'],r['manifest']['version']):r for r in rows}
    assert set(index)=={(w,n) for w in WINDOWS for n in ORDER}
    assert json.loads((R/'parity.json').read_text())['passed']
    build=json.loads((R/'build.json').read_text())
    assert sha(R/'EA/Calyx Session Open Momentum Research.mq5')==build['source_sha256']
    assert sha(R/'EA/Calyx Session Open Momentum Research.ex5')==build['binary_sha256']
    checks=[]
    for (window,name),r in index.items():
        m=r['manifest'];n=r['native'];ts=r['trades'];folder=R/'native'/window/name
        assert m['protocol_sha256']==sha(R/'PROTOCOL.txt')
        assert m['deposit']==10000 and m['risk_percent']==1 and m['delay_ms']==150 and m['model']==4
        assert m['start'].replace('.','-')==WINDOWS[window][0] and m['end_exclusive'].replace('.','-')==WINDOWS[window][1]
        assert sha(Path(m['expert_source']))==m['binary_sha256']
        assert sha(Path(m['settings_source']))==m['set_sha256']
        assert hashlib.sha256(gzip.decompress((folder/'report.htm.gz').read_bytes())).hexdigest()==r['report_sha256']
        assert len(ts)==n['trades'] and abs(sum(t['net_profit'] for t in ts)-n['net_profit'])<.015
        pos=sum(t['net_profit'] for t in ts if t['net_profit']>0);neg=-sum(t['net_profit'] for t in ts if t['net_profit']<0)
        assert r['net_pf']==(pos/neg if neg else None)
        assert len({t['open_ny'][:10] for t in ts})==len(ts)
        prior=None
        for t in ts:
            assert t['open_ny'][11:16]=='09:35'
            assert prior is None or prior<=t['open_time']
            prior=t['close_time']
            assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.015
            when=t['open_time'].replace('-','.').replace('T',' ')
            match=[o for o in r['orders'] if o[0]==when and o[10]==t['entry_comment']]
            assert len(match)==1
            t['initial_sl']=float(match[0][6].replace(' ',''))
            t['initial_tp']=float(match[0][7].replace(' ','')) if match[0][7] else None
            assert (t['initial_sl']<t['open_price']) if t['side']=='Long' else (t['initial_sl']>t['open_price'])
            if name!='OLD':assert t['initial_tp'] is None
            if t['exit_comment'].startswith('sl '):
                v=float(t['exit_comment'].split()[1]);profit=v>t['open_price'] if t['side']=='Long' else v<t['open_price']
                t['exit_reason']='ATR trailing stop in profit' if profit and name!='OLD' else 'Protective stop'
        if window=='3M':assert n['history_quality']=='100% real ticks'
        r['extra']=extra(r)
        save(folder/'trades.json',ts)
        with (folder/'trades.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(ts[0]));w.writeheader();w.writerows(ts)
        save(folder/'results.json',r)
        checks.append(dict(window=window,version=name,positions=len(ts),passed=True,history_quality=n['history_quality'],
                           end_liquidations=r['end_liquidations'],stop_modify_failures=r['stop_modify_failures']))
    for window in WINDOWS:
        a=index[window,'CURRENT'];b=index[window,'CURRENT_NO_DI']
        assert a['manifest']['binary_sha256']==b['manifest']['binary_sha256']
        def differences(a,b):
            aa=a['manifest']['inputs'];bb=b['manifest']['inputs']
            return {k:(aa.get(k),bb.get(k)) for k in set(aa)|set(bb) if aa.get(k)!=bb.get(k)}
        assert differences(a,b)=={'InpRequireDIAgreement':('true','false')}
        for name,mode in [('VIDEO_LITERAL','1'),('VIDEO_SYMMETRIC','2')]:
            r=index[window,name]
            assert differences(b,r)=={'InpSOMBodyMode':(None,mode)}
            assert r['manifest']['binary_sha256']==build['binary_sha256']
        assert differences(index[window,'VIDEO_LITERAL'],index[window,'VIDEO_SYMMETRIC'])=={'InpSOMBodyMode':('1','2')}
    save(R/'verification.json',dict(parity='Passed exact original trades and metrics',native_runs=checks,
         checks='Source, executable, preset, protocol and native-report hashes; exact one-factor inputs; complete net-position costs; NY entries; unique daily entries; no overlapping positions; SL/TP; counts; real-tick coverage; boundary exits.'))
    save(R/'RESULTS.json',rows)
    return index

def render(index):
    out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QuantLab idea 1 · Session Open Momentum</title><style>',
    ':root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#071410;color:#eaf8ef;font:15px/1.6 system-ui,sans-serif}main{max-width:1510px;margin:auto;padding:42px 24px}h1{font-size:clamp(32px,5vw,58px);line-height:1.12;max-width:1000px}h2{font-size:24px}h3{font-size:19px}p{color:#b5d0c2}.tag{color:#7dffd0;font-size:12px;letter-spacing:.13em}.notice{border:1px solid #897234;background:#292a18;color:#ffe9ad;border-radius:12px;padding:18px;margin:20px 0}section{padding:24px;background:#0c1e17;border:1px solid #27493b;border-radius:16px;margin:24px 0}.scroll{overflow-x:auto}table{border-collapse:collapse;white-space:nowrap;width:100%;font-size:13px}td{padding:12px;border-bottom:1px solid #274539;text-align:right}td:first-child{text-align:left}thead{background:#122a20;color:#92f8ca}svg{width:100%;height:auto;display:block;margin:20px 0}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px}a{color:#8bf1c3}details{border-top:1px solid #2a4e3e;margin:20px 0;padding-top:18px}summary{cursor:pointer;font-weight:650}li{margin:8px 0}code{overflow-wrap:anywhere}.muted{font-size:13px;color:#94b3a2}</style></head><body><main>',
    '<p class="tag">CALYX · FIRST IDEA ONLY · FROZEN NATIVE MT5 COMPARISON</p><h1>Session Open Momentum.<br>Does the candle confirmation help?</h1>',
    '<p>Five versions, tested separately on Exness USTEC M5. Each starts flat with $10,000 and 1% planned equity risk per entry, before existing broker-lot rounding. 150 ms execution delay; native spread, commission and swap included.</p>',
    '<div class="notice">Independent public-video reconstruction—not QuantLab’s proprietary EA. Its detailed stop and trailing settings are not public. No parameters were optimised in this experiment. This is retrospective research, not a passed full pipeline or a forecast.</div>',
    '<section><h2>Exactly what was recreated</h2>']
    rules=[
      ['Entry window','Completed first New York M5 candle, 09:30–09:35. Entry on the first tick of the next bar, with NY daylight-saving conversion.'],
      ['Video literal','BUY: bullish candle and close above EMA12. SELL: close below EMA12; short candle colour is not explicit in the transcript. DI OFF.'],
      ['Video symmetric','BUY as above; SELL additionally requires bearish candle. This extra sell requirement is an assumption, not a verified vendor rule. DI OFF.'],
      ['Assumed exits for both','Current EA management unchanged: initial SL 0.60% of entry price, ATR14 M5 × 6 trail after +1 initial R; no fixed target, no break-even, no daily close.'],
      ['Position limits','One position at a time, at most one new entry per NY day. Overnight/weekend holding allowed; an existing position suppresses the next entry.'],
      ['Current controls','Same compiled current EA tested with DI ON and DI OFF, close versus EMA12 without candle-colour confirmation.'],
      ['Old control','Previous DI-on EA, 4 × ATR14 initial stop, fixed 2.5R TP and 15:55 New York close. It changes exits and stop sizing, so it is not a one-factor entry comparison.'],
      ['Parity check','Research mode zero reproduced all 10 original DI-off two-week trades, prices, lots, costs and native metrics exactly.']]
    out.append(table(['Component','Rule'],rules))
    out.append('<p><a href="https://api-quantlab.com/algorithmen/session-open-momentum" target="_blank" rel="noopener">QuantLab public description</a> · Detailed rules are subscription-only. The vendor’s long-period headline numbers are not comparable to these date windows and broker data.</p><p>Changing entry confirmation also changes carried-position availability and subsequent compounding; this is not simply removing a subset of losing trades.</p></section>')
    all_summary=[]
    for window in WINDOWS:
        rs=[index[window,n] for n in ORDER];title=WINDOWS[window][2]
        out.append(f'<section id="{window}"><p class="tag">{window} · {title.upper()}</p><h2>Measured performance</h2>')
        body=[]
        for r in rs:
            n=r['native'];e=r['extra'];name=r['manifest']['version']
            values=[LABELS[name],money(n['net_profit']),f"{100*n['net_profit']/10000:.2f}%",r['positions'],
                    f"{r['net_win_rate_pct']:.1f}%",'N/A' if r['net_pf'] is None else f"{r['net_pf']:.3f}",
                    f"{n['equity_dd_pct']:.2f}%",f"{n['sharpe_ratio']:.2f}",e['max_win_streak'],e['max_loss_streak'],
                    r['end_liquidations'],n['history_quality']]
            body.append(values)
            all_summary.append(dict(window=window,version=name,label=LABELS[name],net_usd=n['net_profit'],
               return_pct=100*n['net_profit']/10000,trades=r['positions'],win_rate_pct=r['net_win_rate_pct'],
               net_pf=r['net_pf'],equity_dd_pct=n['equity_dd_pct'],native_sharpe=n['sharpe_ratio'],**e))
        out.append(table(['Version','Net $','Return','Trades','Net win rate','Net PF','Max equity DD','MT5 Sharpe','Max W streak','Max L streak','End closes','Tick quality'],body))
        out.append('<p class="muted">Net PF and win rate use complete closed positions including commission and swap. MT5 Sharpe is reproduced unchanged from the native report; it is not an independently computed annualised daily-return Sharpe. Streaks follow closing order. End-of-test liquidations stay in all headline figures.</p>')
        out.append('<h3>Closing-balance comparison</h3><p>Five independent tests on a common calendar—not a shared portfolio. This graph excludes floating P&amp;L; maximum equity drawdown in the table is measured separately by MT5.</p>'+chart(rs,window))
        out.append(table(['Version','Average win $','Average loss $','Average holding hours','Overnight positions','Boundary P&L $','Commission + swap $'],
              [[LABELS[r['manifest']['version']],money(r['extra']['avg_win_usd']) if r['extra']['avg_win_usd'] is not None else 'N/A',
                money(r['extra']['avg_loss_usd']) if r['extra']['avg_loss_usd'] is not None else 'N/A',
                f"{r['extra']['avg_hold_hours']:.1f}",r['extra']['overnight_positions'],money(r['extra']['boundary_net_usd']),
                money(r['commission']+r['swap'])] for r in rs]))
        for r in rs:
            name=r['manifest']['version']
            out.append(f'<details><summary>{esc(LABELS[name])} · graph and {r["positions"]} trades</summary>'+chart([r],window))
            ts=[[t['number'],t['side'],t['open_ny'],t['close_ny'],t['volume'],f"{t['open_price']:,.2f}",f"{t['close_price']:,.2f}",
                 f"{t['initial_sl']:,.2f}",'None' if t['initial_tp'] is None else f"{t['initial_tp']:,.2f}",
                 money(t['net_profit']),t['hold_hours'],t['exit_reason']] for t in r['trades']]
            out.append(table(['#','Side','Entry NY','Exit NY','Lots','Entry price','Exit price','Initial SL','Initial TP','Net $','Hours','Exit'],ts))
            out.append(f'<p><a href="native/{window}/{name}/trades.csv">Trade CSV</a> · <a href="native/{window}/{name}/results.json">Native measurements and exact inputs</a></p></details>')
        out.append('</section>')
    out.append('<section><h2>Data and execution limitations</h2><ul>'
      '<li>Real recorded ticks begin on 1 January 2026. The one-year tests are 75% real ticks with generated ticks earlier; the three-month tests are 100% real ticks. This is not a full year of real-tick validation.</li>'
      '<li>One-year and three-month tests both begin flat. A carried position from before the three-month window is deliberately not inherited, so that window does not have to equal the tail of the year’s run.</li>'
      '<li>Current production lot rounding up/minimum-lot behaviour is retained. Actual planned risk can exceed 1%, and execution gaps can exceed it further.</li>'
      '<li>The inherited ATR manager can repeatedly attempt stop updates during broker market closures, and sometimes receive invalid-stop rejections. Rejected updates keep the existing accepted stop; later retries and their actual outcomes remain in the test. No assumed successful fills or stop changes were inserted.</li>'
      '<li>No shared portfolio capital/margin, adaptive 0.25× Nasdaq multiplier, FTMO limits, manual closes or other EAs. These figures do not reproduce your live account or predict FTMO passing.</li>'
      '<li>No stop/trailing optimisation, independent holdout, cost-stress, bootstrap or Monte Carlo validation was done at this step. The current configuration was selected in September 2026, so most of the tested historical window predates that selection. Recent historical success is not proof of an edge.</li>'
      '<li>No live EA, installer, website, trading permission or Git remote was changed. NQBlade and the UK100/Gold ideas have not been started; awaiting your review.</li></ul>')
    out.append(table(['Window','Version','Rejected stop-update attempts'],[[w,LABELS[n],index[w,n]['stop_modify_failures']] for w in WINDOWS for n in ORDER]))
    out.append('<p><a href="PROTOCOL.txt">Frozen protocol</a> · <a href="parity.json">Parity test</a> · <a href="verification.json">Verification</a> · <a href="summary.json">Summary data</a> · <a href="RESULTS.json">Full results</a></p></section></main></body></html>')
    (R/'Results.html').write_text(''.join(out),encoding='utf-8')
    save(R/'summary.json',all_summary)
    print(json.dumps(dict(report=str(R/'Results.html'),summary=all_summary),indent=2))
if __name__=='__main__':
    rows=json.loads((R/'RESULTS.json').read_text())
    render(verify(rows))
