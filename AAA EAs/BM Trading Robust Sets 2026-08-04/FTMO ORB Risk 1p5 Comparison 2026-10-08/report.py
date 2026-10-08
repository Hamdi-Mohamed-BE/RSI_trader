"""Standalone risk sensitivity report, not the public website."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import html,json
ROOT=Path(__file__).resolve().parent
def e(x):return html.escape(str(x))
def n(x,d=2):return '—' if x is None else f'{x:,.{d}f}'
def local(x):return datetime.fromisoformat(x).astimezone(ZoneInfo('Europe/Prague')).date().isoformat() if x else '—'
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
    d=json.loads((ROOT/'Results.json').read_text());labels={x['name']:x['label'] for x in d['risk_cases']}
    bits=[]
    rows=[];dates=[]
    for x in d['historical']:
        m=x['portfolio'];c=x['challenge'];passed={z['phase']:z for z in c['passes']}
        rows.append([e(x['label']),m['trades'],n(x['trades_per_weekday']),n(m['win_rate'])+'%',n(m['pf']),n(m['return_pct'])+'%',n(m['closed_balance_dd_pct'])+'%',n(m['stop_reserve_proxy_dd_pct'])+'%',n(m['daily_closed_sharpe']),str(m['win_streak'])+'/'+str(m['loss_streak'])])
        dates.append([e(x['label']),local(passed.get(1,{}).get('time')),local(passed.get(2,{}).get('time')),local(c['funded_at']),local(c['receipt_at']),c['phase'],'$'+n(c['balance'])])
    bits.append('<h2>Historical shared portfolio</h2><p>6 October 2025–5 October 2026 inclusive. Continuous account return is not challenge income: each phase starts again at $10,000, and the payout model stops at the first reward. Four unchanged ORBs: US100 H1, Gold NY M30 and Gold London–NY Overlap at 0.5R; Selective US100 at its existing 2R target (only five source trades). All weekdays, including zero-trade weekdays, are counted.</p>'+table(['Risk sizing','Trades','Trades/weekday','Win rate','PF','Return','Closed DD','Stop-reserve proxy DD','Daily closed Sharpe','Streak wins/losses'],rows))
    bits.append('<h2>Chronological challenge dates</h2><p>Prague calendar dates; administrative delays are assumptions, not promised processing times.</p>'+table(['Risk sizing','Phase 1','Both phases','Funded','First paid','End phase','End phase balance'],dates))
    rejected=[]
    for x in d['historical']:
        m=x['portfolio']['skips']
        rejected.append([e(x['label']),m.get('correlated_risk_rejected',0),m.get('open_risk_rejected',0),m.get('daily_budget_rejected',0),m.get('min_lot_over_budget',0)])
    bits.append('<h2>Why requested risk is not the same as admitted risk</h2><p>'+e(d['guard_warning'])+'</p><p>The $150 request is 1.5% of INITIAL capital, not dynamic 1.5%. In the dynamic version the budget rises with balance; if the rounded order risk exceeds $150, it is rejected rather than resized to the cap. The literal unchanged limits therefore prevent an ordinary compounding test. Changing those caps would be another scenario, not something silently done here.</p>'+table(['Risk sizing','Symbol-cap rejections','Aggregate-cap rejections','Daily reserve rejections','Minimum-lot skips'],rejected))
    protocols={}
    for c in d['random_cases']:protocols.setdefault(c['protocol'],[]).append(c)
    for protocol,cases in protocols.items():
        rr=[]
        for c in cases:
            for z in c['summary']:
                rr.append([e(labels[c['mode']]),z['days'],n(z['phase1_pass_pct'],1)+'%',n(z['both_pass_pct'],1)+'%',n(z['unfinished_evaluation_pct'],1)+'%',n(z['days_to_phase1']['median'],1),n(z['days_to_pass_both']['median'],1),n(z['first_reward_received_pct'],1)+'%','$'+n(z['expected_first_reward_usd'])])
        bits.append('<h2>'+e(protocol)+'</h2><p>1,000 paths for each risk case, identical market blocks. Pass medians are CALENDAR days and conditional on completion inside the stated horizon; they are not an unconditional expected time for unfinished paths. 730 days resamples the SAME source year, not additional two-year evidence.</p>'+table(['Risk sizing','Horizon days','Phase 1 pass','Both phases pass','Still evaluating','Phase 1 median†','Both-pass median†','First payment','Expected first reward'],rr))
    months=sorted({m for x in d['historical'] for m in x['portfolio']['months']})
    rr=[]
    for m in months:
        rr.append([m]+[n(x['portfolio']['months'].get(m,{}).get('net',0)/100)+'% / '+str(x['portfolio']['months'].get(m,{}).get('trades',0)) for x in d['historical']])
    bits.append('<h2>Monthly return / trades</h2>'+table(['Month']+[x['label'] for x in d['historical']],rr))
    rr=[]
    for x in d['historical']:
        for z in x['log']:
            rr.append([e(x['label']),e(z['ea']),e(z['open']),e(z['close']),n(z['lots']),n(z['balance_before_entry']),n(z['planned_risk_budget']),n(z['initial_risk']),n(z['net_profit']),n(z['balance'])])
    bits.append('<details><summary>All admitted historical trades and entry budgets</summary>'+table(['Sizing','EA','Open UTC','Close UTC','Lots','Balance before entry','Requested risk budget','Actual initial stop risk','Net P&amp;L','Closing balance'],rr)+'</details>')
    bits.append('<h2>Assumptions and limitations</h2><p>'+e(d['primary_interpretation'])+'</p><p>'+e(d['live_guard_warning'])+'</p><p>Our admission settings remain: $225 portfolio and $150 symbol initial exposure, $300 daily reserve, $9,200 equity admission floor, 7 entries and 3 closed losses per Prague day; 1.25× initial-risk reserve plus $5 per open position. Official FTMO 2-Step objectives remain 10%/5% targets, 5% maximum daily loss, 10% maximum loss and four entry days per phase. See <a href="https://ftmo.com/en/2-step-challenge/">FTMO 2-Step objectives</a> and <a href="https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/">Swing account rules</a>.</p><ul>'+''.join('<li>'+e(x)+'</li>' for x in d['limitations'])+'</ul><p>No live account, BAT, SET, EX5, public website, guard or repository-tracked file changed. No push was requested.</p><p><a href="Results.json">Full results</a> · <a href="VERIFICATION.json">Independent verification</a></p>')
    doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FTMO pure ORB — 1.5% risk sensitivity</title><style>body{font:16px system-ui;background:#071713;color:#edf8f2;max-width:1500px;margin:30px auto;padding:20px}h1{font-size:34px}h2{font-size:23px;margin-top:40px}p,li{color:#b3cfbd;line-height:1.65}.note{padding:18px;border:1px solid #a7883f;border-radius:10px;color:#ffe1a0}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border-bottom:1px solid #2a4336;padding:11px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#73ebbc;background:#10281c}a{color:#75f0bd}summary{cursor:pointer;padding:15px;background:#143124}</style></head><body><h1>FTMO pure ORB: 1.5% risk sensitivity</h1><p>Research only · 8 October 2026 · four-EA shared $10,000 Swing model</p><p class="note">Fixed $150 improves fitted-history challenge speed but raises drawdown. True dynamic 1.5% stalls under the unchanged $150 symbol cap. Neither result is a calibrated future pass probability or measured floating-equity replay. Nothing was deployed.</p>'+''.join(bits)+'</body></html>'
    (ROOT/'Results.html').write_text(doc,encoding='utf-8');print('RISK REPORT CREATED')
if __name__=='__main__':main()
