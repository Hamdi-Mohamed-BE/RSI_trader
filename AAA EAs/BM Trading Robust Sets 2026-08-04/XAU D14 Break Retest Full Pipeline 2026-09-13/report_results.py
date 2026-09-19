"""Render the frozen native evidence; never choose or change strategy parameters."""
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
import csv
import json

ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent/'D14 H1 M5 Break Retest Raw 2026-09-13'

def load(path):return json.loads(path.read_text())
def run(tag):return load(ROOT/'Runs'/f'{tag}.json')
def trades(tag):return load(ROOT/'Audit'/f'{tag}-trades.json')
def num(x):return f'{x:,.2f}' if x is not None else 'n/a'
def pct(x):return f'{x:+.2f}%'
def usd(x):return f'${x:,.2f}'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+
                     ['| '+' | '.join(str(c) for c in r)+' |' for r in rows])+'\n'
def performance(r):
    return [r['trades'],f"{r['net_win_rate']:.2f}%",pct(r['return_pct']),usd(r['net_profit']),num(r['net_pf']),f"{r.get('dd_pct',r.get('max_equity_dd_pct')):.2f}%"]
def csvsave(path,rows,keys=None):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=keys or list(rows[0]),extrasaction='ignore');writer.writeheader();writer.writerows(rows)
def period_ledger(ts,window):
    grouped=defaultdict(list)
    for t in ts:grouped[t['close_time'][:7]].append(t)
    start=datetime.strptime(window[0],'%Y.%m.%d');end=datetime.strptime(window[1],'%Y.%m.%d')
    year,month=start.year,start.month;balance=10000.;rows=[]
    while (year,month)<=(end.year,end.month):
        key=f'{year:04d}-{month:02d}';items=grouped[key];net=sum(t['net_profit'] for t in items)
        before=balance;balance+=net
        rows.append({'month':key,'trades_closed':len(items),'wins':sum(t['net_profit']>0 for t in items),
                     'net_usd':round(net,2),'commission_usd':round(sum(t['commission'] for t in items),2),
                     'swap_usd':round(sum(t['swap'] for t in items),2),'opening_balance':round(before,2),
                     'closing_balance':round(balance,2),'return_on_opening_balance_pct':100*net/before,
                     'partial_calendar_month':key in (start.strftime('%Y-%m'),end.strftime('%Y-%m'))})
        month+=1
        if month==13:month=1;year+=1
    return rows

