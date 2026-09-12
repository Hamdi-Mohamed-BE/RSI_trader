from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import run_raw as raw

ROOT=Path(__file__).resolve().parent

def stamp(value):
    return datetime.strptime(value, '%Y.%m.%d %H:%M:%S')

@lru_cache(maxsize=1)
def journal_blocks():
    blocks={}
    for path in sorted((raw.TESTER/'Tester').glob('Agent-*/logs/20260912.log')):
        data=path.read_bytes()
        lines=data.decode('utf-16' if data[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8',errors='replace').splitlines()
        starts=[i for i,line in enumerate(lines) if 'XAU London Opening Sweep FVG Raw.ex5 from ' in line and 'started with inputs:' in line]
        for start in starts:
            finish=next((i for i in range(start+1,len(lines)) if 'MetaTester 5 stopped' in lines[i]),len(lines)-1)
            block='\n'.join(lines[max(0,start-5):finish+1])
            magic=re.search(r'InpMagic=(\d+)',block)
            if magic:blocks[int(magic.group(1))]=block
    return blocks

def validate(tf, period):
    tag=f'xau-london-sweep-fvg-m{tf}-{period}-model4'
    stats=json.loads((ROOT/f'{tag}-stats.json').read_text())
    rows=list(csv.DictReader((ROOT/'Audit'/f'{tag}.csv').open(encoding='utf-8-sig')))
    trades=json.loads((ROOT/'Audit'/f'{tag}-trades.json').read_text())
    orders={}
    fills=Counter()
    late_ranges=[]
    late_sweeps=[]
    for row in rows:
        server=stamp(row['server_time'])
        london=stamp(row['london_time'])
        expected=server.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Europe/London')).replace(tzinfo=None)
        assert london==expected, ('London DST mismatch', row)
        date=london.date()
        kind=row['event']
        if kind=='range':
            assert 9<=london.hour<17, ('opening range used before close',row)
            if london.hour!=9 or london.minute!=0:late_ranges.append(row['london_time'])
            assert float(row['range_high'])>float(row['range_low'])
        if kind=='sweep':
            assert 10<=london.hour<17
            assert stamp(row['sweep_confirmed']).minute==0
            assert server>=stamp(row['sweep_confirmed'])
            if (server-stamp(row['sweep_confirmed'])).total_seconds()>=60:late_sweeps.append(row['london_time'])
        if kind in ('fvg','limit'):
            assert server>=stamp(row['sweep_confirmed'])  # confirmed H1, no future signal
            assert (server-stamp(row['sweep_confirmed'])).total_seconds()>=3*tf*60
            assert 10<=london.hour<17
            entry, stop, target=map(float,(row['entry'],row['stop'],row['target']))
            if kind=='limit':
                if int(row['bias'])>0:
                    assert stop<entry<target and math.isclose(target,float(row['range_high']),abs_tol=.002)
                else:
                    assert target<entry<stop and math.isclose(target,float(row['range_low']),abs_tol=.002)
                orders[date]=row
        if kind=='fill':
            assert date in orders and stamp(orders[date]['server_time'])<=server
            fills[date]+=1
            assert fills[date]==1, ('multiple fills on one London day',row)
    assert sum(fills.values())==len(trades)==stats['trades']==stats['audit_fills']
    assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.05
    report=ROOT/'Backtest Reports'/f'{tag}.htm'
    soup=raw.parser.read_report(report)
    assert f'InpEntryTimeframe={tf}' in soup.get_text(), ('wrong timeframe in native report',report)
    cells={}
    for tr in soup.find_all('tr'):
        values=[raw.parser.compact(x.get_text(' ',strip=True)) for x in tr.find_all(['td','th'],recursive=False)]
        for i,value in enumerate(values[:-1]):
            if value.endswith(':'):cells[value[:-1]]=values[i+1]
    stats['equity_drawdown_relative_pct']=raw.parser.percent(cells.get('Equity Drawdown Relative',''))
    stats['balance_drawdown_relative_pct']=raw.parser.percent(cells.get('Balance Drawdown Relative',''))
    stats['raw_report']=str(report.relative_to(ROOT))
    filled_rr=[t['planned_rr'] for t in trades if 'planned_rr' in t]
    stats['median_filled_planned_rr']=statistics.median(filled_rr) if filled_rr else None
    yearly=defaultdict(lambda:{'trades':0,'net':0.0})
    for t in trades:
        year=t['close_time'][:4]
        yearly[year]['trades']+=1;yearly[year]['net']+=t['net_profit']
    stats['calendar_years']={year:{**row,'net':round(row['net'],2)} for year,row in yearly.items()}
    stats['audit_passed']=True
    stats['late_range_observations']=late_ranges
    stats['late_sweep_observations']=late_sweeps
    stats['exit_reasons']=dict(Counter(r['detail'] for r in rows if r['event']=='exit'))
    stats['source_sha256']=hashlib.sha256(raw.SOURCE.read_bytes()).hexdigest()
    magic=84124000+tf*100+list(raw.WINDOWS).index(period)*10+4
    journal=journal_blocks()[magic]
    assert 'generating based on real ticks' in journal
    assert 'testing with execution delay 1 milliseconds' in journal
    assert 'final balance ' in journal and 'MetaTester 5 stopped' in journal
    rejected=[line.split('\t')[-1] for line in journal.splitlines() if 'not enough money for order' in line]
    stats['activation_margin_rejections']=len(rejected)
    stats['activation_margin_rejection_examples']=rejected[:5]
    stats['fixed_execution_delay_ms']=1
    stats['real_ticks_begin']='2026-01-01'
    (ROOT/'Audit'/f'{tag}-tester-journal.txt').write_text(journal+'\n',encoding='utf-8')
    return stats,trades

def main():
    results=[]
    ledgers={}
    for period in raw.WINDOWS:
        for tf in (1,5,15):
            row,trades=validate(tf,period)
            results.append(row)
            if period=='5y':ledgers[tf]=trades
    (ROOT/'VERIFIED RESULTS.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    columns=['entry_timeframe','period','return_pct','net_ledger_pf','win_rate_pct','equity_drawdown_relative_pct','trades','history_quality','commission','swap','max_win_streak','max_loss_streak','execution_errors','activation_margin_rejections','overnight_trades']
    print(json.dumps([{key:r[key] for key in columns} for r in results],indent=2))
    lines=['# XAU London Opening Sweep + FVG — raw timeframe comparison','',
           'Native MT5 test of the frozen transcript interpretation in RAW RULES.md. The only compared strategy setting is M1, M5 or M15 FVG entry timeframe; stop is one tick beyond the FVG, and target is the opposite opening-range boundary.','',
           'USD 10,000 initial balance; Exness-MT5Trial16 XAUUSD CFD, tester leverage 1:2000; 1% requested equity risk, rounded up to broker volume step/minimum. Recorded commission, variable spread and swaps are included. The native journal confirms a FIXED 1 ms execution delay, not a random-delay stress test. Stop fills use simulated available quotes; this does not reproduce all live slippage, liquidity or market impact. Risk to the initial stop excludes additional transaction costs and gaps.','',
           'PF below is recomputed from net closed trades including fees. It can differ slightly from the rounded native headline PF. Drawdown is native relative EQUITY drawdown, including floating P/L.','',
           '| Period | Entry | Return | PF | Win rate | Max equity DD | Trades | Max W/L streak | Commission | Swap |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        lines.append(f"| {r['period']} | {r['entry_timeframe']} | {r['return_pct']:+.2f}% | {r['net_ledger_pf']:.2f} | {r['win_rate_pct']:.2f}% | {r['equity_drawdown_relative_pct']:.2f}% | {r['trades']} | {r['max_win_streak']}/{r['max_loss_streak']} | ${r['commission']:,.2f} | ${r['swap']:,.2f} |")
    lines+=['','## Exact date ranges','']
    for period,(start,end) in raw.WINDOWS.items():lines.append(f'- {period}: {start.replace(".","-")} through {end.replace(".","-")} (end exclusive).')
    lines+=['','## Verification','',
            'All trade ledgers reconcile to native MT5 net P/L and trade counts. The audit independently checks Europe/London DST, completed H1 sweeps, at least three completed lower-timeframe candles after confirmation, correct stop/target direction, entry after FVG confirmation and no more than one fill per London date. No trades are removed from the results.','',
            '| Period | Entry | MT5 history quality | EA placement/close errors | Margin rejections at activation | Overnight trades |','|---|---|---|---:|---:|---:|']
    for r in results:lines.append(f"| {r['period']} | {r['entry_timeframe']} | {r['history_quality']} | {r['execution_errors']} | {r['activation_margin_rejections']} | {r['overnight_trades']} |")
    lines+=['',
            'An accepted pending order is not a guaranteed fill. The tester journal separately records margin failures when orders activate; these are included above and must not be confused with zero EA placement/close errors. M1 five-year balance falls to $1.02 and its last filled trade is 2024-03-22: later signals still occur but the account cannot finance the minimum lot. Consequently, five-year counts are not directly comparable with shorter runs restarted at $10,000.','',
            'Occasional gaps in older quotes delay observation of an already closed range or sweep. These are retained and recorded as late_range_observations / late_sweep_observations in VERIFIED RESULTS.json, rather than filled in using future data.']
    lines+=['','## Five-year detail','',
            '| Entry | Final balance | Wins / losses | Average win | Average loss | Expected net / trade | Long net | Short net | Median planned RR of fills |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        if r['period']=='5y':lines.append(f"| {r['entry_timeframe']} | ${r['final_balance']:,.2f} | {r['wins']} / {r['losses']} | ${r['average_win']:,.2f} | ${r['average_loss']:,.2f} | ${r['expected_payoff']:,.2f} | ${r['long_net']:,.2f} | ${r['short_net']:,.2f} | {r['median_filled_planned_rr']:.2f}R |")
    lines+=['','## Five-year calendar breakdown','',
            '| Entry | Calendar year | Trades | Net P/L |','|---|---|---:|---:|']
    for r in results:
        if r['period']=='5y':
            for year,item in r['calendar_years'].items():lines.append(f"| {r['entry_timeframe']} | {year} | {item['trades']} | ${item['net']:,.2f} |")
    lines+=['','Calendar amounts come from the continuously compounded five-year run; 2021 and 2026 are partial years. They are not independent annual restarts.','',
            'The actual real-tick percentage is reported above. Missing broker tick history can be replaced with generated ticks by MT5 even when Model=4 is requested; see https://www.metatrader5.com/en/terminal/help/algotrading/testing_features .','',
            'Native HTML reports and plots are in Backtest Reports. Audit contains every signal event, each native tester journal and the complete closed trade JSON ledgers. This is research only; no website, installer or live EA was updated.','',
            '## Conclusion and review decision','',
            'No timeframe is a robust winner under this raw interpretation. M5 is the only positive six-month candidate (+11.61%, 21 trades, 19.05% wins), but loses over one, three and five years. M15 has smaller losses and far fewer trades; that is not evidence of a profitable edge. Do not deploy or call this a high-win-rate strategy.','',
            'The one-tick-beyond-FVG stop can be much narrower than spread. Example: M1 on 2026-03-09 had a planned $0.030 stop distance and 32.98 lots; the actual trade lost $1,830.39 including $181.39 commission. A nominal 1% risk calculation does not cap realized loss.','',
            'Recommendation: do not run broad parameter optimization yet. If the user approves a further experiment, first test practical spread-aware minimum FVG width, cost/margin-aware sizing, and clarify whether the intended FVG may form during the H1 sweep rather than only after its close. These change the present raw rules and have NOT been applied or tested here.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(12,8),gridspec_kw={'height_ratios':[2,1]},layout='constrained')
    for tf,color in ((1,'#df6060'),(5,'#26a981'),(15,'#4b8ed9')):
        values=[10000];dates=[datetime.fromisoformat('2021-09-05')]
        for trade in ledgers[tf]:
            values.append(values[-1]+trade['net_profit']);dates.append(datetime.fromisoformat(trade['close_time']))
        dates.append(datetime.fromisoformat('2026-09-05'));values.append(values[-1])
        axes[0].step(dates,values,where='post',color=color,label=f'M{tf} FVG')
        rows=[r for r in results if r['entry_timeframe']==f'M{tf}']
        position={1:-.25,5:0,15:.25}[tf]
        axes[1].bar([i+position for i in range(4)],[r['return_pct'] for r in rows],width=.23,color=color,label=f'M{tf}')
    axes[0].set_title('XAU London H1 sweep + FVG: raw MT5 results, stop beyond FVG')
    axes[1].set_title('Each window restarts at $10,000; real-tick coverage: 100%, 67%, 22%, 13%',fontsize=10)
    axes[0].set_ylabel('Closed-trade balance ($)');axes[0].legend();axes[0].grid(alpha=.2)
    axes[1].set_xticks(range(4),list(raw.WINDOWS));axes[1].set_ylabel('Net return (%)');axes[1].axhline(0,color='#555',lw=.8);axes[1].grid(axis='y',alpha=.2)
    fig.savefig(ROOT/'raw-timeframe-comparison.png',dpi=150)
    plt.close(fig)

if __name__=='__main__':main()
