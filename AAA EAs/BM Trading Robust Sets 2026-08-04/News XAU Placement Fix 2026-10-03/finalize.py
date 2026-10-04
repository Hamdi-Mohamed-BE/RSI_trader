"""Reconcile frozen research, compile production in place, write evidence receipt.
Never attach the build to, restart, or change the normal MT5 terminal.
"""
import gzip
import json
import re
import statistics
import subprocess
import time
from collections import defaultdict
from datetime import date, timedelta
import run as study


def messages(folder):
    # Both the local agent and terminal repeat the same message. Count once.
    raw=gzip.decompress((folder/'journal.gz').read_bytes()).decode()
    return {(t,m.strip()) for t,m in re.findall(r'\b(202\d\.\d\d\.\d\d \d\d:\d\d:\d\d)\s+(.*)',raw)}


def detail(result):
    folder=study.R/'native'/result['tag']
    trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
    msgs=messages(folder)
    accepted={re.search(r'NP\|(\d+)\|(NFP|CPI|FOMC)\|([BS])',m).groups()
              for _,m in msgs if m.startswith('NP_SIDE_ACCEPTED|')}
    all_rejected=[(t,m) for t,m in msgs if 'CTrade::OrderSend:' in m and
               any(x in m for x in ['[invalid price]','[invalid expiration]','[invalid stops]'])]
    rejection=[(t,m) for t,m in all_rejected if 'modify position' not in m]
    modify_rejections=[(t,m) for t,m in all_rejected if 'modify position' in m]
    event_counts=defaultdict(int)
    for epoch,kind,side in accepted:event_counts[epoch]+=1
    daily=defaultdict(float)
    for x in trades:daily[x['close_time'][:10]]+=x['net_profit']
    balance=10000; returns=[]
    day=date(2025,10,3);end=date(2026,10,3)
    while day<end:
        change=daily[str(day)]
        if day.weekday()<5:returns.append(change/balance)
        balance+=change;day+=timedelta(days=1)
    sharpe=(statistics.mean(returns)/statistics.stdev(returns)*252**.5) if statistics.stdev(returns)>0 else None
    old=[x for x in trades if x['open_time'][:10]<'2026-01-01']
    real=[x for x in trades if x['open_time'][:10]>='2026-01-01']
    gp=sum(x['net_profit'] for x in real if x['net_profit']>0)
    gl=-sum(x['net_profit'] for x in real if x['net_profit']<0)
    start_real=10000+sum(x['net_profit'] for x in old)
    families={}
    for kind in ['NFP','CPI','FOMC']:
        rows=[x for x in trades if '|'+kind+'|' in x['entry_comment']]
        wins=sum(x['net_profit']>0 for x in rows)
        gains=sum(x['net_profit'] for x in rows if x['net_profit']>0)
        losses=-sum(x['net_profit'] for x in rows if x['net_profit']<0)
        families[kind]=dict(trades=len(rows),net=sum(x['net_profit'] for x in rows),
            win_rate_pct=100*wins/len(rows) if rows else None,pf=gains/losses if losses else None)
    return dict(**{**result,'families':families},unique_broker_rejections=sorted(rejection),
        unique_modify_rejections=sorted(modify_rejections),
        accepted_sides=len(accepted),complete_two_sided_events=sum(n==2 for n in event_counts.values()),
        daily_closed_balance_sharpe=sharpe,weekday_observations=len(returns),
        real_tick_subperiod=dict(from_date='2026-01-01',to_exclusive='2026-10-03',
            not_fresh_balance_backtest=True,starting_balance=start_real,trades=len(real),
            net=sum(x['net_profit'] for x in real),return_pct=100*sum(x['net_profit'] for x in real)/start_real,
            win_rate_pct=100*sum(x['net_profit']>0 for x in real)/len(real),pf=gp/gl if gl else None))


