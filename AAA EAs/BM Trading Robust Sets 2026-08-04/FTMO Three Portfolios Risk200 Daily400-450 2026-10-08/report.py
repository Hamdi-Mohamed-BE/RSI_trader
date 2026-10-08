"""Side-by-side standalone research report. No public-site mutations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import html,json
ROOT=Path(__file__).resolve().parent
def e(x):return html.escape(str(x))
def n(x,d=2):return '—' if x is None else f'{x:,.{d}f}'
def date(x):return datetime.fromisoformat(x).astimezone(ZoneInfo('Europe/Prague')).date().isoformat() if x else '—'
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
    d=json.loads((ROOT/'Results.json').read_text());profiles={x['name']:x for x in d['profiles']};policies={x['name']:x for x in d['policies']}
    hist={(x['profile'],x['policy']):x for x in d['historical']};bits=[]
    timing_path=ROOT/'AGGREGATE_TIMING.json'
    timing={(x['protocol'],x['profile'],x['policy'],x['horizon_days']):x['half_of_all_paths_completed_by_days'] for x in json.loads(timing_path.read_text())} if timing_path.exists() else {}
    head=['Metric','Four qualifying ORBs','Current FTMO: 14 EAs','Four ORBs + requested five: 9 EAs']
    for pol in d['policies']:
        xx=[hist[(profile,pol['name'])] for profile in profiles]
        metric=[('Trades',lambda x:x['portfolio']['trades']),('Trades / weekday',lambda x:n(x['trades_per_weekday'])),
                ('Win rate',lambda x:n(x['portfolio']['win_rate'])+'%'),('Net profit factor',lambda x:n(x['portfolio']['pf'])),
                ('Continuous account return',lambda x:n(x['portfolio']['return_pct'])+'%'),
                ('Closed-balance drawdown',lambda x:n(x['portfolio']['closed_balance_dd_pct'])+'%'),
                ('Stop-reserve proxy drawdown',lambda x:n(x['portfolio']['stop_reserve_proxy_dd_pct'])+'%'),
                ('Daily closed Sharpe',lambda x:n(x['portfolio']['daily_closed_sharpe'])),
                ('Max win / loss streak',lambda x:str(x['portfolio']['win_streak'])+' / '+str(x['portfolio']['loss_streak'])),
                ('Worst daily reserve loss (not floating equity)',lambda x:'$'+n(x['worst_daily_reserve_usd'])),
                ('Maximum concurrent initial-risk USD',lambda x:'$'+n(x['max_open_risk']))]
        bits.append('<h2>'+e(pol['label'])+'</h2><p>Historical window: 6 October 2025–5 October 2026 inclusive, $10,000 initial account. Continuous history uses one account, whereas challenge results below reset account capital between phases. The internal loss setting blocks new entries and reserves existing initial-stop risk; it does NOT close the open portfolio at a live floating-equity threshold.</p>'+table(head,[[label]+[f(x) for x in xx] for label,f in metric]))
    rr=[]
    for x in d['historical']:
        c=x['challenge'];passed={z['phase']:z for z in c['passes']}
        rr.append([e(profiles[x['profile']]['label']),e(policies[x['policy']]['label']),date(passed.get(1,{}).get('time')),date(passed.get(2,{}).get('time')),date(c['funded_at']),date(c['receipt_at']),c['phase'],'$'+n(c['balance']),date(c['breach_at'])])
    bits.append('<h2>Actual chronological challenge dates</h2><p>Start 6 October 2025; dates shown in Prague. Blank dates mean the milestone was not reached by the source end. The large continuous annual returns above are not withdrawable challenge income.</p>'+table(['Portfolio','Sizing / stop','Phase 1 passed','Both phases passed','Funded','First paid','End phase','End phase balance','Proxy breach'],rr))
    protocols={}
    for c in d['random_cases']:protocols.setdefault(c['protocol'],[]).append(c)
    for name,cases in protocols.items():
        rows=[]
        for c in cases:
            for z in c['summary']:
                if z['days'] not in (365,730):continue
                rows.append([e(profiles[c['profile']]['label']),e(policies[c['policy']]['label']),z['days'],n(z['phase1_pass_pct'],1)+'%',n(z['both_pass_pct'],1)+'%',n(z['unfinished_evaluation_pct'],1)+'%',n(z['days_to_phase1']['median'],1),n(z['days_to_pass_both']['median'],1),n(timing.get((name,c['profile'],c['policy'],z['days'])),1),n(z['first_reward_received_pct'],1)+'%','$'+n(z['expected_first_reward_usd'])])
        bits.append('<h2>'+e(name)+'</h2><p>1,000 matched joint-market paths per portfolio/policy, preserving cross-EA timing within blocks. Medians marked † are CALENDAR days among paths completing the milestone within that horizon. The separate 50%-of-ALL-paths column includes unfinished starts: a dash means that half of all starts never completed within the stated horizon. Unfinished evaluations remain in the pass-rate denominator; their eventual pass times are unknown. Two-year paths repeat/resample the same historical year, not new two-year evidence.</p>'+table(['Portfolio','Policy','Days','Phase 1 pass','Both-phase pass','Still evaluating','Phase 1 median†','Both-pass median†','50% of ALL paths by','First payment','Expected first reward'],rows))
    rr=[]
    for c in protocols['Joint 4-week blocks']:
        for z in c['summary']:
            if z['days'] not in (90,180):continue
            rr.append([e(profiles[c['profile']]['label']),e(policies[c['policy']]['label']),z['days'],n(z['both_pass_pct'],1)+'%',n(z['days_to_pass_both']['median'],1)])
    bits.append('<h2>Short deadlines: 90 / 180 calendar days</h2>'+table(['Portfolio','Policy','Deadline','Both-phase pass','Conditional median days'],rr))
    rr=[]
    for c in protocols['Joint 4-week blocks']:
        z=next(z for z in c['summary'] if z['days']==365)
        f=z['expected_net_cash_and_fee_roi'][0]
        rr.append([e(profiles[c['profile']]['label']),e(policies[c['policy']]['label']),'$'+n(f['fee_usd']),'$'+n(z['expected_first_reward_usd']),'$'+n(f['expected_net_cash']),n(f['expected_fee_roi_pct'])+'%'])
    bits.append('<h2>Illustrative $150 fee ROI after one year</h2><p>Actual fee not supplied. First-reward-only cash flows: expected reward + first-payment probability × assumed full fee refund − purchase fee. This is not annual recurring income or a valuation of unfinished evaluations. No-payout paths count zero first reward. Administrative waits and reward-payment timing are assumptions.</p>'+table(['Portfolio','Policy','Assumed fee','Expected first reward','Expected net cash','Fee ROI'],rr))
    rr=[]
    for x in d['historical']:
        counts=x['portfolio']['skips']
        rr.append([e(profiles[x['profile']]['label']),e(policies[x['policy']]['label']),counts.get('open_risk_rejected',0),counts.get('correlated_risk_rejected',0),counts.get('daily_budget_rejected',0),counts.get('total_loss_buffer_rejected',0),counts.get('daily_latched_stop',0),counts.get('margin_rejected',0),counts.get('min_lot_over_budget',0)])
    bits.append('<h2>Admission rejections explain the trade-count change</h2><p>$225 total open-risk cap is retained: it normally allows only one full $200 trade at a time. A new $200 trade reserves about $255 plus entry charges. After a full $200 loss, another full-size order would require more than $450 that day, so it is rejected rather than promising that two losses plus costs fit a $400–$450 threshold.</p>'+table(['Portfolio','Policy','Aggregate cap','Symbol cap','Daily reserve','Total buffer','Day latch','Margin','Minimum lot'],rr))
    rr=[]
    for x in d['profiles']:
        rr.append([e(x['label']),x['ea_count'],'<br>'.join(e(k) for k in x['keys'])])
    bits.append('<h2>Exact profile membership</h2><p>Saved launcher manifest: '+e(d['current_manifest_version'])+'. Its legacy folder name says thirteen, but the current package contains FOURTEEN entries. No strategy is silently removed. The nine-EA profile uses the four selected ORB variants (three at 0.5R, Selective US100 at current 2R), plus the current FTMO-input versions of RSI VWAP, Gold Overnight Value Area, Trend Progression, 3-Way Gold and Nasdaq 5M Momentum. No news or hourly-timed EAs are added.</p>'+table(['Portfolio','EAs','Strategies'],rr))
    rows=[]
    for x in d['starts']:
        passed={z['phase']:z for z in x['passes']}
        rows.append([e(profiles[x['profile']]['label']),e(policies[x['policy']]['label']),x['horizon_days'],x['start'],x['end_exclusive'],date(passed.get(1,{}).get('time')),date(passed.get(2,{}).get('time')),date(x['receipt_at']),date(x['breach_at'])])
    bits.append('<details><summary>All 603 real historical start windows</summary><p>40 complete 90-day and 27 complete 180-day Monday starts per portfolio/policy; no source wraparound. These overlapping windows are dependent historical tests, not future pass probabilities.</p>'+table(['Portfolio','Policy','Horizon','Start','End exclusive','Phase 1','Both phases','First paid','Proxy breach'],rows)+'</details>')
    bits.append('<h2>Daily-stop interpretation and limitations</h2><p>'+e(d['stop_policy'])+'</p><p>'+e(d['unchanged_rules'])+'</p><p class="note">'+e(d['hard_stop_warning'])+'</p><ul>'+''.join('<li>'+e(x)+'</li>' for x in d['limitations'])+'</ul><p>Official FTMO losses include floating P&amp;L, commissions and swap, resetting against midnight Prague balance. A closed-balance or reserved-stop model cannot confirm compliance with that true equity rule. See <a href="https://academy.ftmo.com/lesson/maximum-daily-loss/">FTMO daily-equity calculation</a> and <a href="https://ftmo.com/en/2-step-challenge/">2-Step objectives</a>.</p><p>No native shared multi-EA FTMO portfolio was run. No current BAT, SET, EX5, guard, public website or tracked repository file was changed, and nothing was pushed.</p><p><a href="Results.json">All metrics</a> · <a href="VERIFICATION.json">Independent verification</a> · <a href="FROZEN_ROWS.json">Frozen source rows</a></p>')
    doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FTMO three portfolios — $200 risk / $400–$450 stop</title><style>body{font:16px system-ui;background:#071713;color:#edf8f2;max-width:1550px;margin:30px auto;padding:20px}h1{font-size:32px}h2{font-size:23px;margin-top:40px}p,li{color:#b3cfbd;line-height:1.65}.note{padding:18px;border:1px solid #a7883f;border-radius:10px;color:#ffe1a0}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border-bottom:1px solid #2a4336;padding:11px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#73ebbc;background:#10281c}a{color:#75f0bd}summary{cursor:pointer;padding:15px;background:#143124}</style></head><body><h1>FTMO Swing: three portfolios at $200 risk</h1><p>Research only · 8 October 2026 · fixed USD risk / two reserved daily-stop levels</p><p class="note">This comparison stops new entries with a reserved-risk admission budget; it does not force-close a portfolio at measured live floating drawdown. $400 and $450 are tested separately. Pass rates are fitted-history scenarios, not reliable forecasts. Nothing is deployed.</p>'+''.join(bits)+'</body></html>'
    (ROOT/'Results.html').write_text(doc,encoding='utf-8');print('THREE PORTFOLIOS REPORT CREATED')
if __name__=='__main__':main()
