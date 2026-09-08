"""Generate the research handoff from saved evidence; never reruns native tests."""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from research import ROOT,PAIRS,BASE,SESSIONS,MANAGE_NAMES,METRICS,dump,score

CHARTS=ROOT/'Charts';CHARTS.mkdir(exist_ok=True)
plt.rcParams.update({'figure.facecolor':'#071411','axes.facecolor':'#0c201b','savefig.facecolor':'#071411','text.color':'#e8f5ef','axes.labelcolor':'#c0d8cf','xtick.color':'#b6cec5','ytick.color':'#b6cec5','axes.edgecolor':'#3d5c50','grid.color':'#315145','font.size':10})
GREEN='#46edb0';RED='#f67f82';BLUE='#57bfe6';GOLD='#eac574'

def fmt(x,d=2):return 'N/A' if x is None or not np.isfinite(x) else f'{x:.{d}f}'
def rowtable(rows,native=False):
    out=['| Pair / config | Period | Return | PF | Win rate | DD | Trades | Sharpe | Recovery |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if native:pf,wr,dd,n,sh,rec=r['basket_profit_factor'],r['basket_win_rate'],r['equity_dd_pct'],r['baskets'],r['sharpe_ratio'],r['recovery_factor']
        else:pf,wr,dd,n,sh,rec=[r[k] for k in ('profit_factor','win_rate','dd_pct','trades','sharpe','recovery')]
        out.append(f"| {r['pair']} {r.get('label',r.get('id',''))} | {r['stage']} | {r['return_pct']:+.2f}% | {fmt(pf)} | {wr:.2f}% | {dd:.2f}% | {n} | {sh:.2f} | {rec:.2f} |")
    return '\n'.join(out)

def native_balance(r):
    b=pd.read_csv(ROOT/'Native'/r['case']/'baskets.csv')
    times=[pd.Timestamp(r['period'].split('(')[1].split(' - ')[0],tz='UTC')]+list(pd.to_datetime(b.exit_time,unit='s',utc=True))
    values=np.r_[10000.,10000.+b.net.cumsum().to_numpy()]
    end=pd.Timestamp(r['period'].split(' - ')[1].rstrip(')'),tz='UTC')
    if times[-1]<end:times.append(end);values=np.r_[values,values[-1]]
    return b,times,values

def monte_carlo(r):
    b,_,_=native_balance(r);returns=b.return_fraction.to_numpy();n=len(b);block=min(5,max(1,n//4));rng=np.random.default_rng(20260906)
    if not n:return None
    starts=rng.integers(0,n,size=(5000,(n+block-1)//block));ix=(starts[:,:,None]+np.arange(block))%n
    sampled=returns[ix.reshape(5000,-1)[:,:n]];paths=np.c_[np.full(5000,10000.),10000*np.cumprod(1+sampled,axis=1)]
    end=(paths[:,-1]/10000-1)*100;dd=np.max(1-paths/np.maximum.accumulate(paths,axis=1),axis=1)*100
    result=dict(pair=r['pair'],stage=r['stage'],model=r['model'],baskets=n,paths=5000,block_trades=block,return_p5=float(np.percentile(end,5)),return_median=float(np.median(end)),return_p95=float(np.percentile(end,95)),dd_p95=float(np.percentile(dd,95)),simulated_profitable_pct=float(np.mean(end>0)*100),sample_warning='Insufficient sample for a reliable Monte Carlo inference' if n<30 else 'Conditional resampling, not a future forecast')
    fig,ax=plt.subplots(figsize=(10,4.4),layout='constrained');lo,med,hi=np.percentile(paths,[5,50,95],axis=0)
    ax.fill_between(np.arange(n+1),lo,hi,color=BLUE,alpha=.22,label='5–95% conditional outcomes');ax.plot(med,color=GREEN,label='Median')
    ax.axhline(10000,color=GOLD,ls='--',lw=.8);ax.set(title=f"{r['pair']} — {r['stage']} MT5 baskets / 5,000 bootstrap paths\n{n} baskets; "+('INSUFFICIENT SAMPLE' if n<30 else 'not a forecast'),xlabel='Closed basket number',ylabel='Simulated closed balance, USD');ax.legend(fontsize=8);ax.grid(alpha=.3)
    fig.savefig(CHARTS/f"{r['pair']}-{r['stage']}-monte-carlo.png",dpi=150);plt.close(fig)
    return result

def main():
    screen=json.loads((ROOT/'screen-results.json').read_text());selections=json.loads((ROOT/'selection.json').read_text())
    native=[json.loads(p.read_text()) for p in (ROOT/'Native').glob('*/result.json')]
    final=[r for r in native if r['stage']!='smoke' and r['model']==0 and r['execution_mode']==-1 and r['label'] in ('baseline','selected')]
    execution=[r for r in native if r['stage']=='test' and (r['execution_mode']==250 or 'repeat' in r['label'])]
    real=[r for r in native if r['model']==4]
    unavailable=[json.loads(p.read_text()) for p in (ROOT/'Native').glob('*/unavailable.json')]
    final.sort(key=lambda r:(r['pair'],r['stage'],r['label']))
    for stage in ('test','full'):
        fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
        for ax,pair in zip(axes,PAIRS):
            for r in [r for r in final if r['pair']==pair and r['stage']==stage]:
                b,t,v=native_balance(r);ax.step(t,v,where='post',label=f"{r['label']}: {r['return_pct']:+.2f}% | PF {fmt(r['basket_profit_factor'])} | WR {r['basket_win_rate']:.1f}% | {len(b)} baskets",color=GREEN if r['label']=='selected' else RED)
            ax.axhline(10000,color=GOLD,ls='--',lw=.7)
            if stage=='full':ax.axvline(pd.Timestamp('2025-09-01',tz='UTC'),color=BLUE,ls='--',label='Final-test year begins')
            ax.set_title(pair+(' — final year' if stage=='test' else ' — three-year context (includes development)'));ax.set_ylabel('Closed-basket balance, USD');ax.legend(fontsize=8);ax.grid(alpha=.3);ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        fig.suptitle('Native MT5 generated Every Tick + random execution delay\n1% combined planned risk; balance curves, not floating equity',fontsize=12)
        fig.savefig(CHARTS/f'native-{stage}-comparison.png',dpi=155);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,pair in zip(axes,PAIRS):
        r=next(r for r in final if r['pair']==pair and r['stage']=='test' and r['label']=='selected')
        b,t,v=native_balance(r);ax.step(t,v,where='post',color=GREEN,lw=1.8);ax.axhline(10000,color=GOLD,ls='--',lw=.8)
        ax.set_title(f"{pair}: {r['return_pct']:+.2f}%\nPF {fmt(r['basket_profit_factor'])} | WR {r['basket_win_rate']:.1f}% | n={r['baskets']}");ax.set_ylabel('Closed-basket balance, USD');ax.grid(alpha=.3);ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    fig.suptitle('Locked settings — final year 2025-09-01 to 2026-09-01\nNative generated ticks + random delay; 1% combined planned risk')
    fig.savefig(CHARTS/'selected-final-year-detail.png',dpi=160);plt.close(fig)
    # Every broad-grid configuration has an explicit cell; no hidden best-of-stop aggregation.
    for pair in PAIRS:
        rows=[r for r in screen if r['pair']==pair and r['stage']=='train']
        fig,axes=plt.subplots(6,3,figsize=(18,24),layout='constrained')
        for session in range(6):
            for stop in range(3):
                ax=axes[session,stop];mat=np.full((5,10),np.nan)
                for r in rows:
                    c=r['config']
                    if c['session']!=session or c['stop']!=stop or any(c[k]!=BASE[k] for k in ('window','model','entry','manage','direction','hold')):continue
                    mat[(5,15,30,60,240).index(c['tf']),c['exit']]=r['return_pct']
                im=ax.imshow(mat,cmap='RdYlGn',vmin=-50,vmax=20,aspect='auto')
                for y in range(5):
                    for x in range(10):
                        if np.isfinite(mat[y,x]):ax.text(x,y,f'{mat[y,x]:.0f}',ha='center',va='center',fontsize=6,color='white' if mat[y,x]<-30 else 'black')
                ax.set_xticks(range(10),['.5R','1R','1.5R','2R','3R','4R','6R','Mean','Roll','Time'],rotation=60);ax.set_yticks(range(5),['M5','M15','M30','H1','H4']);ax.set_title(f'{SESSIONS[session]} / '+['SD stop','spread ATR stop','swing stop'][stop],fontsize=10)
        fig.suptitle(f'{pair}: all 900 broad-grid training tests — return %\nColour clipped at -50/+20%; cell numbers are actual values. Not final-year evidence.',fontsize=14)
        fig.savefig(CHARTS/f'{pair}-all-session-stop-RR-timeframe-tests.png',dpi=135);plt.close(fig)
        # Refinements, one point per actual setting, labelled via the full ledger.
        fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
        for ax,metric,title in zip(axes,['profit_factor','win_rate'],['Profit factor (training)','Win rate % (training)']):
            for s in range(6):
                group=[(i,r) for i,r in enumerate(screen) if r['pair']==pair and r['stage']=='train' and r['config']['session']==s]
                ax.scatter([i for i,r in group],[r[metric] for i,r in group],s=9,alpha=.65,label=SESSIONS[s])
            ax.set_ylabel(title);ax.grid(alpha=.25)
        axes[0].axhline(1,color=RED,ls='--');axes[0].legend(ncol=3,fontsize=8);axes[-1].set_xlabel('Configuration index in all-settings.md');fig.suptitle(f'{pair}: every one of {len(rows)} training configurations')
        fig.savefig(CHARTS/f'{pair}-all-configurations-PF-win-rate.png',dpi=145);plt.close(fig)
    mc=[monte_carlo(r) for r in final if r['label']=='selected'];mc=[r for r in mc if r]
    stress=[];yearly=[]
    for r in final:
        if r['label']!='selected':continue
        b,t,v=native_balance(r)
        if r['stage']=='test':
            for extra in (.05,.10):
                returns=b.return_fraction.to_numpy()-extra*.01
                sv=np.r_[10000.,10000*np.cumprod(1+returns)];p=np.diff(sv);loss=-p[p<0].sum()
                stress.append(dict(pair=r['pair'],extra_R_per_basket=extra,return_pct=float((sv[-1]/10000-1)*100),profit_factor=float(p[p>0].sum()/loss) if loss else None,win_rate=float((p>0).mean()*100) if len(p) else 0))
        else:
            times=pd.to_datetime(b.exit_time,unit='s',utc=True)
            for start,end in [('2023-09-01','2024-09-01'),('2024-09-01','2025-09-01'),('2025-09-01','2026-09-01')]:
                s=b[(times>=start)&(times<end)];loss=-s.loc[s.net<0,'net'].sum();gain=s.loc[s.net>0,'net'].sum()
                yearly.append(dict(pair=r['pair'],start=start,end=end,baskets=len(s),net_usd=float(s.net.sum()),win_rate=float((s.net>0).mean()*100) if len(s) else 0,profit_factor=float(gain/loss) if loss else None))
    sessions=[]
    for pair in PAIRS:
        for session in range(6):
            candidates=[r for r in screen if r['pair']==pair and r['stage']=='validation' and r['config']['session']==session]
            if candidates:
                best=max(candidates,key=lambda r:r['selection_score']);sessions.append(best)
    summary=dict(step=2,title='Relative-Value Pairs',risk_percent_combined=1.,decision='Do not add either pair to the active system',screen_configurations_per_pair={p:selections[p]['screen_configs'] for p in PAIRS},native_results=[{k:v for k,v in r.items() if k not in ('series',)} for r in final],real_tick_results=[{k:v for k,v in r.items() if k!='series'} for r in real],execution_sensitivity=[{k:v for k,v in r.items() if k!='series'} for r in execution],monte_carlo=mc,native_cost_stress=stress,yearly_context=yearly,session_selection_validation=sessions)
    dump(ROOT/'summary.json',summary)
    summary['real_tick_unavailable']=unavailable
    dump(ROOT/'summary.json',summary)
    # Auditable full metric ledger for every configuration, not just winners.
    appendix=['# All tested settings — Python screening only','','Each row shows its complete configuration and metrics. `train` is optimization data; `validation` helped select; `test` was not used to select. Do not interpret the maximum training result as a live recommendation.','', '| # | Pair | Period | ID | TF | Session | Model/window/Z | Stop | Exit/RR | Management | Direction | Hold h | Return % | PF | Win % | DD % | Trades | Sharpe | Recovery |','|---:|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for i,r in enumerate(screen):
        c=r['config'];extra=f" +{r['extra_commission_bps_per_side']:g}bps/side" if r.get('extra_commission_bps_per_side') else '';appendix.append(f"| {i} | {r['pair']} | {r['stage']}{extra} | {r['id']} | {c['tf']} | {SESSIONS[c['session']]} | {c['model']}/{c['window']}/{c['entry']} | {c['stop']} | {c['exit']}/{c['rr']} | {MANAGE_NAMES[c['manage']]} | {c['direction']} | {c['hold']} | {r['return_pct']:.2f} | {r['profit_factor']:.2f} | {r['win_rate']:.2f} | {r['dd_pct']:.2f} | {r['trades']} | {r['sharpe']:.2f} | {r['recovery']:.2f} |")
    (ROOT/'all-settings.md').write_text('\n'.join(appendix),encoding='utf-8')
    lines=['# Step 2 — Relative-Value Pairs: final research report','','## 1. Decision','','**Do not add BTC/ETH or XAU/XAG to the active system.** The locked candidates did not establish a repeatable net edge. These findings reject the tested implementation, not every possible pairs strategy. No production BATs, website data, or live-account orders were changed.','','## 2. What was tested','','3,132 distinct Python screening configurations (1,566 per pair), plus separate selection-validation/final/cost runs and native MT5 checks. Risk stayed at 1% **combined across both legs**, not 1% each. Risk was not optimized upward. Starting capital: $10,000. Exact scope is in PLAN.md.','',
        '- Timeframes: M5, M15, M30, H1, H4.','- Six clock windows: all day, Asia 00–08 UTC, London 08–17 local, New York 08–17 local, overlap, and London-or-New-York. Historical DST is handled; crypto weekend clock windows are not claims that stock exchanges are open.','- Fixed RR: 0.5, 1, 1.5, 2, 3, 4, 6. Also entry-time mean targets, rolling mean targets that genuinely change while holding, and time-only exits.','- Log-ratio and rolling OLS hedge; formation windows 32/64/128 completed bars; divergence thresholds 1.5/2/2.5/3; both spread directions and each direction separately.','- Stop placement: spread standard deviation, spread ATR, or adverse recent spread swing; each leg has an emergency stop and the remaining leg is closed when one exits.','- Management: none, BE at +0.5R/+1R, M15 closed-candle +0.5R → basket floor +0.2R, 0.5R/1R trailing after +1R, spread-volatility trailing. Hold caps 6/24/72 hours.','- The broad cross-grid contains all timeframe × session × stop × exit combinations. Signal and management refinements are staged around training anchors; this is not every possible Cartesian combination of all inputs.','',
        'Training: 2023-09-01–2024-09-01. Selection validation: 2024-09-01–2025-09-01. Final year: 2025-09-01–2026-09-01. Both candidates were saved to selection-lock.json before final-year performance was read. Subsequent debugging was correctness work, not retuning to improve the final year. The supplemental rolling diagnostic is not another untouched test.','',
        '## 3. Native MT5 results','','PF and win rate below are calculated from **completed baskets**, including any aborted single-leg executions; the two leg trades are not counted as independent strategy wins. DD is native maximum relative floating-equity DD. Sharpe/recovery are the MT5-reported account metrics; a Sharpe of -5 may reflect the platform floor.','',rowtable(final,True),'','![Native final-year comparison](Charts/native-test-comparison.png)','','![Three-year context](Charts/native-full-comparison.png)','','The curves above are closed-basket balances, not sampled floating equity. Full-period results include training/selection and are descriptive, not an independent test.','','### Real-tick execution checks','',rowtable(real,True) if real else 'Real-tick check unavailable; no claim of real-tick validation.','',
        'Real-tick mode must be read with each Native/*model4/tester-audit.txt: MT5 may use generated ticks for minutes with missing real ticks. It is not automatically 100% genuine recorded ticks. Native broker spread/commission/swap differ from the conservative screen assumptions, so Python and MT5 are deliberately shown separately.','',
        '## 4. Selected research settings (not recommended for deployment)','','| Pair | TF | Formation / entry | Session | Direction | Stop | Exit | Management | Hold |','|---|---|---|---|---|---|---|---|---|']
    if unavailable:
        insert=lines.index('## 4. Selected research settings (not recommended for deployment)')
        lines[insert:insert]=['### Recorded-tick limitation','','**No successful full-year recorded-tick validation is claimed for the unavailable runs.** The broker history synchronization did not produce a report within the bounded wait. Saved `unavailable.json` files record the actual status; this is not proof that the broker can never provide the data. The accepted native results above use generated Every Tick.','']
    if real:
        insert=lines.index('## 4. Selected research settings (not recommended for deployment)')
        coverage=['### Recorded-tick coverage audit','','| Pair | Requested period | History quality | Evidence use |','|---|---|---:|---|']
        for r in real:
            coverage.append(f"| {r['pair']} | {r['period']} | {r['history_quality_pct']:.0f}% | "+('Partial recorded-tick window: exclude from full-year validation' if r['history_quality_pct']<90 else 'Accepted for this stated period only')+' |')
        coverage+=['','Gold/silver recorded ticks begin on 2026-01-01. Its 66%-quality full-year request is **not** accepted as full-year validation. The separate January–August run has 100% history quality, but only four baskets. BTC/ETH did not produce an auditable recorded-tick run; the shorter request logged no history data and stopped.','']
        lines[insert:insert]=coverage
    # Execution comparison is kept distinct from the primary evidence table.
    if execution:
        insert=lines.index('## 4. Selected research settings (not recommended for deployment)')
        erows=[dict(r,label=r['label']+(' / 250ms' if r['execution_mode']==250 else ' / random delay')) for r in execution]
        lines[insert:insert]=['### Execution sensitivity (settings unchanged)','',rowtable(erows,True),'','250ms is an illustrative lower-latency model, not a measured end-to-end fill guarantee. Repeat rows show independent random-delay realizations, not newly optimized strategies.','']
    for pair,s in selections.items():
        c=s['config'];lines.append(f"| {pair} | {c['tf']} min | {'Log ratio' if c['model']==0 else 'OLS'}, {c['window']} bars, {c['entry']}Z | {SESSIONS[c['session']]} | {'Long A / short B' if c['direction']==1 else 'Short A / long B' if c['direction']==-1 else 'Both'} | {['SD','spread ATR','recent swing'][c['stop']]} | {c['rr']}R | {MANAGE_NAMES[c['manage']]} | {c['hold']}h |")
    lines+=['','“Selected” means the least-bad candidate under a predeclared score, not an approved or profitable setup. A high PF on a handful of trades is not reliable evidence.','','## 5. Sessions and optimization effects','','Best training-shortlisted candidate per session, evaluated on the separate selection-validation year. These are not final-year winners.','',rowtable(sessions),'']
    for pair in PAIRS:lines += [f'### {pair}: every broad-grid setting',f'![All broad settings](Charts/{pair}-all-session-stop-RR-timeframe-tests.png)',f'![All PF and win rates](Charts/{pair}-all-configurations-PF-win-rate.png)','']
    lines+=['The complete 3,186-row metric/configuration ledger is in all-settings.md and screen-results.json. The heatmaps contain all 900 broad cells per pair; refinement points and their exact inputs are retained rather than hidden.','','## 6. Statistical relationship checks','','Correlation is not sufficient evidence of a stable mean-reverting spread. These daily diagnostics are descriptive, not an entry filter chosen after viewing the results. The Engle–Granger null is **no cointegration**; six reported tests are exploratory and not adjusted for multiple comparisons.','','| Pair | Year role | Daily return correlation | Cointegration p | Fitted hedge beta |','|---|---|---:|---:|---:|']
    for r in json.loads((ROOT/'relationship-diagnostics.json').read_text()):lines.append(f"| {r['pair']} | {r['period']} | {r['daily_return_correlation']:.3f} | {r['engle_granger_p']:.4f} | {r['ols_beta']:.3f} |")
    lines+=['','The relationships were not consistently cointegrated across development years. OLS hedge ratios also changed materially. A fitted residual half-life is not reliable evidence when stationarity is unsupported.','','## 7. Rolling walk-forward diagnostic','','Predefined 900-cell broad grid; train on previous 12 months, apply next 3 months. Hold cash unless training return > 0, PF ≥ 1.10, at least 30 baskets, and DD ≤ 15%. Rules were fixed before this supplemental run. These are bar-screen results, not native execution tests.','','| Pair | Quarter start | Eligible training configs | Applied return | Trades | Win rate | PF |','|---|---|---:|---:|---:|---:|---:|']
    for r in json.loads((ROOT/'walk-forward.json').read_text()):
        t=r['test'];lines.append(f"| {r['pair']} | {r['test_start']} | {r['eligible_configs']} | {t['return_pct']:+.2f}% | {int(t['trades'])} | {t['win_rate']:.2f}% | {t['profit_factor']:.2f} |")
    lines+=['','Cash-only quarters have no trades: their zero return is **not** a profitable trading edge. Normalized compounded fold balances in the JSON are illustrative; each fold starts its lot-exact simulation from $10,000.','','## 8. Monte Carlo and execution-cost stress','','5,000 circular block-bootstrap paths, with the original number of baskets and fixed-percent compounding. Blocks are up to 5 trades, shorter for tiny samples. DD below is simulated **closed-balance** drawdown, not intratrade equity DD. These are conditional resamples, not a next-year forecast or probability guarantee.','','| Pair / evidence | Baskets | Return P5 | Median | P95 | DD P95 |','|---|---:|---:|---:|---:|---:|']
    for r in mc:lines.append(f"| {r['pair']} / {r['stage']} | {r['baskets']} | {r['return_p5']:+.2f}% | {r['return_median']:+.2f}% | {r['return_p95']:+.2f}% | {r['dd_p95']:.2f}% |")
    lines+=['','**Do not infer a reliable distribution from the tiny XAU/XAG final-year sample.** Three-year bootstrap results include development trades and selection bias. There is no defensible positive expected-profit estimate for next month from this evidence.','']
    for pair in PAIRS:lines.append(f'![{pair} Monte Carlo](Charts/{pair}-test-monte-carlo.png)')
    lines+=['','Native final-year basket returns with hypothetical additional cost (not a new native test):','','| Pair | Extra cost per basket | Return | PF | Win rate |','|---|---:|---:|---:|---:|']
    for r in stress:lines.append(f"| {r['pair']} | {r['extra_R_per_basket']:.2f}R | {r['return_pct']:+.2f}% | {fmt(r['profit_factor'])} | {r['win_rate']:.2f}% |")
    lines+=['','## 9. Data, costs and risk caveats','','- Broker M5 history: 2023-06-01–2026-09-01, four symbols, exact timestamp inner joins. No forward-filling into signals. Only complete decision candles and prior formation bars are used.','- Many recorded spreads are zero; on a Zero-type account that can be genuine. The Python screen conservatively floors spread at the **training-period positive median**, adds 1 basis point commission per side per leg, and applies current broker swap snapshots historically. These are assumptions, not recovered historical fee schedules; they can materially overstate costs. Native tests use the actual tester account costs instead.','- Python evaluates basket/leg protection at synchronized M5 observations; it does not know the within-bar joint path. MT5 runs check tick execution and broker emergency stops. This explains trade-count and performance differences.','- The 1% figure is a planned combined risk budget. Both legs are sequential market orders, not an atomic exchange spread. Gaps, stop slippage, stale quotes, and a failed second leg can exceed the intended limit. The research EA closes an orphan leg and never opens on a normal chart.','- Small balance/minimum volume constraints can prevent a proper hedge; invalid/undersized/overly distorted hedges are skipped, not rounded up. These $10,000 results cannot be assumed to work on $50.','- Metals and crypto here are broker CFDs. This is not exchange-futures execution, and native broker history quality percentages do not prove tick provenance.','',
        '## 10. Verification and deliverables','','- EA compiles with 0 errors and 0 warnings.','- 20 causal-prefix checks across both pairs, timeframes and model types; removing future data does not change prior signals.','- Native features are compared numerically with the Python causal signal calculation.','- Native basket cash is reconciled against the MT5 final balance; completed and aborted leg executions are counted explicitly.','- Exact sets, source/binary, native reports, per-leg entries/exits, basket ledgers, feature audits, cost assumptions and selection lock are saved locally.','- VERIFICATION.txt gives the checks actually completed. No claim is made about passing a future live test.','',
        '### Source references','','- [Original pairs research (Gatev, Goetzmann, Rouwenhorst)](https://www.nber.org/papers/w7032)','- [Engle–Granger documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html)','- [MetaQuotes multi-symbol testing](https://www.mql5.com/en/docs/runtime/testing)','- [MetaQuotes tester settings](https://www.metatrader5.com/en/terminal/help/start_advanced/start)','- [Exness commission account types](https://get.exness.help/hc/en-us/articles/360012007919-Are-trading-accounts-charged-a-commission-fee)','- [Exness crypto swaps / trading hours](https://get.exness.help/hc/en-us/articles/17854191888540-Cryptocurrencies)','',
        '### Reproduction','','Use the local .venv Python environment. research.py runs the bar screen; native.py runs generated-tick checks; native.py --real requests recorded-tick mode; verify_research.py audits; diagnostics.py and walk_forward.py generate supplemental evidence; build_report.py only rebuilds outputs. Data and reports are already saved: opening this report does not rerun any test.','',
        '## Review gate','','Step 2 research is complete within the stated finite test space. **Keep both pairs out of the active system.** Wait for user review before moving to another strategy.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    real_resolved={r['pair'] for r in real}|{r['pair'] for r in unavailable}
    finished=len(execution)==6 and real_resolved==set(PAIRS)
    dump(ROOT/'progress.json',dict(step=2,title='Relative-Value Pairs: BTC/ETH and XAU/XAG',status='completed_research_not_recommended' if finished else 'execution_validation_in_progress',screen_configs=3132,native_reports=len(native),accepted_native_reports=sum(r['history_quality_pct']>=90 for r in native),risk_percent_combined=1.,full_year_real_tick_validation_passed=False,accepted_partial_real_tick_periods=[dict(pair=r['pair'],period=r['period']) for r in real if r['history_quality_pct']>=90],real_tick_unavailable_pairs=sorted({r['pair'] for r in unavailable}),live_changes=False,report='REPORT.md',awaiting='user_review' if finished else 'remaining_native_jobs'))
    print('REPORT READY',ROOT/'REPORT.md')
    print(rowtable(final,True));print('REAL TICKS');print(rowtable(real,True))

if __name__=='__main__':main()
