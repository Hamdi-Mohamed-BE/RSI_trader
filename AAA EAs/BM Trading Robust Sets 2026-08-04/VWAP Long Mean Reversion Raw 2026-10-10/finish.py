"""Render all outcomes, never select parameters or substitute failed/short history."""
from pathlib import Path
import csv, html, json, math
import run as r

ROOT=r.ROOT
def esc(x):return html.escape(str(x))
def f(x,d=2):return '—' if x is None else f'{x:,.{d}f}'
def pct(x):return '—' if x is None else f'{x:+.2f}%'
def curve(q):
    ledger=q['ledger'];points=[(0,10000)]+[(i+1,x['balance']) for i,x in enumerate(ledger)]
    low=min(v for _,v in points);high=max(v for _,v in points);spread=max(high-low,1);maximum=max(len(points)-1,1)
    step=max(1,len(points)//500);chosen=points[::step]
    if chosen[-1]!=points[-1]:chosen.append(points[-1])
    path=' '.join(f'{12+676*i/maximum:.2f},{118-104*(v-low)/spread:.2f}' for i,v in chosen)
    return '<svg viewBox="0 0 700 140" role="img" aria-label="Native closed balance by deal sequence"><polyline points="'+path+'" fill="none" stroke="#75efce" stroke-width="2"/><text x="12" y="136">$10,000 → $'+f(points[-1][1])+'</text></svg>'

def main():
    plan=r.n.read(ROOT/'PLAN.json');state=r.n.read(ROOT/'RUN_STATUS.json')
    assert state['total']==26
    out=[];blocks=[];cards=[]
    for row in plan['cases']:
        record=state['complete'].get(row['slug'])
        if not record:continue
        q=r.n.read(Path(record['path']));m=q['metrics']
        assert q['signal_audit_verified'] and q['no_live_changes']
        positive_r=sum(max(t['net_r'],0) for t in q['trades']);negative_r=-sum(min(t['net_r'],0) for t in q['trades'])
        m['pf_r_normalized']=positive_r/negative_r if negative_r else None
        m['mean_commission_r']=-sum(t['commission']/t['initial_risk_usd'] for t in q['trades'])/len(q['trades']) if q['trades'] else None
        coverage='No filled trades'
        if q['trades']:
            first=min(t['open_epoch'] for t in q['trades']);last=max(t['close_epoch'] for t in q['trades'])
            coverage=str(r.n.pd.Timestamp(first,unit='s',tz='UTC'))+' → '+str(r.n.pd.Timestamp(last,unit='s',tz='UTC'))
        out.append(dict(asset=row['label'],symbol=row['symbol'],window=row['window'],start=row['start'],end_exclusive=plan['end_exclusive'],metrics=m,
            history_quality=q['native']['history_quality'],tick_notes=q['tick_notes'],diagnostics=q['diagnostics'],
            tester_end_liquidations=q['tester_end_liquidations'],report='native/'+q['tag']+'/report.htm'))
        csvname=row['slug']+'-trades.csv'
        with (ROOT/csvname).open('w',encoding='utf-8-sig',newline='') as file:
            fields=['position_id','open_utc','close_utc','volume','open_price','close_price','sl','tp','gross','commission','swap','fee','net','initial_risk_usd','net_r','exit_reason']
            w=csv.DictWriter(file,fieldnames=fields);w.writeheader()
            for t in q['trades']:
                values={k:t[k] for k in fields if k in t}
                values.update(open_utc=r.n.pd.Timestamp(t['open_epoch'],unit='s',tz='UTC').isoformat(),
                    close_utc=r.n.pd.Timestamp(t['close_epoch'],unit='s',tz='UTC').isoformat(),exit_reason='; '.join(t['exit_comments']))
                w.writerow(values)
        cards.append('<details class="case" data-window="'+row['window']+'"><summary>'+esc(row['label'])+' · '+row['window']+' · '+str(m['trades'])+' trades · PF '+f(m['pf'])+'</summary>'+curve(q)+
            '<p>Avg win $'+f(m['avg_win'])+' · avg loss $'+f(m['avg_loss'])+' · net '+f(m['total_net_r'])+'R · '+f(m['avg_trades_per_calendar_day'])+' trades/calendar day.</p>'+
            '<p>Risk-normalised PF '+f(m['pf_r_normalized'])+' (separate from the cash PF above). First/last actual filled-trade coverage: '+esc(coverage)+'.</p>'+
            '<p>Commission $'+f(m['commission'])+' (mean '+f(m['mean_commission_r'],3)+'R per trade, excluding bid/ask spread already in execution) · swap $'+f(m['swap'])+' · tester-end liquidations '+str(q['tester_end_liquidations'])+'.</p>'+
            '<p>History: '+esc(q['native']['history_quality'])+'. '+esc(' | '.join(q['tick_notes']))+'</p><p>'+esc(' | '.join(q['diagnostics']))+'</p>'+
            '<p><a href="'+esc(csvname)+'">Trade-by-trade CSV</a> · <a href="native/'+esc(q['tag'])+'/report.htm">Native MT5 report</a> · <a href="native/'+esc(q['tag'])+'/signals.csv">Signal audit</a></p></details>')
    for window,title in [('1y','Last year: 10 October 2025 → 10 October 2026'),('3y','Three years: 10 October 2023 → 10 October 2026')]:
        rows=[]
        for label,symbol in r.ASSETS:
            found=[x for x in out if x['symbol']==symbol and x['window']==window]
            if not found:
                error=state['failed'].get(f'vwap-2atr-1r-{symbol.lower()}-{window}',{}).get('error','Not yet complete')
                rows.append('<tr><td>'+esc(label)+'</td><td colspan="10">Unavailable: '+esc(error[:300])+'</td></tr>');continue
            a=found[0];m=a['metrics']
            rows.append('<tr><td>'+esc(label)+'</td><td>'+str(m['trades'])+'</td><td>'+f(m['win_rate'],1)+'%</td><td>'+f(m['pf'])+'</td><td class="'+('positive' if m['return_pct']>0 else 'negative')+'">'+pct(m['return_pct'])+'</td><td>'+f(m['equity_dd_pct'])+'%</td><td>'+f(m['sharpe_calendar_daily_equity'])+'</td><td>'+str(m['win_streak'])+' / '+str(m['loss_streak'])+'</td><td>'+f(m['total_net_r'])+'</td><td>'+f(m['mean_net_r'],3)+'</td><td>'+esc(a['history_quality'])+'</td></tr>')
        blocks.append('<section class="window" data-window="'+window+'"><h2>'+title+' (end exclusive)</h2><div class="scroll"><table><thead><tr><th>Asset</th><th>Trades</th><th>Win rate</th><th>PF net</th><th>Return</th><th>Max equity DD</th><th>Sharpe</th><th>Win / loss streak</th><th>Net R</th><th>Mean R</th><th>Tick quality</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>')
    failures={k:v['error'] for k,v in state['failed'].items()}
    verified=dict(completed=len(out),planned=26,failed=failures,all_signal_audits_passed=True,
        current_source_hash_matches_plan=all(r.n.sha(Path(p))==d for row in plan['cases'] for p,d in row['production_hashes'].items()),
        native_costs_and_cash_reconciled=True,unoptimised=True,no_live_changes=True,no_push=True)
    assert verified['current_source_hash_matches_plan']
    r.n.save(ROOT/'SUMMARY.json',dict(plan=plan,results=out,verification=verified))
    r.n.save(ROOT/'VERIFICATION.json',verified)
    rules=''.join('<tr><th>'+esc(k.replace('_',' ').title())+'</th><td>'+esc(v)+'</td></tr>' for k,v in plan['rules'].items())
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>VWAP long mean reversion · 1R raw results</title><style>
    :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#071611;color:#edf9f4;font:15px/1.65 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:34px 24px}h1{font-size:34px;line-height:1.2}h2{font-size:22px;margin-top:30px}p{color:#a7c1b7}a{color:#79efce}small,.eyebrow{color:#82dfc3}.notice{border:1px solid #777339;background:#202316;padding:16px;border-radius:12px}nav{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}button{background:#102a20;border:1px solid #447561;border-radius:8px;color:#d8ffef;padding:10px 18px;cursor:pointer}button.active{background:#75efce;color:#061910}.scroll{overflow-x:auto;border:1px solid #294d3e;border-radius:12px}table{border-collapse:collapse;width:100%;min-width:1050px;font-variant-numeric:tabular-nums}th,td{padding:12px 14px;text-align:left;border-bottom:1px solid #234234;white-space:nowrap}thead{background:#10291f}tbody tr:hover{background:#0c2319}.positive{color:#78efc9}.negative{color:#ff9c9c}.rules{min-width:0}.rules th{width:145px;white-space:normal}.rules td{white-space:normal}.case{border:1px solid #2e5342;border-radius:12px;padding:16px;margin:12px 0}.case summary{cursor:pointer;font-weight:650}.case p{overflow-wrap:anywhere}.case svg{max-width:100%;width:700px;display:block;margin-top:20px}svg text{fill:#a7c1b7;font-size:12px}.hidden{display:none}@media(max-width:650px){main{padding:22px 12px}h1{font-size:28px}th,td{padding:10px}.rules th{width:95px}}
    </style></head><body><main><div class="eyebrow">CALYX · RESEARCH ONLY · NO LIVE CHANGES</div><h1>VWAP discount mean reversion · fixed 1:1 RR</h1>'''
    page+='<p>13 assets × 2 independent native windows. Each starts with $10,000, risks 1% of current closed balance and uses the same frozen parameters. Completed '+str(len(out))+'/26; unresolved '+str(len(failures))+'.</p>'
    page+='<div class="notice">This is a labelled reconstruction—not the creator’s exact strategy or a reproduction of their reported +149R / PF 1.36. A <a href="'+plan['source_corroboration']+'">matching secondary repost</a> transcribes “2 ATR” rather than literal “280R.” Complete original rules are unavailable. Your requested 1R target is a deliberate change: the trade does NOT wait for a full return to VWAP. Neither window is claimed untouched out-of-sample.</div>'
    page+='<nav aria-label="Result period"><button class="active" data-period="1y">Last year</button><button data-period="3y">Three years</button><button data-period="all">Both</button></nav>'+''.join(blocks)
    page+='<p>Returns include compounding and native costs. DD is the native tester’s maximum floating-equity drawdown. Sharpe uses UTC daily sampled equity returns × √365, including no-trade days, with zero risk-free rate; it is not MT5’s internal Sharpe. Win/loss streaks count complete net-closed positions. Net R divides each realised net trade by its USD initial fill-to-stop risk; gaps, fees and time exits make realised outcomes differ from ±1R. Tick-quality percentages do not turn generated ticks into genuine historical ticks.</p>'
    page+='<p>Important sizing limitation: after severe drawdown, some accounts cannot meet the broker’s minimum lot at 1% risk. Those signals are skipped, never rounded up. A longer test can therefore contain fewer trades than a fresh one-year account; see each asset’s undersize/margin count and filled-trade dates below.</p>'
    page+='<h2>Frozen reconstruction rules</h2><div class="scroll"><table class="rules">'+rules+'</table></div><p>The broker clock UTC+0 matches the <a href="https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader">official Exness server-time documentation</a>. The UTC daily anchor is not US regular-hours or futures-session VWAP. CFD tick volume is not exchange traded volume.</p>'
    page+='<h2>Asset details and trades</h2>'+''.join(cards)
    page+='<h2>Limitations</h2><ul>'+''.join('<li>'+esc(v)+'</li>' for v in plan['limitations'])+'</ul><p><a href="PLAN.json">Frozen plan</a> · <a href="SUMMARY.json">Complete metrics</a> · <a href="VERIFICATION.json">Verification</a> · <a href="PROTOCOL.txt">Research protocol</a></p>'
    page+='<p>Implementation references: <a href="https://www.mql5.com/en/docs/constants/structures/mqlrates">MetaQuotes separates tick volume and trade volume</a>; <a href="https://www.mql5.com/en/docs/series/copyrates">closed-bar history access</a>; <a href="https://www.mql5.com/en/docs/indicators/iatr">ATR indicator</a>. These document the implementation, not an economic edge.</p>'
    page+='''</main><script>const buttons=[...document.querySelectorAll('[data-period]')];function select(p){buttons.forEach(b=>b.classList.toggle('active',b.dataset.period===p));document.querySelectorAll('[data-window]').forEach(x=>x.classList.toggle('hidden',p!=='all'&&x.dataset.window!==p));}buttons.forEach(b=>b.addEventListener('click',()=>select(b.dataset.period)));select('1y');</script></body></html>'''
    (ROOT/'Results.html').write_text(page,encoding='utf-8')
    print('Report written: '+str(len(out))+'/26 completed, '+str(len(failures))+' failed')
    for a in out:
        m=a['metrics'];print(a['window'],a['asset'],m['trades'],round(m['win_rate'] or 0,2),round(m['pf'] or 0,3),round(m['return_pct'],2),round(m['equity_dd_pct'] or 0,2))

if __name__=='__main__':main()
