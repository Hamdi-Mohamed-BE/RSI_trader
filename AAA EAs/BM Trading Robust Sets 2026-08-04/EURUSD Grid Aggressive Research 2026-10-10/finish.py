"""Show all high-risk outcomes without hiding failed development or stopouts."""
import html
from pathlib import Path
import run as r
n=r.n;ROOT=r.ROOT
def esc(x):return html.escape(str(x))
def f(x,d=2):return 'N/A' if x is None else f'{x:,.{d}f}'

def curve(q,folder):
    trace=n.export_rows(folder/'trace.csv');step=max(1,len(trace)//750);xs=trace[::step]
    if xs[-1]!=trace[-1]:xs.append(trace[-1])
    start=int(trace[0]['epoch']);end=int(trace[-1]['epoch']);low=min(float(x['equity']) for x in trace)
    high=max(max(float(x['balance']) for x in trace),max(float(x['equity']) for x in trace));span=max(high-low,1)
    paths=[]
    for field,col in [('balance','#85edcc'),('equity','#f7b86e')]:
        p=' '.join(f'{65+865*(int(x["epoch"])-start)/max(end-start,1):.2f},{240-210*(float(x[field])-low)/span:.2f}' for x in xs)
        paths.append('<polyline points="'+p+'" stroke="'+col+'" fill="none" stroke-width="1.6"/>')
    return '<svg viewBox="0 0 1000 285" role="img" aria-label="Closed balance and floating equity"><text x="2" y="30">$'+f(high,0)+'</text><text x="2" y="240">$'+f(low,0)+'</text>'+''.join(paths)+'<text x="65" y="275">Green: closed balance · Orange: equity · dates '+esc(' → '.join(q['window']))+'</text></svg>'

def main():
    summary=n.read(ROOT/'SUMMARY.json');assert summary['completed']==36 and not summary['failed']
    results=summary['results'];selected={x['id']:x for x in summary['selection']['selected']};baseline=n.read(r.RAW/'SUMMARY.json')
    selected.update({x['id']:x for x in summary['supplemental_selection']['selected']})
    for window,q in baseline['results'].items():
        trace=n.export_rows(r.RAW/'native'/q['tag']/'trace.csv');m=r.monthly_metrics(trace,q['window'],q['summary']['net_profit'])
        q['summary'].update(m);q['candidate']='Original 1×';q['stage']=window;q['family']='baseline';q['_folder']=r.RAW/'native'/q['tag']
    all_cases=[*baseline['results'].values(),*results]
    columns=['Case / window','Orders','Basket WR','Basket PF','Total return','Mean month','Median month','Compound/mo','10%+ months','Max equity DD','Worst month','Stopout deals']
    def row(q):
        m=q['summary'];b=m['baskets'];return '<tr><th>'+esc(q['candidate'])+' · '+esc(q['stage'])+'</th>'+''.join('<td>'+esc(v)+'</td>' for v in [str(m['orders']),f(b['win_rate'],1)+'%',f(b['pf']),f(m['return_pct'])+'%',
            f(m['average_monthly_pct'])+'%',f(m['median_monthly_pct'])+'%',f(m['compounded_equivalent_monthly_pct'])+'%',str(m['months_10pct'])+'/'+str(m['full_months']),f(m['equity_dd_pct'])+'%',f(m['worst_month_pct'])+'%',str(m.get('stopout_deals',0))])+'</tr>'
    def table(cases):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in columns)+'</tr></thead><tbody>'+''.join(row(q) for q in cases)+'</tbody></table></div>'
    validation=[q for q in results if q['stage'].startswith('validation')]
    dev=[q for q in results if q['stage']=='dev'];stress=[q for q in all_cases if q['family']!='guarded']
    cards=[]
    for q in sorted(all_cases,key=lambda x:(x['stage'],x['candidate'])):
        m=q['summary'];folder=q.get('_folder',ROOT/'native'/q['tag'])
        relative=str(folder.relative_to(ROOT)) if folder.is_relative_to(ROOT) else '../EURUSD EMA Volume Grid Raw 2026-10-10/native/'+q['tag']
        development_note=''
        if q['stage']=='dev':development_note='Development gate: '+('PASS' if r.passes(m) else 'FAIL')
        elif q['candidate'] in selected:development_note='Selected using older development only. Gate: '+('PASS' if selected[q['candidate']]['passes_development_gate'] else 'FAIL — exploratory validation only')
        months=''.join('<tr><td>'+x['month']+(' · partial' if not x['full_month'] else '')+'</td><td>'+f(x['equity_start'])+'</td><td>'+f(x['equity_end'])+'</td><td>'+f(x['return_pct'])+'%</td><td>'+('yes' if x['full_month'] else 'no')+'</td></tr>' for x in m['monthly'])
        extra=''
        if q['family']=='guarded':
            extra='<p>Basket loss exits '+str(m['basket_loss_exits'])+' · 72-hour exits '+str(m['max_age_exits'])+' · largest cash-stop overshoot $'+f(m['max_budget_overshoot_usd'])+'.</p>'
        cards.append('<details class="case" data-family="'+q['family']+'"><summary>'+esc(q['candidate'])+' · '+esc(q['stage'])+' · return '+f(m['return_pct'])+'% · mean monthly '+f(m['average_monthly_pct'])+'%</summary><p>'+esc(development_note)+'</p>'+curve(q,folder)+
            '<p>Dates '+esc(' → '.join(q['window']))+' (end exclusive). History: '+esc(q['native']['history_quality'])+'. '+esc(' | '.join(q['tick_notes']))+'</p>'+
            '<p>Final balance $'+f(m['final_balance'])+' · equity Sharpe '+f(m['sharpe_calendar_daily_equity'])+' · basket win/loss streak '+str(m['baskets']['win_streak'])+'/'+str(m['baskets']['loss_streak'])+'. Individual-order WR '+f(m['positions']['win_rate'],1)+'%, PF '+f(m['positions']['pf'])+'.</p>'+
            '<p>Peak concurrent positions '+str(m['max_positions'])+' · peak total lots '+f(m['max_lots'])+' · worst daily floating DD $'+f(m['max_daily_equity_dd_usd'])+' · terminal liquidation cash $'+f(m.get('test_end_net',0))+'.</p>'+extra+
            '<p><a href="'+relative+'/report.htm">Native report</a> · <a href="'+relative+'/inputs.set">Exact SET inputs</a> · <a href="'+relative+'/signals.csv">Signal audit</a> · <a href="'+relative+'/deals.csv">Every deal</a> · <a href="'+relative+'/results.json">Full baskets and metrics</a></p>'+
            '<div class="scroll"><table><thead><tr><th>Month UTC</th><th>Starting equity</th><th>Ending equity</th><th>Equity return</th><th>Included in monthly average?</th></tr></thead><tbody>'+months+'</tbody></table></div></details>')
    verdicts={}
    for q in results:
        m=q['summary'];verdicts[q['candidate']+'-'+q['stage']]=dict(arithmetic_mean_target_met=(m['average_monthly_pct'] or -999)>=10,
            compound_target_met=m['compounded_equivalent_monthly_pct'] is not None and m['compounded_equivalent_monthly_pct']>=10,median_target_met=(m['median_monthly_pct'] or -999)>=10,
            stopout=m['stopout_deals']>0,return_pct=m['return_pct'],max_equity_dd_pct=m['equity_dd_pct'])
    n.save(ROOT/'TARGET_CHECK.json',dict(target_monthly_pct=10,cases=verdicts,
        validation_candidates_meeting_mean_target=[q['candidate']+'-'+q['stage'] for q in validation if (q['summary']['average_monthly_pct'] or -999)>=10],
        monthly_returns_use_floating_equity=True,selected_on_development_only=True))
    passed=sum(r.passes(q['summary']) for q in dev)
    page=('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EURUSD aggressive grid · 10% monthly target experiment</title><style>
    :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#071710;color:#ecfaf2;font:15px/1.65 system-ui}main{max-width:1650px;margin:auto;padding:30px 22px}h1{font-size:34px;line-height:1.2}h2{font-size:23px;margin-top:36px}p{color:#b3cabd}a{color:#80f0ca}.eyebrow{color:#80e8c1;letter-spacing:2px;font-size:13px}.notice{border:1px solid #987748;border-radius:12px;background:#262216;padding:18px}.scroll{overflow-x:auto;margin:20px 0}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:11px;border-bottom:1px solid #30533f;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}thead{background:#123423}details{border:1px solid #31533e;padding:16px;border-radius:12px;margin:14px 0}summary{cursor:pointer;font-weight:650}svg{width:100%;max-height:330px}svg text{fill:#b3cabd;font-size:13px}.rules{max-width:1100px}nav{display:flex;gap:8px;flex-wrap:wrap}button{background:#123423;color:#eafff3;border:1px solid #557c68;border-radius:8px;padding:10px 16px;cursor:pointer}button.active{background:#82eac2;color:#092316}.hidden{display:none}@media(max-width:600px){main{padding:20px 12px}h1{font-size:27px}details p{overflow-wrap:anywhere}}
    </style></head><body><main><div class="eyebrow">CALYX · HIGH-RISK EXPERIMENT · NO LIVE CHANGES</div><h1>Can this EURUSD grid average 10% a month?</h1>
    <p>$10,000 independent accounts, leverage 1:2000, EURUSD M5, native broker costs and 150ms delay. 20 bounded-grid development candidates, 10 frozen recent-validation tests, 6 unchanged-grid lot stress tests. Two earlier original-grid controls shown separately. The 8 higher-exposure supplemental candidates were declared after the initial development failures, before their own outcomes; their selection still excludes recent history.</p>
    <div class="notice">Increasing risk does not establish an edge. Cash basket stops are client-side close attempts—not guaranteed loss ceilings. Uncapped stress versions can lose the account. All losses, stopouts and unfinished baskets remain in the results; no top-ups, deposit resets or discarded blown accounts.</div>
    <h2>Recent validation · settings selected before these tests</h2>'''+table(sorted(validation,key=lambda q:(q['stage'],q['candidate'])))+
    '<p>Development gate passed by '+str(passed)+'/20 candidates. A selected candidate that failed the gate is explicitly exploratory, not a validated winner. Last two years: 2024-10-10 → 2026-10-10; independent last year: 2025-10-10 → 2026-10-10. Both end exclusive.</p>'+
    '<h2>Original grid · risk-scaling stress comparison</h2>'+table(sorted(stress,key=lambda q:(q['stage'],q['candidate'])))+
    '<p>1× original settings: starting/increment 0.01 lot and $10 target. 5×: 0.05/+0.05/$50; 10×: 0.10/+0.10/$100; 20×: 0.20/+0.20/$200. All retain 30-pip spacing, forced alternating sides, no stop or cap, and fixed lot sizes. Actual native reruns—not linear extrapolations.</p>'+
    '<h2>All development candidates · none hidden</h2>'+table(sorted(dev,key=lambda q:q['candidate']))+
    '<div class="rules"><h2>What was changed and how selection worked</h2><p>Guarded IDs encode nominal basket loss budget r5/r10 = 5%/10% of starting closed balance; g100/g300 = 10/30-pip spacing; tp0.25/tp0.5/tp1 = 0.25R/0.5R/1R basket targets. Fixed equal lots within each basket, initially 0.10 at r5 or 0.20 at r10 per $10k, proportionally scaled at the next basket start. Maximum 5 orders, no forced alternating sides, 72-hour maximum age. Entry remains EMA5 plus three strictly increasing closed M5 tick volumes.</p>'+
    '<p>Supplemental fast IDs also state initial equal lots per $10k: 0.5/1.0 at 5% budget and 1.0/2.0 at 10% budget. They retain 10-pip spacing, 5-order cap, 72-hour exit and the same signals. This higher exposure allows shorter price moves to reach a given cash target, but also reaches cash stops sooner.</p>'+
    '<p>Development uses 2020-10-10 → 2024-10-10. Gate: ≥30 baskets, positive return, basket PF ≥1.05, no stopout, equity DD ≤70%. Rank by compounded equivalent monthly growth, then PF, then lower DD. The initial group selects three candidates and the supplemental group two; if too few pass, remaining slots use the highest-ranked gate failures, clearly labelled exploratory. Each selection file is frozen before its validation. No validation-result retuning.</p>'+
    '<p>Mean month is the arithmetic mean of complete calendar-month floating-equity returns; median shows the typical month. Compound/mo is the full-window equivalent monthly growth from final account value, not an arithmetic average; it is undefined (N/A) when the account ends at or below zero. Boundary partial October months are listed but excluded from monthly mean, median and 10% frequency. No-trade months are retained. Full-window total return and drawdown include those partial months, so a positive complete-month mean can coexist with a negative total return. A 10% month here or there does not demonstrate a 10% average. Different independent starting dates can change grid paths.</p>'+
    '<p>Recent prices were already examined in earlier raw work; this is selection-excluded validation, NOT genuinely untouched OOS. Older tick history contains generated ticks; native real-tick percentages are disclosed per case. DD is the larger of native MT5 and before/after trade tick-observer measurements. Equity graphs sample one minute and may miss transient minima. Historical outcomes are not future-return promises.</p></div>'+
    '<h2>Graphs, every month and native evidence</h2><nav aria-label="Case family"><button class="active" data-filter="all">All cases</button><button data-filter="guarded">Capped research</button><button data-filter="scaled">Uncapped stress</button><button data-filter="baseline">Original controls</button></nav>'+''.join(cards)+
    '<p><a href="PLAN.json">Original frozen plan</a> · <a href="SELECTION.json">Initial development selection</a> · <a href="SUPPLEMENTAL_PLAN.json">Higher-exposure plan</a> · <a href="SUPPLEMENTAL_SELECTION.json">Higher-exposure selection</a> · <a href="TARGET_CHECK.json">10% target checks</a> · <a href="SUMMARY.json">All results</a> · <a href="VERIFICATION.json">Verification</a> · <a href="PROTOCOL.txt">Protocol</a> · <a href="EURUSD Grid Aggressive Research.mq5">Tester-only research source</a></p>'+
    '<p>Risk reference: leverage amplifies both gains and losses; see the <a href="https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html">CFTC forex advisory</a>. No live bots, BATs, website, account trades or Git push.</p>'+
    '''</main><script>document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('[data-family]').forEach(x=>x.classList.toggle('hidden',b.dataset.filter!=='all'&&x.dataset.family!==b.dataset.filter));}));</script></body></html>''')
    (ROOT/'Results.html').write_text(page,encoding='utf-8');print('Complete high-risk report written')

if __name__=='__main__':main()
