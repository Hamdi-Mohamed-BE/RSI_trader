"""Render an evidence-backed Bitcoin review; no tuning or further native runs."""
from pathlib import Path
import json,zipfile,hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
def table(rows):
    out='| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |\n'
    out+='|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        m=r['metrics'];label=r['window']+(' control' if r['control'] else ' strategy')
        out+=f"| {label} | {m['trades']} | {m['trades_per_month']:.2f} | {m['trades_per_eligible_day']:.3f} | {m['return_pct']:+.2f}% | {m['profit_factor']:.3f} | {m['win_rate_pct']:.1f}% | {m['equity_dd_pct']:.2f}% | {m['win_streak']}/{m['loss_streak']} | {m['mean_net_R']:.3f} |\n"
    return out

def chart(get):
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for ax,w in zip(axes,['5y','1y']):
        for control,color in [(False,'#217d69'),(True,'#a66b4c')]:
            r=get(w,control);d=pd.read_csv(Path(r['evidence_root'])/'trace.csv.gz')
            line=pd.Series(d.equity.to_numpy(),index=pd.to_datetime(d.time,unit='s',utc=True)).resample('1h').last().dropna()
            ax.plot(line.index,100*(line/10000-1),label='Random-direction control' if control else 'Shock reversal',color=color,lw=1.2)
        ax.set_title(('Five-year' if w=='5y' else 'Recent one-year')+' native confirmation',loc='left',weight='bold')
        ax.set_ylabel('Equity change (%)');ax.axhline(0,color='#777',lw=.7);ax.grid(axis='y',alpha=.15)
        ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False)
    fig.suptitle('Bitcoin shock reversal — unchanged raw rules',fontsize=16,weight='bold')
    fig.savefig(ROOT/'comparison.png',dpi=160);plt.close(fig)

