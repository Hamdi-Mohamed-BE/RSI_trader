"""Create review artifacts from completed, immutable native evidence only."""
import csv,gzip,io,json,shutil,zipfile
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import search as s

def load(name):return json.loads((s.OUT/name/'results.json').read_text())[0]
def table(items):
    lines=['| Version / period | Return | Net PF | Equity DD | Trades | / month | / weekday | Net win% | Max W / L streak |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label,r in items:
        m=r['net'];days=np.busday_count(r['start'].replace('.','-'),r['end'].replace('.','-'))
        lines.append(f"| {label} | {m['return_pct']:+.2f}% | {m['profit_factor']:.2f} | {m['equity_dd_pct']:.2f}% | {m['trades']} | {m['trades_per_month']:.2f} | {m['trades']/days:.3f} | {m['win_rate_pct']:.2f}% | {m['max_win_streak']} / {m['max_loss_streak']} |")
    return '\n'.join(lines)

def main():
    verdict=json.loads((s.ROOT/'VERDICT.json').read_text());assert verdict['status']=='REJECTED_RECENT_CONFIRMATION'
    final=json.loads((s.ROOT/'FROZEN FINAL.json').read_text());dev=json.loads((s.ROOT/'DEVELOPMENT FINALISTS.json').read_text())
    val=[load('validation-repair1-'+str(i)) for i in range(3)];recent=load('recent-frozen');baseval=load('baseline-validation');base=load('parity')
    rows=[r for p in s.OUT.glob('*/results.json') for r in json.loads(p.read_text())];screens=[r for r in rows if r['model']==1]
    count=dict(native_passes=len(rows),screening_passes=len(screens),unique_parameters=len({r['parameters_sha'] for r in rows}),
               prior_raw_screen_passes=64,with_prior_raw=len(rows)+64,execution_flagged=sum(not r['clean'] for r in rows))
    s.save(s.ROOT/'TRIAL ACCOUNTING.json',count)
    bledger=s.read_trades('parity');cledger=s.read_trades('recent-frozen')
    small_losses=sum(-5<t['net_profit']<0 for t in cledger)
    recent_cost=dict(commission=sum(t['commission'] for t in cledger),swap=sum(t['swap'] for t in cledger),fees=sum(t['fee'] for t in cledger),
                     tiny_negative_positions_under_5_dollars=small_losses)
    s.save(s.ROOT/'RECENT COST ACCOUNTING.json',recent_cost)
    # Display hourly samples of the recorded minute-equity traces. Report DD is full native tick-equity DD.
    fig,axes=plt.subplots(2,1,figsize=(12,8),gridspec_kw={'height_ratios':[2.2,1]},layout='constrained')
    for name,label,color in [('parity','Original Gold bot','#16745b'),('recent-frozen','Selected optimization — rejected','#c54446')]:
        d=pd.read_csv(s.OUT/name/'0-trace.csv.gz');d['date']=pd.to_datetime(d.time,unit='s',utc=True)
        a=d.set_index('date')['equity'].resample('1h').last().dropna();axes[0].plot(a.index,(a/10000-1)*100,label=label,color=color,lw=1.5)
    axes[0].axhline(0,color='#8393a1',lw=.7);axes[0].set_ylabel('Equity change (%)');axes[0].legend(frameon=False,loc='upper left');axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    axes[0].set_title('Gold: the selected optimization failed the reserved-year check',loc='left',fontsize=16,pad=14)
    x=np.arange(2);w=.34
    axes[1].bar(x-w/2,[baseval['net']['return_pct'],base['net']['return_pct']],w,label='Original',color='#16745b')
    axes[1].bar(x+w/2,[final['net']['return_pct'],recent['net']['return_pct']],w,label='Selected',color='#c54446')
    for xx,value in zip(list(x-w/2)+list(x+w/2),[baseval['net']['return_pct'],base['net']['return_pct'],final['net']['return_pct'],recent['net']['return_pct']]):
        axes[1].annotate(f'{value:+.2f}%',(xx,value),xytext=(0,5 if value>=0 else -14),textcoords='offset points',ha='center',fontsize=11)
    axes[1].set_xticks(x,['Validation: Mar 2024–Sep 2025','Reserved: Sep 2025–Sep 2026']);axes[1].set_ylabel('Net return (%)');axes[1].axhline(0,color='#8393a1',lw=.7);axes[1].set_ylim(-5,12)
    for a in axes:a.spines[['top','right']].set_visible(False);a.grid(axis='y',alpha=.18);a.set_axisbelow(True)
    fig.text(.01,-.025,'Same $10,000 starting balance per period. Historical Exness CFD simulation; recorded ticks only from Jan 2026. No live deployment.',fontsize=9,color='#54616f')
    fig.savefig(s.ROOT/'comparison.png',dpi=160,bbox_inches='tight');plt.close(fig)
    stages=json.loads((s.ROOT/'STAGES.json').read_text());plateaus=json.loads((s.ROOT/'PLATEAUS.json').read_text());verification=json.loads((s.ROOT/'VERIFICATION.json').read_text())
    text=f'''# Gold volatility-regime bot — review

## Decision

**No improved version survived. Keep the original as the benchmark; do not replace it with the optimized candidate.** This is not approval to trade the original live. Gold alone was tested; Nasdaq, Bitcoin and GBPUSD have not been started.

The selected candidate passed development, the parameter-neighbourhood check and the 18-month validation. It then lost money and had worse drawdown than the original over the reserved latest year. The pipeline correctly stops at **REJECTED_RECENT_CONFIRMATION**. No attempt was made to rescue it by tuning that year.

## Like-for-like native results

Each run starts with $10,000 USD; target risk is 1% equity, rounded UP to the broker's lot step. Model 4 uses recorded ticks where available and generated ticks otherwise. Return is cumulative, not annualized; DD is native floating-equity drawdown. PF and win rate use net position P&L including fees and swap, so may differ from the platform's gross-trade win count. Frequency per weekday uses Monday–Friday calendar days, including holidays; it is not trades per active trading day.

{table([('Original — validation',baseval),('Selected A — validation',final),('Original — reserved year',base),('Selected A — reserved year',recent)])}

Validation: **2024-03-27 to 2025-09-27 exclusive**. Reserved year: **2025-09-27 to 2026-09-27 exclusive**. The candidate underperformed the original's cash return even in validation; its slight PF advantage was not an improvement that held up afterward.

![Gold comparison]({(s.ROOT/'comparison.png').as_posix()})

The chart samples the recorded equity trace hourly for legibility. Table drawdowns come from the full native tester, not the downsampled chart.

## Three finalists, not three proven edges

Development: 2021-09-27 to 2024-03-27 exclusive. These are **Model 1 one-minute OHLC screening results**, selected after searching, not comparable evidence quality to the Model 4 validation above.

{table([(f'Candidate {chr(65+i)} — development',r) for i,r in enumerate(dev)])}

Native Model 4 validation of all three, with the same threshold fixed in advance: at least30 positions, positive return, PF>=1.15 and clean execution.

{table([(f'Candidate {chr(65+i)} — validation',r) for i,r in enumerate(val)])}

- A passed validation and was frozen before the latest-year test. Latest year: PF0.80, negative return, and one rejected stop modification. It fails on performance independently of that execution flag.
- B and C failed validation (PF1.06). They were not tried on the reserved year. Their no-elapsed-time and16-hour holds produced identical development/validation results because the daily flat rule dominated here; they are not independent corroboration.
- All three neighbourhoods passed the coarse plateau screen; that did **not** imply they would generalize. A's27 neighbours were100% profitable in development, medianPF{plateaus[0]['median_pf']:.2f}, yet A still failed later.

## Selected candidate A — exact interpretation

- H1 completed candles; ATR14/ATR100 Hot threshold1.2;252-transition history,20 Hot observations minimum, Laplace smoothing, persistence threshold0.65; the newest transition is excluded.
- EMA50 direction/slope over5 bars and previous-bar breakout, with completed-H4 EMA50 direction agreement.
- Buy/sell stop0.5ATR beyond the observed executable quote; pending lifetime4 signal bars, bounded by the daily flat time. Both directions, weekday entry07:00–16:59 UTC.
- Fixed **$10 price-distance stop** (not $10 account risk), target2.5R. Move the stop to entry at0.5R favorable movement. A breakeven stop does not guarantee zero net P&L because of execution and costs.
- One position, normally one attempt/day, one additional qualifying attempt after a losing-price SL;8-hour maximum holding or20:00UTC /5minutes before broker session close. The retry implementation checks negative DEAL_PROFIT on an SL; it is not a universal after-fees-loss trigger.
- 1% target risk; observed maximum initial fill-to-stop risk was{recent['net']['max_actual_risk_pct']:.3f}% in the reserved year. Original maximum on that year was{base['net']['max_actual_risk_pct']:.3f}%. These are stop-distance estimates, not a guarantee on realized loss.

Execution exception: **2026-06-10 12:29:52**, one breakeven-stop modification returned `Invalid stops`. The rejected request is preserved in the native journal. No post-result code or parameter change was used to improve the reported return. Net-cost totals and small-loss counts are in `RECENT COST ACCOUNTING.json`; the18-loss maximum streak includes small negative trades, not18 full1R losses.

## Coverage and audit

- {count['native_passes']} native passes archived, including {count['screening_passes']} development/plateau screen passes; {count['unique_parameters']} unique parameter vectors. Repeats and retired trials remain counted. Including the earlier64-run raw screen gives{count['with_prior_raw']} observed passes for any later multiplicity accounting. Counts are not independent experiments.
- Seven timeframes; market/confirmation/pending entries; ATR, percentage, fixed-price and structural stops; BE/trailing/partial/time/RR exits; sessions; direction; filters; trade management; regime parameters; joint neighbourhoods. Search is staged with a top-three beam, **not** an exhaustive global optimum.
- Every completed pass reconciles native report cash to its position ledger. Verified{verification['native_positions']:,} position rows across{verification['native_case_ledgers']} archived passes;{verification['execution_rejected_cases']} passes had execution flags and were not treated as clean candidates.
- Zero-error, zero-warning final compilation. The initial warning-only build was corrected and archived before any test.
- Exact original/new-engine parity on44 baseline trades: times, side, prices, volume, SL/TP and net P&L. Independent numerical checks passed216 past-only/symmetry windows and44 native baseline signal checks.
- The regime skill informed the causal-state checks. Its packaged runner was unavailable; this uses the disclosed ATR-state Markov filter, **not GARCH**, an HMM or proof that volatility clustering predicts direction.

### Important repair and selection bias

The first management search allowed two position slots with only one daily attempt and split the risk between them. That inactive second slot only cut risk in half. Those versions were retired. The management/regime search was restarted with a structural capacity rule: at least two daily attempts and actual observed overlap for a two-slot candidate. The original runs remain in `repair1-audit` and the all-pass ledger.

This was found before inspecting those early validation returns, although two early validation runs had executed automatically. They were retained; validation is therefore not represented as pristine. The latest year was also already seen for the raw baseline. This is retrospective screening, not untouched future-forward evidence. It is enough to reject this candidate, not enough to certify a survivor.

Exness-MT5Trial16 XAUUSD CFD, USD,1:2000 research leverage,150ms delay. Recorded real ticks start **2026-01-01**. The earlier validation used generated ticks; Model4 does not make missing historical ticks real. The recent report's49% real-tick coverage includes the180-day no-trade warmup. This is not an FTMO-native feed or proof of live fills.

## Where the pipeline stopped

Raw eligibility: passed earlier. Baseline parity: passed. Broad search: completed. Neighbourhoods: passed. Validation: onlyA passed. Reserved recent year: **failed**.

**Not advanced:** older2019–2021 holdout; new6m/3y/5y candidate confirmations; direction control on the selected candidate;10,000-path Monte Carlo; deflated Sharpe; additional-cost stress; FTMO scenarios; portfolio integration; forward/live deployment. Those gates cannot turn a failed reserved-period result into a validated strategy, and no readiness or probability claim is made. `finish.py` is a prepared, guarded continuation utility, not evidence that those tests ran.

Your original +33.11%/PF1.33/7.48% five-year result was the faster Model1 screen. Its prior Model4 confirmation was +33.06%/PF1.33/7.38%,209 trades. No five-year result is claimed for the selected optimized version because it failed earlier.

## Files and next action

`PROTOCOL.md` records dates, rules and the repair. `ALL NATIVE RESULTS.json` includes every completed pass, including retired ones. `DEVELOPMENT FINALISTS.json`, `PLATEAUS.json`, `FROZEN FINAL.json`, `PARITY.json`, `VERIFICATION.json` and `VERDICT.json` provide machine-readable evidence. Native source, binaries, inputs, compressed ledgers/reports and journals remain in the local native folders. The review ZIP excludes private tester connection files and raw account-identifying reports.

The original bot was not modified; no website, installer, portfolio or live account was changed. The candidate has a tester-only guard and remains rejected. **Stop here for the user's Gold review before any other asset.** The list still has four assets despite the wording “three”; confirm the remaining scope when continuing.

## Method references

MetaTrader documents that [missing real ticks are replaced by generated ticks](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation), and defines the [native testing modes](https://www.mql5.com/en/docs/runtime/testing). The reason to count all trials is the [Bailey–Lopez de Prado Deflated Sharpe research](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); that statistic was not run after this candidate failed its earlier gate.
'''
    (s.ROOT/'REPORT.md').write_text(text,encoding='utf-8');s.save(s.ROOT/'ALL NATIVE RESULTS.json',rows)
    # Preserve exact tested candidate and original, clearly labeled research-only.
    selected=s.OUT/'recent-frozen';package=s.ROOT/'Gold-review-research-only.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for name in ['REPORT.md','comparison.png','PROTOCOL.md','TRIAL ACCOUNTING.json','RECENT COST ACCOUNTING.json','ALL NATIVE RESULTS.json','DEVELOPMENT FINALISTS.json','PLATEAUS.json','FROZEN FINAL.json','PARITY.json','VERIFICATION.json','VERDICT.json','search.py','verify.py','report.py','finish.py']:
            z.write(s.ROOT/name,name)
        for p in selected.iterdir():
            if p.suffix in ['.mq5','.mqh','.ex5','.set'] or p.name=='manifest.json' or p.name.endswith(('-trades.csv.gz','-signals.csv.gz')):z.write(p,'REJECTED-candidate/'+p.name)
        for name in ['MarketStyles.mq5','MarketStyles.ex5','RULES.md']:z.write(s.RAW/name,'unchanged-original/'+name)
        for name in ['search.py','PROTOCOL.md','STAGES.json','SEARCH RESULTS.json','DEVELOPMENT FINALISTS.json','PLATEAUS.json']:
            p=s.ROOT/'repair1-audit'/name
            if p.exists():z.write(p,'retired-risk-comparison/'+name)
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None and not any(p.lower().endswith('.ini') for p in z.namelist())
    s.save(s.ROOT/'PACKAGE.json',dict(path=str(package),sha256=s.sha(package),files=len(zipfile.ZipFile(package).namelist()),no_private_tester_ini=True))
    print(json.dumps(dict(verdict=verdict['status'],counts=count,report=str(s.ROOT/'REPORT.md'),package=str(package)),indent=2))

if __name__=='__main__':main()
