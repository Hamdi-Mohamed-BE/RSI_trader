from __future__ import annotations
import json,math,xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import run_research as r

ROOT=r.ROOT
def money(x):return f'${x:,.2f}' if x>=0 else f'−${-x:,.2f}'
def pf(x):return f'{x:.3f}' if x is not None else 'N/A (no losses)'
def main():
    rows=[json.loads(p.read_text()) for p in sorted((ROOT/'Runs').glob('*.json'))]
    assert len([x for x in rows if x['delay_ms']==1])==24
    assert all(x['source_hashes']==r.fingerprint() for x in rows)
    xmlns={'s':'urn:schemas-microsoft-com:office:spreadsheet'}
    for path in sorted({ROOT/x['report'] for x in rows if x['report'].endswith('.xml')}):
        table=ET.parse(path).findall('.//s:Table/s:Row',xmlns)
        values=[[c.text or '' for c in row.findall('s:Cell/s:Data',xmlns)] for row in table]
        data=[dict(zip(values[0],v)) for v in values[1:]]
        for result in (x for x in rows if ROOT/x['report']==path):
            native=next(x for x in data if int(x['InpExitCase'])==result['case'])
            assert abs(float(native['Profit'])-result['net_profit'])<.011
            assert int(native['Trades'])==result['trades']
    doc=['# LTA XAUUSD — fixed 3R versus volume-profile exits','',
         'Research comparison only. Nothing deployed and no website/BAT changes. Exness Zero demo feed, XAUUSD M15, $10,000 initial USD, 1% equity sizing using the current round-up/min-lot rule. Safe filter ON; account-wide adaptive overlay OFF for this standalone exit comparison. Original entries and initial stops preserved. All standard windows end 2026-09-05 exclusive.','',
         'Net P/L, win rate and profit factor include all recorded commissions, swap and fees. Drawdown below is the larger of native MT5 maximum relative equity drawdown and the independent every-tick observer. It is not closed-balance drawdown.','',
         'The user-confirmed no-TP candidate is **Rolling AOI trail**. Frozen AOI trail is an extra diagnostic, not the recommended implementation. Both keep the same original LTA entry logic. Fewer trades can result from the unchanged one-position-per-symbol rule while an earlier position remains open.','',
         '## Rules','',
         '- Current: fixed 3R target.','- Day/week/combined TP: nearest favorable POC, VAH or VAL from the specified completed profile(s). If none is ahead, use original 3R, with fallback counts disclosed. No minimum-R filter was optimized.',
         '- Frozen trail: no TP; both profiles frozen at entry. A completed M15 close must cross beyond a favorable rung plus the fixed 0.05-entry-ATR buffer. SL moves one rung behind, buffered, and only tightens.',
         '- Rolling trail: same, but loads newly completed day/week profiles for subsequent candles. It never applies a newly calculated profile retroactively.',
         '- TP profile windows exclude the first bar of the current day/week; existing entry-profile boundary semantics are unchanged across every case. 64 bins / 70% value area. Broker tick volume when real volume is unavailable.','',
         'See [frozen protocol](RULES.md) for complete rules, scope, fallback behavior, date boundaries and limitations.','']
    by= {(x['period'],x['case']):x for x in rows if x['delay_ms']==1}
    first_entries={}
    for period in ['6m','1y','3y','5y']:
        first=[]
        for case in range(6):
            ts=json.loads((ROOT/'Audit'/f'{period}-case{case}-d1-trades.json').read_text())
            t=min(ts,key=lambda x:x['open_time'])
            first.append({k:t[k] for k in ('open_time','open_price','direction','volume','initial_sl')})
        assert all(x==first[0] for x in first),('Initial entry parity failed',period,first)
        first_entries[period]=first[0]
    for period in ['6m','1y','3y','5y']:
        doc += [f'## {period} — {r.WINDOWS[period][0]} to {r.WINDOWS[period][1]}','',
                '| Exit | Net P/L | Return | Final balance | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |',
                '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for c in range(6):
            x=by[period,c];dd=max(x['observed_equity_dd_pct'],x['max_equity_dd_pct'])
            doc.append(f"| {x['label']} | {money(x['net_profit'])} | {x['return_pct']:+.2f}% | {money(x['final_balance'])} | {x['trades']} | {x['net_win_rate']:.2f}% | {pf(x['net_pf'])} | {dd:.2f}% | {money(x['commission'])} | {money(x['swap'])} |")
        doc+=['']
    doc+=['## Exit usage and realized behavior — 3 years','',
          '| Exit | AOI targets | 3R fallbacks | Successful SL advances | Native modification failures | Initial target R range | Average win | Average loss | Worst loss streak |',
          '|---|---:|---:|---:|---:|---|---:|---:|---:|']
    monthly=defaultdict(lambda:defaultdict(lambda:{'trades':0,'net':0.,'commission':0.,'swap':0.}))
    for year in range(2023,2027):
        for month in range(1,13):
            if '2023.09'<=f'{year}.{month:02d}'<='2026.09':monthly[f'{year}.{month:02d}']
    for c in range(6):
        x=by['3y',c];s=x['summary'];rr='No TP' if c>=4 else f"{x['planned_rr_min']:.3f}R to {x['planned_rr_max']:.3f}R"
        doc.append(f"| {x['label']} | {int(float(s['aoi_targets']))} | {int(float(s['fallbacks']))} | {int(float(s['trails']))} | {int(float(s['modify_failures']))} | {rr} | {money(x['average_win'])} | {money(x['average_loss'])} | {x['max_loss_streak']} |")
        trades=json.loads((ROOT/'Audit'/f'3y-case{c}-d1-trades.json').read_text())
        for t in trades:
            b=monthly[t['close_time'][:7]][c];b['trades']+=1;b['net']+=t['net'];b['commission']+=t['commission'];b['swap']+=t['swap']
    doc+=['','## Closed-trade monthly P/L — 3-year run','',
          'Month allocation uses exit time and includes each trade’s recorded fees. Floating profits/losses are not monthly realized P/L. First and last months are partial.','',
          '| Month | '+' | '.join(r.LABELS)+' |','|---|'+'---:|'*6]
    for month,values in sorted(monthly.items()):
        doc.append('| '+month+' | '+' | '.join(f"{money(values[c]['net'])} ({values[c]['trades']} trades)" for c in range(6))+' |')
    events=r.csvrows(ROOT/'Audit'/'3y-case5-d1-events.csv')
    from collections import Counter
    counts=Counter(e['position_id'] for e in events if e['event']=='trail')
    example=next((e for e in events if e['event']=='entry' and counts[e['position_id']]>=3),None)
    if example:
        doc+=['','## An actual no-TP staircase example','',
              f"Broker timestamp {example['time']}: {'BUY' if int(example['dir'])>0 else 'SELL'} at {float(example['entry']):.3f}, initial SL {float(example['sl']):.3f}, TP = none. These are historical broker prices, not current trade advice.",'',
              '| Confirmed at | Broken AOI | Preceding AOI | Previous SL | New SL |','|---|---:|---:|---:|---:|']
        for e in [x for x in events if x['position_id']==example['position_id'] and x['event']=='trail'][:6]:
            doc.append(f"| {e['time']} | {float(e['broken']):.3f} | {float(e['previous']):.3f} | {float(e['old_sl']):.3f} | {float(e['sl']):.3f} |")
    doc+=['','## Boundary-exit sensitivity','',
          'End-of-test liquidations are included in the main results, as in the native tester. These diagnostics separate their contribution; excluding them is NOT a replacement equity backtest.','',
          '| Period / exit | Boundary-closed positions | Their net P/L | Other closed-trade net P/L | Longest hold (days) |',
          '|---|---:|---:|---:|---:|']
    from datetime import datetime
    for period in ['6m','1y','3y','5y']:
        for c in (4,5):
            ts=json.loads((ROOT/'Audit'/f'{period}-case{c}-d1-trades.json').read_text())
            boundary=[t for t in ts if any('end of test' in s.lower() for s in t['exit_comments'])]
            longest=max(((datetime.strptime(t['close_time'],'%Y.%m.%d %H:%M:%S')-datetime.strptime(t['open_time'],'%Y.%m.%d %H:%M:%S')).total_seconds()/86400 for t in ts),default=0)
            bnet=sum(t['net'] for t in boundary)
            doc.append(f"| {period} / {r.LABELS[c]} | {len(boundary)} | {money(bnet)} | {money(by[period,c]['net_profit']-bnet)} | {longest:.1f} |")
    failures=Counter()
    for x in rows:
        es=r.csvrows(ROOT/'Audit'/f"{x['period']}-case{x['case']}-d{x['delay_ms']}-events.csv")
        failures.update(e['note'] for e in es if e['event']=='order_failed')
    doc+=['','## Evidence and caveats','',
          '- Recorded entry rejections across retained runs: '+str(dict(failures))+'. These remain in the audit; rejected orders are not invented trades. Successful trailing SL changes are checked against broker return codes.',
          '- These are six predeclared mechanical variants, not a full optimization pipeline. The overlapping periods are not independent out-of-sample tests. No deployment or guaranteed profitability is implied.',
          '- Each is a complete independent EA run. Different exits change holding periods, which later entries are available, daily-loss locks and compounded position sizes. They are not identical-entry replay comparisons.',
          '- The current round-up sizing policy can exceed 1% planned stop risk: maximum across these runs '+f"{max(x['max_planned_risk_equity_pct'] for x in rows):.2f}%"+'. This policy was not altered by exit research.',
          '- Model 4 was requested. Real-tick coverage must be read with the source journals; pre-2026 history can use generated ticks. Historical fee schedules, news high-margin requirements and all live slippage are not reconstructed.',
          '- Closed trades at the end of a test can include forced boundary exits. A no-TP variant can hold one trade for a long period and block new entries; high profit factor with few trades is not strong evidence.',
          '- Original active code/SET and shared includes were preserved. Source-fidelity/unit checks and per-trade profile-direction/candle/SL/ledger assertions accompany the evidence.',
          '- Six prototype preflight passes are retained separately and excluded from the primary results; final results use resized per-entry arrays to prevent stale ladder levels when profiles contain duplicate levels.','']
    stress=[x for x in rows if x['delay_ms']!=1]
    if stress:
        doc+=['## Native execution-delay sensitivity','',
              '| Period / exit | Delay | Return | Trades | Net PF | Max equity DD |','|---|---:|---:|---:|---:|---:|']
        for x in stress:doc.append(f"| {x['period']} / {x['label']} | {x['delay_ms']} ms | {x['return_pct']:+.2f}% | {x['trades']} | {pf(x['net_pf'])} | {max(x['max_equity_dd_pct'],x['observed_equity_dd_pct']):.2f}% |")
        doc+=['','Delay can change the full trade path. This is not a guarantee of execution during news or gaps.','']
    doc+=['## Native MT5 reports','']
    for path in sorted({x['report'] for x in rows}):doc.append(f'- [{Path(path).name}](<'+path.replace('\\','/')+'>)')
    verdict=['## Conclusion','',
             '**Keep the current 3R preset for now. Do not deploy the no-TP rolling trail on this evidence.**',
             'The rolling no-TP exit preserved entry logic but reduced return and increased equity drawdown versus 3R over every tested period. Previous-week targets improved 6m and 3y returns but did not beat the 5y control and carried substantially higher 5y drawdown. Nearest-level exits increased win rate at the cost of much smaller average wins; higher hit rate was not an overall improvement.',
             'Weekly AOI targets may merit a separately approved minimum-R / hybrid-exit experiment, but no such improvement was optimized or validated here. The frozen no-TP diagnostic is unsuitable as a deployment candidate because of sparse trades, large drawdowns and boundary-exit dependence.','']
    doc[2:2]=verdict
    (ROOT/'LTA AOI RESULTS.md').write_text('\n'.join(doc)+'\n',encoding='utf-8')
    r.save(ROOT/'verdict.json',{'recommendation':'KEEP_CURRENT_3R','rolling_no_tp':'DO_NOT_PROMOTE','weekly_aoi':'FURTHER_RESEARCH_ONLY',
                              'live_or_website_changes':False,'reason':'No proposed exit dominates current 3R across horizons; rolling no-TP has lower return and higher DD in all four.'})
    r.save(ROOT/'results.json',rows)
    r.save(ROOT/'verification.json',{'final_records':len(rows),'core_fidelity':'11 unit/source tests; see test_rules.py',
                                   'first_entry_identical_all_six_variants_each_period':first_entries,
                                   'xml_net_profit_and_trade_counts':'verified','ledger_and_exit_rules':'verified during analysis',
                                   'maximum_modification_failures':max(int(float(x['summary']['modify_failures'])) for x in rows),
                                   'total_order_failures':sum(int(float(x['summary']['order_failures'])) for x in rows),
                                   'source_fingerprints':r.fingerprint()})
    print('REPORT AND VERIFICATION WRITTEN',flush=True)
if __name__=='__main__':main()
