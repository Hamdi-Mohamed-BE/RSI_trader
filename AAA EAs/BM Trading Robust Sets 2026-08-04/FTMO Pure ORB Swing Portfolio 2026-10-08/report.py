"""Render a separate research report; never changes the public website."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import html, json

ROOT=Path(__file__).resolve().parent
def esc(v):return html.escape(str(v))
def num(v,n=2):return '—' if v is None else f'{v:,.{n}f}'
def local(v):return datetime.fromisoformat(v).astimezone(ZoneInfo('Europe/Prague')).date().isoformat() if v else '—'
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def main():
    d=json.loads((ROOT/'Results.json').read_text());labels={x['name']:x['label'] for x in d['historical']}
    individual=[]
    for x in d['individual']:
        m=x['ftmo_proxy'];a=x['native']
        individual.append([esc(x['label']),num(x['rr'],1)+'R',str(a['trades'])+' → '+str(m['trades']),num(m['win_rate'])+'%',num(m['pf']),num(m['return_pct'])+'%',num(m['closed_balance_dd_pct'])+'%',str(m['win_streak'])+'/'+str(m['loss_streak']),esc(x['small_sample_warning'] or 'Passed numerical gate')])
    history=[];dates=[];curves=[]
    for x in d['historical']:
        m=x['portfolio'];c=x['challenge'];p={z['phase']:z for z in c['passes']}
        history.append([esc(x['label']),x['ea_count'],m['trades'],num(m['return_pct'])+'%',num(m['win_rate'])+'%',num(m['pf']),num(m['closed_balance_dd_pct'])+'%',num(m['daily_closed_sharpe']),str(m['win_streak'])+'/'+str(m['loss_streak']),num(m['trades']/261)])
        dates.append([esc(x['label']),local(p.get(1,{}).get('time')),local(p.get(2,{}).get('time')),local(c['funded_at']),local(c['receipt_at']),c['phase'],'$'+num(c['balance'])])
        curves.append(dict(name=x['name'],label=x['label'],values=m['balance_curve']))
    sections=[]
    sections.append('<h2>The four qualifying ORBs</h2><p>Numerical gate: win rate ≥60% and finite net PF ≥1.15. Prefer the previously tested 0.5R variant when it passes. Selective US100 qualifies only at its existing 2R target; its 0.5R result has no losses in five trades and therefore no finite PF. Both raw native tests and $50 FTMO-cost individual overlays were checked. The Gold NY min-lot budget removes one trade, changing 12 native trades to 11 modelled trades.</p>'+table(['EA','Target','Native → admitted trades','FTMO proxy win rate','PF','Return','Closed DD','Streak W/L','Evidence warning'],individual))
    sections.append('<h2>Combined shared-account history</h2><p>6 October 2025–5 October 2026 inclusive, $10,000 capital and fixed $50 planned risk per entry. Stops, clocks, signal filters and management are retained; no further optimisation. The 14-EA mix is a benchmark only and is not included in the pure ORB profile. Drawdown and Sharpe are closed-balance measures, not true floating-equity measures. Trades/day includes all 261 weekdays, including zero-trade days.</p>'+table(['Portfolio','EAs','Trades','Account return','Win rate','PF','Closed DD','Daily closed Sharpe','Max wins/losses','Trades/weekday'],history)+'<svg id="curve" viewBox="0 0 1100 440" role="img" aria-label="Historical shared closing balance"></svg><div id="legend"></div>')
    sections.append('<h2>Actual chronological challenge: start 6 October 2025</h2><p>Prague calendar dates. The core trio did not reach Phase 1 within this source year. The four-EA profile passed Phase 1 on 2 September 2026, but had not passed Verification by the data end. Continuous return above is not a withdrawable challenge payout. Phase accounts reset to $10,000 on handover.</p>'+table(['Portfolio','Phase 1 passed','Both phases passed','Funded','First paid','End phase','End phase balance'],dates))
    protocols={}
    for x in d['random_cases']:protocols.setdefault(x['protocol'],[]).append(x)
    for name,cases in protocols.items():
        rows=[]
        for x in cases:
            for z in x['summary']:
                t=z['days_to_pass_both'];p=z['days_to_phase1']
                rows.append([esc(labels[x['portfolio']]),z['days'],num(z['phase1_pass_pct'],1)+'%',num(z['both_pass_pct'],1)+'%',num(z['unfinished_evaluation_pct'],1)+'%',num(p['mean'],1),num(t['mean'],1)+' / '+num(t['median'],1),num(z['first_reward_received_pct'],1)+'%','$'+num(z['expected_first_reward_usd'])])
        sections.append('<h2>'+esc(name)+'</h2><p>1,000 matched paths per portfolio. Each portfolio receives the same joint market blocks, preserving within-block cross-EA timing. Source pool: 52 complete weeks, 6 October 2025–4 October 2026; recent-only pool: 6 July–4 October 2026. Synthetic calendars start 12 October 2026. A 730-day path resamples the same year; it is not an additional two-year historical validation.</p>'+table(['Portfolio','Deadline days','Phase 1 pass','Both-phase pass','Still evaluating','Phase 1 mean days†','Both-pass mean / median days†','First-payment rate','Expected first reward‡'],rows))
    fee=[]
    for x in protocols['Joint 4-week blocks']:
        for z in x['summary']:
            if z['days'] not in (365,730):continue
            a=z['expected_net_cash_and_fee_roi'][0]
            fee.append([esc(labels[x['portfolio']]),z['days'],'$'+num(a['fee_usd']),'$'+num(a['expected_net_cash']),num(a['expected_fee_roi_pct'])+'%'])
    sections.append('<h2>Fee ROI — explicitly hypothetical $150 fee</h2><p>Actual fee not supplied. Expected net cash = expected first reward + first-payment probability × fee refund − fee. These are deadline-limited first-reward cash flows, not annual income or a mark-to-market value of an unfinished challenge. A negative figure does not mean the ongoing challenge account has been breached.</p>'+table(['Portfolio','Deadline days','Illustrative fee','Expected net cash','Fee ROI'],fee))
    months=sorted({m for x in d['historical'] for m in x['portfolio']['months']})
    monthly=[]
    for m in months:
        monthly.append([m]+[num(x['portfolio']['months'].get(m,{}).get('net',0)/100)+'% / '+str(x['portfolio']['months'].get(m,{}).get('trades',0)) for x in d['historical']])
    sections.append('<h2>Monthly history: return / trades</h2>'+table(['Month']+list(labels.values()),monthly))
    audit=[]
    for x in d['selection_audit']:
        audit.append([esc(x['label']),'0.5R test' if x['variant']=='half' else 'Existing target',x['native_trades'],num(x['native_win_rate'])+'%',num(x['native_pf']), 'Passed' if x['qualifies'] else esc(x['reason'])])
    sections.append('<h2>Complete ORB selection audit</h2><p>Includes Asia range breakout in the audit, although it fails the gate. EMA3, Elliott Wave, 3-Way Gold, RSI VWAP, DMC, overnight value-area and timed hourly systems are excluded because this profile is strictly opening-range-only. No archived research variations are added.</p>'+table(['ORB/range setup','Variant','Trades','Native win rate','Native PF','Numerical gate'],audit))
    rows=[]
    for x in d['starts']:
        p={z['phase']:z for z in x['passes']}
        rows.append([esc(labels[x['portfolio']]),x['horizon_days'],x['start'],x['end_exclusive'],local(p.get(1,{}).get('time')),local(p.get(2,{}).get('time')),local(x['reward_at']),'Proxy breach' if x['breach'] else 'Both passed' if x['both_passed'] else 'Phase 1 passed' if x['phase1_passed'] else 'Unfinished'])
    sections.append('<details><summary>All 201 historical Monday start windows</summary><p>40 full 90-day and 27 full 180-day windows per portfolio, no wraparound. Overlapping windows are dependent retrospective tests.</p>'+table(['Portfolio','Horizon','Start','End exclusive','Phase 1','Both passed','First paid','Outcome'],rows)+'</details>')
    sections.append('<h2>Same Swing rules and model limitations</h2><p>'+esc(d['methodology'])+'</p><ul>'+''.join('<li>'+esc(x)+'</li>' for x in d['limitations']+d['new_limitations'])+'</ul><p>† Days are conditional on finishing the milestone inside that deadline. There is no finite mean pass time established for unfinished paths. ‡ First reward averages every purchase, including failed/unfinished zeros. Zero stop-reserve proxy breaches do not establish zero real floating-equity breach risk. Administrative timing is assumed, not guaranteed.</p><p>This is a saved research profile, not a compiled guarded installer or a live account application. Copying a normal source SET/EX5 onto a live FTMO account does not automatically add the shared guard.</p><p><a href="PORTFOLIO.json">Saved four-EA research profile</a> · <a href="Results.json">Full data</a> · <a href="SELECTION_AUDIT.json">Eligibility audit</a> · <a href="https://ftmo.com/en/2-step-challenge/">FTMO 2-Step rules</a> · <a href="https://ftmo.com/en/faq/ftmo-swing-account-type/">Swing account type</a> · <a href="https://academy.ftmo.com/lesson/maximum-daily-loss/">Daily equity rule</a></p>')
    js='''<script>const curves=CURVES,colors=['#75e8b8','#f4cb77','#7fbbff'];let visible=[true,true,false];const svg=document.getElementById('curve');function draw(){const all=curves.filter((_,i)=>visible[i]).flatMap(x=>x.values.map(v=>v[1]));if(!all.length){svg.innerHTML='';return}const lo=Math.min(...all)-50,hi=Math.max(...all)+50;svg.innerHTML=[0,.25,.5,.75,1].map(q=>`<line x1="95" x2="1080" y1="${405-q*355}" y2="${405-q*355}" stroke="#294739"/><text x="10" y="${410-q*355}" fill="#b6cfbf">$${Math.round(lo+q*(hi-lo))}</text>`).join('');curves.forEach((x,i)=>{if(visible[i])svg.innerHTML+=`<polyline points="${x.values.map(v=>`${95+v[0]/365*985},${405-(v[1]-lo)/(hi-lo)*355}`).join(' ')}" fill="none" stroke="${colors[i]}" stroke-width="2.5"/>`})}curves.forEach((x,i)=>{const b=document.createElement('button');b.textContent=x.label;b.style.color=colors[i];b.onclick=()=>{visible[i]=!visible[i];b.style.opacity=visible[i]?1:.5;draw()};b.style.opacity=visible[i]?1:.5;document.getElementById('legend').appendChild(b)});draw();</script>'''.replace('CURVES',json.dumps(curves))
    doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FTMO Swing — pure ORB portfolio</title><style>body{font:16px system-ui;background:#071713;color:#edf8f2;max-width:1500px;margin:30px auto;padding:20px}h1{font-size:34px}h2{font-size:23px;margin-top:45px}p,li{color:#b3cfbd;line-height:1.65}.note{padding:18px;border:1px solid #a7883f;border-radius:10px;color:#ffe1a0}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border-bottom:1px solid #2a4336;padding:11px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#73ebbc;background:#10281c}td:last-child{white-space:normal}svg{width:100%;background:#10271c;border-radius:12px}button{padding:10px;margin:5px;background:#153c2a;border:1px solid #3d7657;border-radius:6px}a{color:#75f0bd}summary{cursor:pointer;padding:15px;background:#143124}</style></head><body><h1>FTMO Swing: pure ORB portfolio</h1><p>Research profile · 8 October 2026 · same $10,000 account / $50 fixed risk / shared guards</p><p class="note">Result: high win rate and short losing streaks, but too slow for a quick challenge at unchanged risk. Four-EA annual closing return +9.70%, 76.5% wins, PF 1.78, streak 12 wins / 2 losses. Neither pure ORB mix completed both phases in the chronological source year. These are fitted-history proxy scenarios, not measured FTMO floating equity or future pass odds. Nothing is installed, deployed, pushed or changed on a live account.</p>'+''.join(sections)+js+'</body></html>'
    (ROOT/'Results.html').write_text(doc,encoding='utf-8');print('PURE ORB REPORT CREATED')

if __name__=='__main__':main()