def main():
    a=load(ROOT/'audit-results.json');f=a['final_runs'];selection=a['frozen_selection']['selected'];c=selection['config']
    verified=load(ROOT/'logic-verification.json');allruns=[load(p) for p in (ROOT/'Runs').glob('*.json')]
    assert len(verified)==len(allruns) and all(v['passed'] for v in verified),'Complete independent audit required'
    raw={r['period']:r for r in load(RAW/'results.json')['rows'] if r['symbol_requested']=='XAUUSD'}
    picked={key:run(f[key]) for key in ('6m','1y','3y','5y')};ts=trades(f['5y'])
    for t in ts:
        # The native XAU contract audit reports 100 oz/lot on this feed.
        t['planned_risk_pct']=100*t['planned_risk_cash']/t['equity_at_signal']
        t['initial_fill_risk_usd']=abs(t['open_price']-t['initial_stop'])*100*t['volume']
        t['net_R_on_initial_fill_risk']=t['net_profit']/t['initial_fill_risk_usd'] if t['initial_fill_risk_usd'] else None
    monthly=period_ledger(ts,picked['5y']['window'])
    csvsave(ROOT/'selected-5y-trades.csv',ts)
    csvsave(ROOT/'selected-5y-monthly.csv',monthly)
    ranking=sorted(allruns,key=lambda r:(r['stage'],r['window'],r['score']),reverse=True)
    csvsave(ROOT/'all-native-runs.csv',[{k:r[k] for k in ('tag','stage','config_id','window','model','delay_ms','trades','return_pct','net_pf','net_win_rate','dd_pct','commission','swap','score')} for r in ranking])
    lines=['# XAU D14 / H1 / M5 break and retest — full optimization results','',
           f"Verdict: **{a['verdict'].replace('_',' ')}**.",'',
           'This is a bounded, staged parameter search, not proof of a globally best strategy. XAUUSD only. US100, the live portfolio, installers and website remain unchanged. All money below is simulated, not earned income.','',
           f"Completed {a['native_run_count']} native MT5 runs; {a['unique_parameter_configs']} distinct parameter settings and {a['conservative_tested_configurations_including_delays']} setting/delay combinations counted for conservative multiple-testing adjustment. All {len(verified)} native signal/accounting audits passed; 14 independent unit tests passed; raw-default parity reproduced all seven recent raw trades, fills and costs exactly.",'',
           '## Selected configuration','',
           'Selected using development and validation only, then frozen before evaluating its final-year outcome. This is the best finalist under the predeclared score, not necessarily the highest-return or highest-win-rate configuration in every period.','',
           table(['Setting','Selected value'],[
               ['Direction',{0:'Both directions',1:'Long only',-1:'Short only'}[c['InpDirection']]],
               ['Daily filter','Last 14 completed D1 candles; compare older/newer seven-bar high-low ranges; mixed direction = no entry'],
               ['H1 structure',f"Strict swing with {c['InpH1Pivot']} completed bars on each side; break after the intervening opposite swing"],
               ['H1 zone','Entire broken origin candle' if c['InpZoneMode'] else 'Broken origin candle wick'],
               ['M5 holding',f"At least two rejection wicks in {c['InpHoldBars']} consecutive completed bars; "+('entire body outside zone' if c['InpWickMode']==0 else 'close outside zone')],
               ['M5 entry',f"Confirmed {c['InpM5Pivot']}-bar-each-side swing, higher low/lower high and closing break; entry on next available tick"],
               ['Stop',f"Last M5 swing + one tick + {c['InpStopBufferATR']:g} x closed M5 ATR(14), beyond the swing"],
               ['Take profit',f"{c['InpTargetR']:g}R reward for 1R risk, before trading costs"],
               ['Trailing / BE',{0:'Off',1:'Break-even at 1R',2:'1R-distance trail after 1.5R',3:'Confirmed M5 structural trail after 1R'}[c['InpManagement']]],
               ['Time exit',f"{c['InpMaxHoldHours']} elapsed hours; checked once per M5 bar on an available tick" if c['InpMaxHoldHours'] else 'Off'],
               ['Maximum zone age',f"{c['InpMaxZoneHours']} hours" if c['InpMaxZoneHours'] else 'No extra age limit; normal structural invalidation remains'],
               ['Entry session',f"{c['InpSessionStart']:02d}:00–{c['InpSessionEnd']:02d}:00 broker time"],
               ['Sizing','1% of current equity target; round UP to broker lot step / minimum lot; one position, no martingale'],
           ]),
           '## Raw versus selected — same starting capital and windows','',
           'Each window starts independently at $10,000. Returns and PF include recorded commission and swap; spread is embedded in native fills. DD is maximum relative floating-equity drawdown, not just closed-balance DD.','',
           table(['Window','Version','Trades','Net win rate','Net return','Net USD','Net PF','Equity DD'],
                 [row for p in picked for row in ([p,'Raw',*performance(raw[p])],[p,'Selected',*performance(picked[p])])]),
           '## Evidence separation','',
           table(['Role','From / to exclusive','Trades','Net win rate','Net return','Net USD','Net PF','Equity DD'],
                 [[label,' / '.join(r['window']),*performance(r)] for label,r in [('Development',run(selection['train'])),('Selection validation',run(selection['validation'])),('Search-excluded final year',picked['1y'])]]),
           'The original raw results in the final year were already inspected before this search. It was excluded from parameter selection, but it is NOT a genuinely unseen prospective holdout. The overlapping 3y/5y totals also include development/selection data; they must not be presented as out-of-sample results.','',
           '## Fees, losses and trade duration','',
           table(['Window','Commission','Swap','Average win','Average loss','Worst trade','Longest losing streak','Average hold'],
                 [[p,usd(r['commission']),usd(r['swap']),usd(r['average_win']),usd(r['average_loss']),usd(r['largest_loss']),r['max_loss_streak'],f"{r['mean_holding_minutes']/60:.2f}h"] for p,r in picked.items()]),
           f"Five-year planned stop-risk range after lot rounding: {min(t['planned_risk_pct'] for t in ts):.3f}%–{max(t['planned_risk_pct'] for t in ts):.3f}% of pre-entry equity. That target excludes commission and gap/slippage losses. Entry and exit costs are included in the reported net outcomes. Fees/swaps are what this MT5 test charged under its loaded broker specifications; historical fee-rate changes were not independently reconstructed.",'',
           f"Longest observed holding time: {max(t['holding_minutes'] for t in ts)/60:.2f} hours. The six-hour time exit is checked on available M5-bar ticks and cannot guarantee an exit while the market is closed. It is not a six-hour hard wall-clock holding cap.",'',
           '## Lower-risk and execution-delay controls','',
           table(['Control','Trades','Net win rate','Net return','Net USD','Net PF','Equity DD'],
                 [[label,*performance(run(f[key]))] for key,label in [('safe-1y','0.5% risk — 1y'),('safe-5y','0.5% risk — 5y'),('delay-500','500ms execution delay — 1y'),('delay-2000','2000ms execution delay — 1y')]]),
           'These are native reruns. Lower-risk control retains broker round-up/minimum-lot behavior, so it need not halve results exactly. Delay is fixed, not a claim to simulate every real news/slippage/connection condition.','',
           f"Management-screen activity: {sum(r['trail_updates'] for r in allruns if r['stage']=='management')} successful trailing/BE updates and {sum(r['time_exits'] for r in allruns if r['stage']=='management')} time exits across repeated management tests. Both leading exit configurations had 1R hard targets; their 1R/1.5R management triggers produced no trailing updates before take profit. Thus those no-op trials do not establish that trailing improves the strategy, nor provide native branch coverage for active trailing. The selected variant does not use trailing.",'',
           '## Additional cost stress','',
           table(['Window','Base net USD','Stressed net USD','Stressed return','Stressed PF','Extra spread','Extra commission','Extra swap'],
                 [[p,usd(s['base_net']),usd(s['net']),pct(s['return_pct']),num(s['pf']),usd(s['extra_spread_total']),usd(s['extra_commission_total']),usd(s['extra_swap_total'])] for p,s in a['cost_stress'].items()]),
           'This sensitivity keeps realized trades, prices and lots fixed, then subtracts one more measured entry spread, 50% more recorded negative commission and another recorded negative swap. It is not a fresh execution simulation and does not model changed signals or margin.','',
           '## Restricted-family walk-forward','',
           table(['Prior training','Following test','Trades','Net return','Net PF','Equity DD'],
                 [[' / '.join(w['train']),' / '.join(w['test']),w['trades'],pct(w['return_pct']),num(w['pf']),f"{w['dd_pct']:.2f}%"] for w in a['walk_forward']['folds']]),
           f"Profitable folds: {a['walk_forward']['profitable_folds']}/{a['walk_forward']['total_folds']}. Normalized compounded realized return: {pct(a['walk_forward']['normalized_compound_return_pct'])}. Each native fold starts at $10,000. The normalized stitch is not a separately rerun continuous MT5 account.",'',
           'This tests a smaller, eight-anchor structural family fixed before the search. Each fold selects only from its own previous two years. It does NOT represent full reoptimization of every exit/filter in each fold.','',
           '## Local parameter stability','',
           f"{a['positive_neighbours_pct']:.1f}% of eight one-parameter neighbours were profitable in the selection-validation year; minimum required was 60%. No winner was reselected from these neighbours.",'',
           table(['Changed setting','Trades','Net USD','Net PF','Equity DD'],
                 [[', '.join(f'{k}={v}' for k,v in n['config'].items() if c[k]!=v),n['trades'],usd(n['net']),num(n['pf']),f"{n['dd_pct']:.2f}%"] for n in a['neighbours']]),
           '## 10,000-path uncertainty checks','',
           table(['Window / costs','Return P5','Return median','Return P95','DD P95','PF P5','Positive paths'],
                 [[p,pct(b['return_p05_pct']),pct(b['return_p50_pct']),pct(b['return_p95_pct']),f"{b['max_drawdown_p95_pct']:.2f}%",num(b['profit_factor_p05']),f"{b['probability_profit_pct']:.2f}%"] for p,b in a['bootstrap_full_calendar'].items()]),
           'Conditional five-calendar-day circular block resampling includes inactive days over the full window. PF is resampled separately in five-trade blocks. Drawdown is CLOSED P&L only, not floating-equity DD. These are sensitivity distributions conditional on historical trades, NOT probabilities of future profitability, guaranteed income or FTMO challenge passes.','',
           table(['Window','Win-rate Wilson 95% range','Approx. deflated Sharpe diagnostic','Recent-half PF'],
                 [[p,'–'.join(f'{x:.2f}%' for x in s['metrics']['win_rate_wilson_95_pct']),f"{s['metrics']['deflated_sharpe_pct']:.2f}%",num(s['metrics']['recent_half_profit_factor'])] for p,s in a['common_audit_summaries'].items()]),
           'The common multiple-testing Sharpe adjustment is a heuristic with an assumed trial dispersion, not a calibrated probability; the tested parameters are correlated. The primary bootstrap above includes full calendar boundaries; the older common audit starts/ends at the first/last trade.','',
           '## Frozen acceptance gates','',
           table(['Gate','Result'],[[k.replace('_',' '),'PASS' if v else 'FAIL'] for k,v in a['promotion_gates'].items()]),
           'Common audit failures: '+(', '.join(k for k,v in a['common_audit_summaries']['1y']['gates'].items() if not v) or 'none')+'.','',
           '## Calendar-year breakdown of the selected 5y run','',
           table(['Year','Closed trades','Net USD','Commission','Swap','Win rate','Net PF'],
                 [[y['period'],y['trades'],usd(y['net']),usd(y['commission']),usd(y['swap']),f"{y['win_rate']:.2f}%",num(y['pf'])] for y in a['calendar_breakdown_5y']['years']]),
           '2021 and 2026 are partial years. All 61 touched calendar months, including zero-trade months, are in selected-5y-monthly.csv; the first/last month is partial. Monthly USD is simulated realized account profit, not payout income.','',
           '## Data coverage and implementation audit','',
           table(['Window','From / to exclusive','MT5 reported history quality','Native execution errors'],
                 [[p,' / '.join(r['window']),r['history_quality'],len(r['errors'])] for p,r in picked.items()]),
           'Real ticks on this feed begin 2026-01-01. Earlier history uses generated ticks even though model 4 was requested. Preliminary search used native one-minute OHLC; finalists and published windows were rerun in model 4. No claim of five complete years of real ticks is made. All windows end at 2026-09-05 exclusive; September 5–13 is not tested here.','',
           'Independent audits check completed D1/H1/M5 candles, right-side pivot confirmation, zone boundaries/invalidation, wick conditions, stop/target arithmetic, one attempt per zone, nonoverlapping positions, ratcheting stops and time exits when used, and reconciliation of trade P&L/commission/swap with native reports. Passing these checks reduces known implementation risk but cannot prove absence of every bug.','',
           'Rejected/error details for the published windows: '+json.dumps({p:dict(Counter(x['detail'] for x in r['errors'])) for p,r in picked.items()})+'. Overlapping windows repeat the same rejected event; these counts must not be added as separate real incidents. A native market-closed rejection describes tester behavior under the loaded sessions, not independently verified historical session availability.','',
           '## Saved evidence','',
           '- PLAN.md: predeclared scope, score, search and acceptance gates.\n- frozen-selection.json: parameter freeze and all five finalists.\n- Backtest Reports/: native MT5 reports and equity graphs.\n- Audit/: event records, native journals and per-trade JSON.\n- selected-5y-trades.csv: every trade, stop, target, commission, swap, net P&L and initial-risk R.\n- selected-5y-monthly.csv: calendar months including inactive months.\n- all-native-runs.csv: every test, including losing/rejected variants.\n- audit-results.json and Enhanced Audit/: uncertainty and stress evidence.\n- Sets/SELECTED RESEARCH ONLY - XAU D14 Break Retest.set: frozen settings.\n- EA/: tester-only source and compiled EA; refuses live initialization.','',
           f"EA source SHA-256: `{a['source_sha256']}`.",'',
           'Method references: [MT5 testing reports](https://www.metatrader5.com/en/terminal/help/algotrading/testing_report) and [MT5 tick generation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).','']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'verdict':a['verdict'],'selected':c,'results':{p:{k:r[k] for k in ('trades','net_win_rate','return_pct','net_profit','net_pf','dd_pct')} for p,r in picked.items()}},indent=2))

if __name__=='__main__':main()