def main():
    results=json.loads((ROOT/'RESULTS.json').read_text());rows=results['runs']
    gate=json.loads((ROOT/'GATE.json').read_text());v=json.loads((ROOT/'VERIFICATION.json').read_text());assert v['passed']
    carries=json.loads((ROOT/'CARRYOVER_AUDIT.json').read_text())['positions']
    get=lambda w,c=False,model=4:next(r for r in rows if (r['window'],r['control'],r['model'])==(w,c,model))
    fm=get('5y')['metrics'];tm=get('3y')['metrics'];recent=get('1y')['metrics']
    failed=gate['status']=='RAW_GATE_REJECTED'
    chart(get)
    txt='# Bitcoin shock reversal — pipeline review\n\n'
    txt+=('**Decision: rejected at the raw qualification gate. No optimized or live-ready winner.**' if failed else '**Raw qualification passed; optimization awaits review. This is not live readiness.**')+' Gold and Nasdaq are unchanged. GBPUSD has not been advanced.\n\n'
    txt+=f"Unchanged Bitcoin rules produced **{fm['return_pct']:+.2f}% over five years**, PF **{fm['profit_factor']:.3f}**, native equity drawdown **{fm['equity_dd_pct']:.2f}%**. Three years returned **{tm['return_pct']:+.2f}%**, PF **{tm['profit_factor']:.3f}**. These are historical simulations on BTCUSD CFDs, not forecasts or exchange-spot returns.\n\n"
    txt+='## Confirmed results\n\nNative MT5 Model 4, Exness BTCUSD CFD; USD 10,000 initial equity, nominal 1% equity risk rounded UP, 150ms simulated delay, broker-model spread and recorded fees. Four new 3y/5y raw/control confirmations; original 6m/1y evidence reused without alteration. All windows end September 27, 2026 exclusive.\n\n'
    txt+=table([get(w) for w in ['5y','3y','1y','6m']])
    txt+='\nStart dates: 5y — 2021-09-27; 3y — 2023-09-27; 1y — 2025-09-27; 6m — 2026-03-27. Windows overlap and have previously been seen; they are not independent or untouched holdouts. /month uses elapsed days / 30.4375. /day uses quoted dates with 07–16 UTC entry bars, **including weekends**. Streaks use net position P&L. Native floating-equity DD is distinct from closed-balance DD.\n\n'
    txt+='## Why the gate stopped\n\n' if failed else '## Qualification\n\n'
    txt+=''.join('- '+reason.replace('below1.15','below 1.15')+'.\n' for reason in gate['failures']) if failed else 'All frozen raw thresholds passed.\n'
    txt+='\nRequired: positive 3y and 5y, PF ≥ 1.15 in each, at least 30 trades, beat the matched control in mean net R, valid execution; positive 1y for a current shortlist. Thresholds were frozen before these new runs. No threshold was relaxed to turn a near-miss into a pass. The conclusion applies to this specific implementation, not all Bitcoin mean-reversion strategies.\n\n'
    txt+='## Matched random-direction control\n\nThe control keeps qualifying opportunities, clock, stop/target distances and sizing rules, but assigns direction using frozen seed 290929. This compares directional information conditional on the selected opportunities; it does not test random entry times or random levels. One seed is not a statistical significance test. Compare mean net R because compounded cash paths differ.\n\n'
    txt+=table([get(w,True) for w in ['5y','3y','1y','6m']])+'\n'
    for pair in results['matched_controls']:
        if pair['raw_tag'].endswith(('3y-m4','5y-m4')):
            txt+=f"- {pair['raw_tag']}: {pair['matched_trades']} matched dates; complete matching: {pair['all_dates_matched']}; mean paired net-R advantage {pair['mean_net_R_delta']:+.4f}R.\n"
    txt+=f"\n![Bitcoin native comparison](<{(ROOT/'comparison.png').as_posix()}>)\n\nLines are hourly samples of minute-recorded floating equity, not buy-and-hold Bitcoin prices. Table drawdowns use full native tester equity statistics.\n\n"
    txt+='## Earlier screen retained\n\nThe earlier +3.70% headline was the 5y one-minute-OHLC Model 1 screen. These rows are retained original tests, not newly optimized variants. Model 4 uses a different intrabar execution path.\n\n'
    txt+=table([get(w,c,1) for w in ['5y','3y'] for c in [False,True]])+'\n'
    txt+='## Exact unchanged hypothesis\n\nA completed H1 candle body must be at least 2 × ATR14 measured before that shock. The next completed candle reverses body direction, but closes on the shock side of EMA20. Trade opposite the shock at the next hour. Stop: 1.5 × ATR14; target: 1.5R; one attempt/day; entries 07–16 UTC including weekends; exit after six hours, 20:00 UTC, or before a known session close. The clip did not specify these parameters: they are the original research implementation, not a replication claim. No breakeven, trailing, loss escalation or averaging.\n\n'
    txt+='## Execution and costs\n\n'
    for w in ['5y','3y','1y','6m']:
        r=get(w);m=r['metrics'];flags={k:value for k,value in r['flags'].items() if value}
        txt+=f"- {w}: execution/carry flags {flags or 'none'}; longest hold {m['max_hold_hours']:.2f}h; initial stop risk median {m['median_initial_risk_pct']:.3f}%, maximum {m['max_initial_risk_pct']:.3f}%; closed-balance DD {m['balance_dd_pct']:.2f}%, native equity DD {m['equity_dd_pct']:.2f}%.\n"
    cost=get('5y')['costs']
    txt+=f"\nFive-year gross trade P&L ${cost['gross_profit']:+.2f}; commission ${cost['commission']:+.2f}; swap ${cost['swap']:+.2f}; fees ${cost['fee']:+.2f}; net ${cost['net_profit']:+.2f}. Spread is embedded in bid/ask fills, not separately deducted again.\n\n"
    selectedcarry=[x for x in carries if x['tag']==get('5y')['tag']]
    txt+=f"Five-year raw timed-exit audit: {len(selectedcarry)} delayed/cross-date positions. Diagnostics use6h/20UTC plus a two-minute tolerance; the session rule can require an earlier exit. All positions remain in the results. Minute-trace gaps can show missing modeled quote activity, not its exact historical cause or available live fills. The session API provides weekday sessions, not a full dated holiday calendar. [Official session API](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade).\n\n"
    txt+='## Historical data limits\n\n'
    for w in ['5y','3y','1y','6m']:
        r=get(w);txt+=f"- {w} native history label: {r['metrics']['history_quality']}.\n"
    cover=sorted(set(line.split('Ticks')[-1].strip() if 'Ticks' in line else line for r in rows if r['model']==4 for line in r['tick_coverage']))
    dates=sorted(set(__import__('re').findall(r'real ticks begin from (\d{4}\.\d{2}\.\d{2})','\n'.join(cover))))
    txt+='\nBroker journals report recorded real ticks beginning '+(', '.join(dates) if dates else 'at a date not parsed; consult archived journals')+'. Model4 is therefore not automatically all-real-tick history. MT5 can generate ticks where minute bars exist without tick records. [Official real/generated tick documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation). History labels include90-day warmup. Simulated150ms delay and the broker fee model are not measured live slippage or an independently verified historical fee series.\n\n'
    txt+='## Verification and pipeline stop\n\n'
    txt+=f"- Original source, EX5, rules and configuration matched all original hashes; clean original compile/smoke evidence reused, no strategy recompile or edits.\n- Four fresh native runs and eight retained relevant runs audited. **{v['signal_checks']:,} executed-signal checks**, {v['fresh_signal_checks']:,} from fresh runs, passed the independent H1 oracle. Repeated signals across overlapping runs are not independent samples.\n- Native report/deal cash, fees, full close volumes, risk sizing, chronology, signal clock, control direction and date matching checked. This verifies executed signals, not every possible tick decision.\n"
    if failed:txt+='- Stage4 failed. Optimization, holdout selection, Monte Carlo, additional-cost stress, FTMO simulation, portfolio integration and deployment were **not run**. No research exception is assumed from Nasdaq’s earlier exception.\n'
    else:txt+='- Stage4 passed. Stage5 search and all later gates remain uncompleted and require the recorded review/authorization.\n'
    txt+='- No live orders, normal terminal restart, Ava connection, production SET, installer, website or Git push. Stop for review before GBPUSD.\n\n'
    txt+='Files: PROTOCOL.md, RESULTS.json, GATE.json, VERIFICATION.json, CARRYOVER_AUDIT.json, PROVENANCE.json and native/. RESULTS.json includes monthly closed-P&L breakdowns and links to reused evidence. The review ZIP excludes private connection INIs and raw identity-bearing reports/journals.\n'
    (ROOT/'REPORT.md').write_text(txt,encoding='utf-8')
    package=ROOT/'Bitcoin-raw-pipeline-review.zip'
    allowed=['REPORT.md','PROTOCOL.md','RESULTS.json','GATE.json','VERIFICATION.json','CARRYOVER_AUDIT.json','PROVENANCE.json','BUILD.json','RULES.md','run-config.json','MarketStyles.mq5','MarketStyles.ex5','compile.log','comparison.png']
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for name in allowed:z.write(ROOT/name,name)
        for r in rows:
            folder=Path(r['evidence_root'])
            for name in ['run.json','trades.csv.gz','signals.csv.gz']:
                z.write(folder/name,'evidence/'+r['tag']+'/'+name)
    with zipfile.ZipFile(package) as z:assert z.testzip() is None and not any(n.lower().endswith('.ini') for n in z.namelist())
    (ROOT/'PACKAGE.json').write_text(json.dumps(dict(path=str(package),sha256=hashlib.sha256(package.read_bytes()).hexdigest(),private_connection_files_excluded=True),indent=2))
    print(json.dumps(dict(status=gate['status'],report=str(ROOT/'REPORT.md')),indent=2))

if __name__=='__main__':main()
