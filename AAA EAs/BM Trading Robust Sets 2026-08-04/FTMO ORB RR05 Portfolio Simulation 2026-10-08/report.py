"""Standalone report only; does not edit the public website."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import html, json

ROOT=Path(__file__).resolve().parent
def esc(v):return html.escape(str(v))
def f(v,n=2):return '—' if v is None else f'{v:,.{n}f}'
def localdate(v):return datetime.fromisoformat(v).astimezone(ZoneInfo('Europe/Prague')).date().isoformat() if v else '—'
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
    d=json.loads((ROOT/'Results.json').read_text());labels={x['name']:x['label'] for x in d['historical']}
    sections=[]
    quals=[]
    for q in d['audit']['qualified']:
        a,b=q['current'],q['candidate']
        state='Included: replacement' if q['qualifies'] and q['order_compatible'] and q['already_ftmo'] else 'Included: addition' if q['qualifies'] and q['order_compatible'] else 'Blocked by current FTMO guard' if q['qualifies'] else 'Not qualified / provisional'
        quals.append([esc(q['label']),str(a['trades'])+' → '+str(b['trades']),f(a['win_rate'])+' → '+f(b['win_rate']),f(a['pf'])+' → '+f(b['pf']),str(a['win_streak'])+' → '+str(b['win_streak']),esc(state),esc(q['note'])])
    sections.append('<h2>Selection and compatibility</h2><p>Candidate gate: PF ≥1.15, higher net win rate and longer winning streak in the aligned standalone test. Four existing FTMO EAs are replaced, not duplicated. XAU Weakness cannot enter under the unchanged market-only FTMO guard. The five-trade Selective ORB is provisional, not part of the qualifying group.</p>'+table(['EA','Trades current → 0.5R','Win %','PF','Max winning streak','Decision','Note'],quals))
    mixes=[]
    for x in d['historical']:
        mixes.append([esc(x['label']),x['ea_count'],esc(', '.join(x['replacements']) or 'None'),esc(', '.join(x['additions']) or 'None')])
    sections.append('<h2>Exactly what each mix changes</h2>'+table(['Mix','Total EAs','Existing EAs changed to 0.5R','New 0.5R additions'],mixes))
    history=[];curves=[];fullchallenge=[]
    for x in d['historical']:
        m=x['portfolio'];history.append([esc(x['label']),x['ea_count'],m['trades'],f(m['return_pct'])+'%',f(m['win_rate'])+'%',f(m['pf']),f(m['closed_balance_dd_pct'])+'%',f(m['daily_closed_sharpe']),str(m['win_streak'])+'/'+str(m['loss_streak'])])
        curves.append(dict(label=x['label'],values=m['balance_curve']))
        c=x['challenge'];p={z['phase']:z for z in c['passes']}
        fullchallenge.append([esc(x['label']),localdate(p.get(1,{}).get('time')),localdate(p.get(2,{}).get('time')),localdate(c['funded_at']),localdate(c['receipt_at']),f(c['reward'] if c['payout'] else 0),c['trades'],f(c['balance'])])
    sections.append('<h2>Historical shared-account ledger</h2><p>6 October 2025–5 October 2026 inclusive. $10,000 initial capital; fixed $50 planned risk per full-risk position, except the labelled $25 additions. All use the same shared risk and margin gates. Return is on account capital, not on the challenge fee. Drawdown and Sharpe below are <strong>closed-balance</strong> metrics, not true floating-equity metrics.</p>'+table(['Portfolio','EAs','Trades','Account return','Win rate','PF','Closed DD','Daily closed Sharpe','Streak W/L'],history)+'<svg id="chart" viewBox="0 0 1100 460" aria-label="Historical shared closed balance"></svg><div id="legend"></div>')
    sections.append('<h2>Actual historical dates: challenge started 6 October 2025</h2><p>This chronological replay starts with a fresh account and no warm-start positions. Milestone dates are CE(S)T (Prague). These are simulated milestones on real historical dates, not claims that a real FTMO account passed or received payment.</p>'+table(['Portfolio','Phase 1 pass','Both phases passed','Funded activation*','First payment*','Reward USD','Lifecycle trades','Ending phase balance'],fullchallenge))
    real=[]
    for name in labels:
        for horizon in (90,180):
            xs=[x for x in d['historical_starts'] if x['portfolio']==name and x['horizon_days']==horizon]
            both=[x for x in xs if x['both_passed']]
            durations=[(datetime.fromisoformat(x['passes'][1]['time'])-datetime.fromisoformat(x['start']).replace(tzinfo=ZoneInfo('UTC'))).total_seconds()/86400 for x in both]
            real.append([esc(labels[name]),horizon,len(xs),f(len(both)*100/len(xs),1)+'%',f(sum(x['reward_received'] for x in xs)*100/len(xs),1)+'%',f(sum(durations)/len(durations),1) if durations else '—'])
    sections.append('<h2>Real chronological start-date sensitivity</h2><p>40 complete 90-day windows and 27 complete 180-day windows per portfolio, one fresh start each Monday. No future dates are invented here. Overlapping windows are highly dependent; these are retrospective frequencies, not independent pass probabilities.</p>'+table(['Portfolio','Horizon','Historical starts','Both-pass frequency','First-payment frequency','Mean pass days†'],real))
    protocols=defaultdict(list)
    for x in d['random_cases']:protocols[x['protocol']].append(x)
    for name,cases in protocols.items():
        rows=[]
        for x in cases:
            for s in x['summary']:
                a=s['days_to_pass_both'];b=s['days_to_first_reward'];delta=x.get('paired_vs_baseline_365d',{})
                rows.append([esc(labels[x['portfolio']]),s['days'],f(s['both_pass_pct'],1)+'%',f(s['funded_pct'],1)+'%',f(s['evaluation_proxy_breach_pct'],1)+'%',f(s['unfinished_evaluation_pct'],1)+'%',f(a['mean'],1)+' / '+f(a['median'],1),f(s['first_reward_received_pct'],1)+'%',f(b['mean'],1)+' / '+f(b['median'],1),'$'+f(s['expected_first_reward_usd']),('$'+f(delta.get('expected_reward_change'))) if s['days']==365 else '—'])
        sections.append('<h2>'+esc(name)+'</h2><p>'+str(d['paths_per_case'])+' matched random paths per portfolio. The same market blocks are drawn for every comparison, preserving cross-EA timing within blocks. The full-history pool contains 52 complete weeks, 6 October 2025–4 October 2026. The recent pool contains its final 13 weeks, 6 July–4 October 2026. Synthetic calendar begins 12 October 2026; it is illustrative, not a forecast.</p>'+table(['Portfolio','Horizon days','Both-pass rate','Funded rate','Evaluation proxy breach','Still evaluating','Pass days mean / median†','First-payment rate','Payment days mean / median†','Expected first reward‡','Δ reward vs current /365d'],rows))
    fee=[]
    for x in protocols.get('Joint 4-week blocks',[]):
        s=x['summary'][-1]
        for a in s['expected_net_cash_and_fee_roi']:
            fee.append([esc(labels[x['portfolio']]),'$'+f(a['fee_usd']), 'Illustrative, not your confirmed fee' if a['assumed'] else 'User-supplied fee',f(s['first_reward_received_pct'],1)+'%','$'+f(s['expected_first_reward_usd']),'$'+f(a['expected_net_cash']),f(a['expected_fee_roi_pct'])+'%'])
    sections.append('<h2>Fee-based ROI, first reward only</h2><p>Your actual USD fee is not yet supplied. The figures below use explicitly hypothetical $150/$200 fees. Expected net cash = expected first reward + probability of receipt × fee refund − purchase fee. ROI divides that expected net cash by the fee. Failed/unfinished paths contribute zero reward and no refund by the deadline. Challenge profits are not withdrawable rewards; account return and fee ROI are different quantities.</p>'+table(['Portfolio','Fee','Fee status','Payment rate /365d','Expected reward','Expected net cash','Expected fee ROI'],fee))
    sections.append('<h2>Monthly historical returns and trades</h2>')
    months=sorted({m for x in d['historical'] for m in x['portfolio']['months']})
    rows=[]
    for m in months:
        rows.append([m]+[f(x['portfolio']['months'].get(m,{}).get('net',0)/100)+'% / '+str(x['portfolio']['months'].get(m,{}).get('trades',0)) for x in d['historical']])
    sections.append(table(['Month']+[x['label']+' return / trades' for x in d['historical']],rows))
    sections.append('<h2>Every historical Monday start</h2><p>Only complete 90-/180-day forward windows are included; there is no circular history extension. Starts overlap heavily, so these are not independent trials. Filters below reveal all real dates, milestones and censored outcomes.</p><select id="portfolio"><option value="">All portfolios</option>'+''.join('<option value="'+k+'">'+esc(v)+'</option>' for k,v in labels.items())+'</select><select id="horizon"><option value="">Both horizons</option><option value="90">90 days</option><option value="180">180 days</option></select>')
    rows=[]
    for x in d['historical_starts']:
        p={z['phase']:z for z in x['passes']}
        rows.append('<tr data-p="'+x['portfolio']+'" data-h="'+str(x['horizon_days'])+'">'+''.join('<td>'+str(v)+'</td>' for v in [esc(labels[x['portfolio']]),x['horizon_days'],x['start'],x['end_exclusive'],localdate(p.get(1,{}).get('time')),localdate(p.get(2,{}).get('time')),localdate(x['funded_at']),localdate(x['reward_at']),f(x['first_reward']),'Proxy breach' if x['breach'] else 'Both passed' if x['both_passed'] else 'Unfinished',x['trades']])+'</tr>')
    sections.append('<div class="scroll"><table id="starts"><thead><tr>'+''.join('<th>'+h+'</th>' for h in ['Portfolio','Horizon','Start','End exclusive','Phase 1','Both passed','Funded*','First paid*','Reward USD','Outcome','Trades'])+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')
    sections.append('<h2>Rules, assumptions and limitations</h2><p>'+esc(d['methodology'])+'</p><ul>'+''.join('<li>'+esc(x)+'</li>' for x in d['limitations'])+'</ul><p>† Days are conditional on completing the milestone inside that horizon, not an unconditional waiting-time estimate. ‡ Expected first reward averages every purchase, including zeros. *Administrative dates assume 2/5 business-day phase waits and 4 business-day processing; these are not guaranteed FTMO turnaround times.</p><p>Zero proxy breaches, if present, do not establish zero real breach probability. Stops do not cap gaps, floating equity is not measured, and near-simultaneous chart requests may differ from the cached-entry overlay. No live deployment is approved by these research results.</p><p><a href="https://ftmo.com/en/2-step-challenge/">FTMO 2-Step objectives</a> · <a href="https://academy.ftmo.com/lesson/maximum-daily-loss/">Daily equity loss rule</a> · <a href="https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/">First reward and split</a> · <a href="https://ftmo.com/en/how-it-works/">Fee refund</a></p><p><a href="Results.json">Full frozen results</a> · <a href="DATA_AUDIT.json">Source data and qualification audit</a> · <a href="../ORB%20and%20Range%20Breakout%20RR05%20Comparison%202026-10-08/Results.html">All 15 original target comparisons</a></p>')
    script='''<script>const curves=CURVES;const colors=['#6febbb','#f8c96f','#75b8ff','#e19ade','#baff83','#ff9284'];const svg=document.getElementById('chart'),legend=document.getElementById('legend');const vals=curves.flatMap(c=>c.values.map(v=>v[1]));const lo=Math.min(...vals)-80,hi=Math.max(...vals)+80;svg.innerHTML=[0,.25,.5,.75,1].map(q=>`<line x1="95" x2="1080" y1="${420-q*370}" y2="${420-q*370}" stroke="#294238"/><text x="10" y="${425-q*370}" fill="#afc8bb">$${Math.round(lo+q*(hi-lo))}</text>`).join('');curves.forEach((c,i)=>{svg.innerHTML+=`<polyline id="line${i}" points="${c.values.map(v=>`${95+v[0]/365*985},${420-(v[1]-lo)/(hi-lo)*370}`).join(' ')}" fill="none" stroke="${colors[i]}" stroke-width="2.2"/>`;const b=document.createElement('button');b.textContent=c.label;b.style.color=colors[i];b.onclick=()=>{const l=document.getElementById('line'+i);l.style.display=l.style.display==='none'?'':'none'};legend.appendChild(b)});['portfolio','horizon'].forEach(k=>document.getElementById(k).onchange=()=>{const p=document.getElementById('portfolio').value,h=document.getElementById('horizon').value;document.querySelectorAll('#starts tbody tr').forEach(r=>r.hidden=(p&&r.dataset.p!==p)||(h&&r.dataset.h!==h))});</script>'''.replace('CURVES',json.dumps(curves))
    finding='<p><strong>Result: mixed, not universally better.</strong> The full compatible mix raises historical win rate (50.2% → 55.2%) and reduces closed drawdown (4.85% → 4.37%). It improves the recent-only scenario but is slower and pays less in full-year reference resampling, and does worse under cost stress. Keeping existing targets and adding only Gold NY M30 plus Elliott Wave is the better full-year compromise; the classical ORB-only mix is strongest in recent-regime resampling. None is established as superior in untouched out-of-sample data.</p>'
    doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FTMO qualifying ORBs: portfolio comparison</title><style>body{font:15px system-ui;background:#071713;color:#edf8f2;max-width:1600px;margin:30px auto;padding:20px}h1{font-size:34px}h2{font-size:24px;margin-top:48px}p,li{line-height:1.65;color:#b6d0c1}a{color:#7df7c8}.warning{border:1px solid #a78836;border-radius:10px;padding:18px;color:#ffe7a3}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:11px;border-bottom:1px solid #2a4439;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#72edba;background:#10261c}svg{width:100%;background:#10241b;border-radius:12px}button,select{background:#17392b;border:1px solid #42715b;color:#d7f2df;padding:10px;margin:5px;border-radius:6px}td:last-child{white-space:normal}strong{color:#e5ffe8}</style></head><body><h1>FTMO + qualifying 0.5R ORBs</h1><p>Shared-$10,000 research simulation · 8 October 2026 · unchanged FTMO profile risk, news off</p>'+finding+'<p class="warning">Fitted-history, standalone-ledger overlay—not a validated FTMO equity backtest or a forecast of future pass probability. Individual entry/exit histories were refreshed to the actual FTMO strategy inputs. Shared guards and first-reward lifecycle are modelled offline. No EAs, BATs, website, GitHub or live account settings were changed.</p>'+''.join(sections)+script+'</body></html>'
    (ROOT/'Results.html').write_text(doc,encoding='utf-8')
    print('Report created: '+str(ROOT/'Results.html'))

if __name__=='__main__':main()