def main():
    study.free()
    summary=json.loads((study.R/'SUMMARY.json').read_text())
    assert json.loads((study.R/'FAULT_CHECK.json').read_text())['passed']
    rows=[detail(x) for x in summary['results'] if x['from_date']=='2025.10.03']
    assert len(rows)==4
    for result in rows:
        assert result['source_sha']==study.sha(study.R/'snapshot'/(result['name']+'.mq5'))
        if result['name'].startswith('New-'):
            assert result['complete_two_sided_events']==30 and result['accepted_sides']==60
            assert not result['unique_broker_rejections'] and result['closure_violations']==0
    # Match live-capable production to the tested private wrapper, apart from
    # flattened includes and its explicit tester-only initialization guard.
    body=study.read(study.SOURCE).replace('\r\n','\n')
    body=re.sub(r'#include "[^"\r\n]*[/\\]([^"/\\]+)"',r'#include "\1"',body)
    body=body.replace('int OnInit()\n{','int OnInit()\n{\n   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;')
    assert body==study.read(study.R/'snapshot/New-fixed-test.mq5').replace('\r\n','\n')
    log=study.R/'production.compile.log';began=time.time()
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    subprocess.run(f'"{study.T/"metaeditor64.exe"}" /portable /compile:"{study.SOURCE}" /log:"{log}"',
        startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    assert '0 errors, 0 warnings' in study.read(log),study.read(log)[-4000:]
    assert study.SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
    release=dict(version='2.20',source=str(study.SOURCE),source_sha256=study.sha(study.SOURCE),
        binary_sha256=study.sha(study.SOURCE.with_suffix('.ex5')),set_sha256=study.sha(study.SET),
        helper_sha256=study.sha(study.SOURCE.parent/'NewsPulsePlacement.mqh'),compile_passed=True,
        active_terminal_changed=False,live_chart_deployed=False,github_pushed=False)
    study.save(study.R/'RELEASE.json',release)
    study.save(study.R/'ANALYSIS.json',dict(**summary,comparisons=rows,release=release,
        caveat='75% real ticks. Previously fitted baseline overlaps the window. No live-liquidity model or out-of-sample validation.'))
    lines=['XAU NEWS PULSE - MATCHED OLD/NEW NATIVE MT5 REPLAY',
        '2025-10-03 inclusive to 2026-10-03 exclusive; includes 2 October NFP.',
        '$10,000 USD start; 0.75% equity risk per side; isolated Exness XAUUSD tester.',
        'Real-tick mode requested; report quality 75% real ticks. Before January 2026 ticks are generated.',
        '', 'Variant | Delay | Return | NET PF | Net win rate | Trades | Native equity DD | Win / loss streak | Weekday closed-balance Sharpe']
    for row in rows:
        m=row['net_metrics'];n=row['native']
        lines.append(f"{row['name']} | {row['delay_ms']}ms | {m['return_pct']:+.2f}% | {m['pf']:.3f} | {m['win_rate_pct']:.2f}% | {m['trades']} | {n['max_drawdown_pct']:.2f}% | {m['max_win_streak']} / {m['max_loss_streak']} | {row['daily_closed_balance_sharpe']:.2f}")
    lines+=['', '150ms event-family breakdown: kind / trades / net cash / net wins / net PF']
    for row in rows:
        if row['delay_ms']!=150:continue
        lines.append(row['name'])
        for kind,m in row['families'].items():
            pf=f"{m['pf']:.3f}" if m['pf'] is not None else 'undefined (no net losses)'
            lines.append(f"  {kind}: {m['trades']} / ${m['net']:.2f} / {m['win_rate_pct']:.2f}% / {pf}")
        accepted=str(row['complete_two_sided_events']) if row['name'].startswith('New-') else 'not instrumented in old source'
        lines.append(f"  Placement rejections: {len(row['unique_broker_rejections'])}; trailing-modify rejections: {len(row['unique_modify_rejections'])}; complete two-side acknowledgements: {accepted}")
    lines+=['', 'Real-tick subperiod (Jan 1-Oct 3, same ledger; NOT a fresh-balance backtest):']
    for row in rows:
        m=row['real_tick_subperiod']
        lines.append(f"{row['name']} {row['delay_ms']}ms: return {m['return_pct']:+.2f}% on Jan starting balance ${m['starting_balance']:.2f}, net PF {m['pf']:.3f}, win {m['win_rate_pct']:.2f}%, {m['trades']} trades.")
    lines+=['', 'EXECUTION CHECKS AND LIMITS',
        '31 official scheduled releases: NFP12 / CPI11 / FOMC8. All 30 tradable events attempted.',
        '3 April NFP was on Good Friday during XAU market closure; no usable placement-window quote.',
        'Corrected new model: 60 sides accepted, 30 complete straddles, zero rejected submissions or duplicate side/event entries in each year replay.',
        'One FOMC trailing-stop modification was rejected at 150ms; original protective SL remained. This was not an entry rejection.',
        'Old model can count a partially accepted setup as successful; inspect unique rejection records in ANALYSIS.json.',
        'Both pending directions remain active (NOT OCO). Missing sides retry before release only.',
        'Same-direction market fallback is reserved for price crossing a frozen pending level during submission.',
        'Native fault test forced a crossed buy, skipped the first sell, manually closed buy and reloaded masks: repair and no re-entry checks passed.',
        'native/New-test-* is the DISQUALIFIED short-expiration prototype; it is retained for debugging, not included in the final comparison. New-fault-test is fault injection, not performance evidence.',
        'Cleanup starts at event+30 seconds for THIS EA symbol/magic only, not every account trade.',
        'Broker execution can finish later; both tester delays had no closes later than T+30 plus delay plus a 2-second execution tolerance.',
        'Pending server expiration is a >=120-second whole-minute backup. Positions still require the EA connected/running for timed close.',
        '$10 SL and $6 offset are XAU price distances, not $10/$6 account risk. Broker tick/stops restrictions can widen geometry.',
        'Lots are rounded up, and broker minimum lot, gaps, fees or market-fill slippage can exceed selected risk.',
        'No blind retry of unknown broker responses. No system can guarantee orders through market closure, permission, margin or network failure.',
        '', 'INTERPRETATION',
        'New version improves placement reliability, win rate and drawdown here; it reduces historical return and PF materially.',
        'These tests are not forward profitability proof: only 29 new trades, partly generated ticks and a hindsight-fitted old baseline.',
        'The baseline used separate $1/$2 offsets, $2 stops and 60/300/120-second holds; this is a bundled change, not an isolated stop-size experiment.',
        'Sharpe above is recomputed from weekday closing-balance returns including zero-trade days; it excludes intraday floating P/L. Native huge Sharpe values are not comparable.',
        'Old website cached returns are withheld for the changed source/SET; they were NOT relabelled as new results.',
        '', 'DELIVERY',
        'Production v2.20 source, compiled EX5, selected SET, shared installer and website logic updated.',
        'No normal MT5 terminal restarted, no running chart changed, no live trade placed, no Git push.',
        'Reinstall/reload the revised compiled EA when you choose to use it. Other news EAs and FTMO news-OFF policy are unchanged.',
        'See RELEASE.json, ANALYSIS.json, SUMMARY.json, FAULT_CHECK.json and native compressed reports/deals for receipts.']
    (study.R/'RESULTS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    study.status('COMPLETE verified comparison and production build; running MT5 unchanged')


if __name__=='__main__':main()
