"""Build the final report and robustness artefacts from frozen saved evidence."""
from pathlib import Path
import importlib.util
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
CHARTS=ROOT/'Charts';CHARTS.mkdir(exist_ok=True)
SYMBOLS=('XAUUSD','XAGUSD','USTEC','US30','GBPJPY')
spec=importlib.util.spec_from_file_location('screen',ROOT/'research.py');screen=importlib.util.module_from_spec(spec);sys.modules['screen']=screen;spec.loader.exec_module(screen)

def money_pct(value):return f'{value:+.2f}%'
def metric_table(rows, native=False):
    lines=['| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for symbol,m in rows:
        lines.append(f'| {symbol} | {money_pct(m["return_pct"])} | {m["profit_factor"]:.2f} | {m["win_rate"]:.2f}% | {m["equity_dd_pct" if native else "max_dd_pct"]:.2f}% | {int(m["trades"])} | {m["sharpe_ratio" if native else "sharpe"]:.2f} | {m["recovery_factor" if native else "recovery"]:.2f} |')
    return '\n'.join(lines)

def native_map(rows,stage):return {x['symbol']:x for x in rows if x['stage']==stage}

def bootstrap(rs,paths=10000,seed=9604):
    if not len(rs):return np.zeros(paths),np.zeros(paths)
    rng=np.random.default_rng(seed);ret=np.empty(paths);dd=np.empty(paths);block=5
    for p in range(paths):
        starts=rng.integers(0,max(1,len(rs)-block+1),size=math.ceil(len(rs)/block));sample=np.concatenate([rs[s:s+block] for s in starts])[:len(rs)]
        curve=np.r_[1.0,np.cumprod(1+sample)];ret[p]=(curve[-1]-1)*100;dd[p]=np.max(1-curve/np.maximum.accumulate(curve))*100
    return ret,dd

def main():
    final=json.loads((ROOT/'screen-final.json').read_text(encoding='utf-8'));native_rows=json.loads((ROOT/'native-results.json').read_text(encoding='utf-8'))
    locked_native=native_map(native_rows,'locked');full_native=native_map(native_rows,'full')
    grid=pd.read_csv(ROOT/'all-screen-results.csv');grid['cfg']=grid.config.map(json.loads)
    rr_rows=[];session_rows=[];management_rows=[];stop_rows=[]
    for _,row in grid.iterrows():
        cfg=row.cfg
        common=dict(symbol=row.symbol,train_return=row.train_return_pct,train_pf=row.train_profit_factor,train_win_rate=row.train_win_rate,train_dd=row.train_max_dd_pct,train_trades=row.train_trades,
                    validation_return=row.validation_return_pct,validation_pf=row.validation_profit_factor,validation_win_rate=row.validation_win_rate,validation_dd=row.validation_max_dd_pct,validation_trades=row.validation_trades,score=row.score)
        if row.phase=='target':rr_rows.append(common|dict(target=cfg['target_mode'],rr=cfg['rr']))
        elif row.phase=='session-timeframe-recheck':session_rows.append(common|dict(timeframe=cfg['timeframe'],session=cfg['session']))
        elif row.phase=='management':management_rows.append(common|dict(management=cfg['management']))
        elif row.phase=='stop':stop_rows.append(common|dict(stop=cfg['stop_mode'],stop_value=cfg['stop_value']))
    pd.DataFrame(rr_rows).to_csv(ROOT/'rr-sensitivity.csv',index=False);pd.DataFrame(session_rows).to_csv(ROOT/'session-timeframe-sensitivity.csv',index=False)
    pd.DataFrame(management_rows).to_csv(ROOT/'management-sensitivity.csv',index=False);pd.DataFrame(stop_rows).to_csv(ROOT/'stop-sensitivity.csv',index=False)

    # Frozen half-year slices; parameters are never re-selected on these intervals.
    periods=[]
    starts=pd.date_range('2023-09-01','2026-03-01',freq='6MS',tz='UTC')
    for symbol in SYMBOLS:
        base,_=screen.load(symbol);c=screen.Config(**final[symbol]['config']);bars=screen.resample(base,c.timeframe);arrays=screen.anchored_features(bars,c.session)
        for start in starts:
            end=min(start+pd.DateOffset(months=6),pd.Timestamp('2026-09-01',tz='UTC'));m=screen.run(arrays,c,(start,end))
            periods.append(dict(symbol=symbol,start=start.date().isoformat(),end=end.date().isoformat(),**m))
    rolling=pd.DataFrame(periods);rolling.to_csv(ROOT/'rolling-stability.csv',index=False)

    # Bootstrap native locked trade returns; these include native spread, commission and swap.
    mc=[];mc_distributions=[]
    for index,symbol in enumerate(SYMBOLS):
        trades=json.loads((ROOT/'Native'/f'{symbol.lower()}-frozen-locked-model0'/'trades.json').read_text(encoding='utf-8'))
        rs=np.array([x['return_fraction'] for x in trades],float);returns,dds=bootstrap(rs,10000,9604+index)
        mc.append(dict(symbol=symbol,paths=10000,profitable_probability=float(np.mean(returns>0)*100),return_p5=float(np.percentile(returns,5)),return_median=float(np.median(returns)),return_p95=float(np.percentile(returns,95)),dd_median=float(np.median(dds)),dd_p95=float(np.percentile(dds,95)),trades=len(rs)))
        mc_distributions.append(returns)
    pd.DataFrame(mc).to_csv(ROOT/'monte-carlo-summary.csv',index=False)

    fig,ax=plt.subplots(figsize=(13,7));ax.boxplot(mc_distributions,tick_labels=SYMBOLS,showfliers=False,patch_artist=True,boxprops=dict(facecolor='#34d399',alpha=.55));ax.axhline(0,color='#ef4444',ls='--');ax.set_ylabel('Bootstrapped locked-year return (%)');ax.set_title('Native locked-trade Monte Carlo — 10,000 block-bootstrap paths');ax.grid(alpha=.2,axis='y');fig.tight_layout();fig.savefig(CHARTS/'monte-carlo.png',dpi=170);plt.close(fig)

    pivot=rolling.pivot(index='symbol',columns='start',values='return_pct').reindex(SYMBOLS)
    fig,ax=plt.subplots(figsize=(14,5));image=ax.imshow(pivot.to_numpy(),cmap='RdYlGn',aspect='auto',vmin=-max(1,np.nanmax(np.abs(pivot))),vmax=max(1,np.nanmax(np.abs(pivot))))
    ax.set_xticks(range(len(pivot.columns)),[x[:7] for x in pivot.columns]);ax.set_yticks(range(len(pivot.index)),pivot.index)
    for y in range(len(pivot.index)):
        for x in range(len(pivot.columns)):ax.text(x,y,f'{pivot.iloc[y,x]:+.1f}%',ha='center',va='center',fontsize=8)
    ax.set_title('Frozen configuration — six-month return stability');fig.colorbar(image,ax=ax,label='Return %');fig.tight_layout();fig.savefig(CHARTS/'rolling-stability.png',dpi=170);plt.close(fig)

    rr=pd.DataFrame(rr_rows);fig,axes=plt.subplots(2,3,figsize=(15,9));
    for ax,symbol in zip(axes.flat,SYMBOLS):
        x=rr[(rr.symbol==symbol)&(rr.target=='fixed-r')].sort_values('rr');ax.plot(x.rr,x.validation_return,marker='o',color='#34d399');ax.axhline(0,color='#777',lw=.8);ax.set_title(symbol);ax.set_xlabel('Fixed target (R)');ax.set_ylabel('Pre-lock validation return %');ax.grid(alpha=.2)
    axes.flat[-1].axis('off');fig.suptitle('Reward:risk sensitivity before the locked year');fig.tight_layout();fig.savefig(CHARTS/'rr-sensitivity.png',dpi=170);plt.close(fig)

    session=pd.DataFrame(session_rows);fig,axes=plt.subplots(2,3,figsize=(17,9));
    for ax,symbol in zip(axes.flat,SYMBOLS):
        x=session[session.symbol==symbol].pivot(index='timeframe',columns='session',values='validation_return').reindex(index=('M5','M15','M30','H1'),columns=screen.SESSIONS)
        vmax=max(1,float(np.nanmax(np.abs(x.to_numpy()))));im=ax.imshow(x.to_numpy(),cmap='RdYlGn',aspect='auto',vmin=-vmax,vmax=vmax);ax.set_xticks(range(len(x.columns)),x.columns,rotation=35,ha='right');ax.set_yticks(range(len(x.index)),x.index);ax.set_title(symbol)
        for y in range(len(x.index)):
            for z in range(len(x.columns)):ax.text(z,y,f'{x.iloc[y,z]:+.1f}',ha='center',va='center',fontsize=7)
    axes.flat[-1].axis('off');fig.suptitle('Session × timeframe pre-lock validation return (%)');fig.tight_layout();fig.savefig(CHARTS/'session-timeframe-sensitivity.png',dpi=170);plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(15,5));native_locked=[locked_native[s] for s in SYMBOLS]
    axes[0].bar(SYMBOLS,[x['return_pct'] for x in native_locked],color=['#34d399' if x['return_pct']>0 else '#fb7185' for x in native_locked]);axes[0].set_title('Native locked return (%)')
    axes[1].bar(SYMBOLS,[x['profit_factor'] for x in native_locked],color='#60a5fa');axes[1].axhline(1.1,color='#fbbf24',ls='--');axes[1].set_title('Native locked PF')
    axes[2].bar(SYMBOLS,[x['win_rate'] for x in native_locked],color='#a78bfa');axes[2].set_title('Native locked win rate (%)')
    for ax in axes:ax.tick_params(axis='x',rotation=30);ax.grid(alpha=.2,axis='y')
    fig.suptitle('Session VWAP Snapback — MT5 Every Tick / random delay');fig.tight_layout();fig.savefig(CHARTS/'native-locked-summary.png',dpi=170);plt.close(fig)

    config_lines=['| Asset | TF | Session | Band | Confirmation | Regime | Direction | Stop | Target | Management |','|---|---|---|---:|---|---|---|---|---|---|']
    for symbol in SYMBOLS:
        c=final[symbol]['config'];target='VWAP' if c['target_mode']=='vwap' else f'{c["rr"]:g}R';config_lines.append(f'| {symbol} | {c["timeframe"]} | {c["session"]} | {c["sigma"]:g}σ | {c["confirmation"]} | {c["regime"]} | {c["direction"]} | {c["stop_mode"]} {c["stop_value"]:g} | {target} | {c["management"]} |')
    mc_lines=['| Asset | Profit probability | Return P5 | Median return | Return P95 | Median DD | DD P95 |','|---|---:|---:|---:|---:|---:|---:|']
    for x in mc:mc_lines.append(f'| {x["symbol"]} | {x["profitable_probability"]:.2f}% | {x["return_p5"]:+.2f}% | {x["return_median"]:+.2f}% | {x["return_p95"]:+.2f}% | {x["dd_median"]:.2f}% | {x["dd_p95"]:.2f}% |')
    positive_folds=rolling.assign(positive=rolling.return_pct>0).groupby('symbol').positive.agg(['sum','count'])
    stability_lines=['| Asset | Positive six-month periods | Worst period | Best period |','|---|---:|---:|---:|']
    for s in SYMBOLS:stability_lines.append(f'| {s} | {int(positive_folds.loc[s,"sum"])}/{int(positive_folds.loc[s,"count"])} | {rolling[rolling.symbol==s].return_pct.min():+.2f}% | {rolling[rolling.symbol==s].return_pct.max():+.2f}% |')

    report=f'''# Step 4 — Session VWAP Liquidity Snapback

## Final decision: reject for the active system

None of the five markets passes the pre-declared locked-year gate. **No BAT, website listing, recommended portfolio, or live MT5 profile was changed.** XAGUSD is the only positive locked-year candidate, but 15 native trades are far below the 30-trade minimum and are not enough to establish an edge.

## Native MT5 locked-year evidence

Frozen settings, 2025-09-01 through 2026-09-01, generated Every Tick, random execution delay, broker spread, commission and swap, exactly 1% equity risk.

{metric_table([(s,locked_native[s]) for s in SYMBOLS],True)}

![Native locked summary](Charts/native-locked-summary.png)

### US100 retest

US100 was re-tested from scratch under the new details. The selected H1 Asia / 2.5σ / ADX≤25 / 0.75 ATR stop / 0.5R version produced **{locked_native['USTEC']['return_pct']:+.2f}%**, PF **{locked_native['USTEC']['profit_factor']:.2f}**, **{locked_native['USTEC']['win_rate']:.2f}%** wins, **{locked_native['USTEC']['equity_dd_pct']:.2f}%** DD and **{locked_native['USTEC']['trades']} trades**. A 0.5R target needs roughly 66.7% wins before costs; its native {locked_native['USTEC']['win_rate']:.2f}% was not enough. It remains rejected.

## Frozen configurations

{chr(10).join(config_lines)}

Every setting above was selected from the two pre-lock years before the final year was read.

## Broad-screen locked year

The Python M5 screen includes recorded spread, conservative stop-first bar handling and an added 0.02R execution charge. Native MT5 evidence above is the final authority.

{metric_table([(s,final[s]['locked']) for s in SYMBOLS])}

![Locked equity curves](Charts/locked-equity-curves.png)

## Three-year native context — not independent validation

This interval contains the development sample, so it is descriptive only.

{metric_table([(s,full_native[s]) for s in SYMBOLS],True)}

![Configuration screen](Charts/configuration-screen.png)

## Temporal stability

{chr(10).join(stability_lines)}

![Rolling stability](Charts/rolling-stability.png)

## Monte Carlo

10,000 five-trade block-bootstrap paths use the exact native locked trade returns. With only 6–57 trades per market, these ranges are highly uncertain rather than forecasts.

{chr(10).join(mc_lines)}

![Monte Carlo](Charts/monte-carlo.png)

## RR, session, timeframe, stop and trailing tests

- Fixed targets tested: 0.5R, 0.75R, 1R, 1.5R, 2R, 2.5R, 3R, 4R and 6R, plus central-VWAP exit.
- Stops tested: rejection candle, four-bar swing, session extreme, and 0.75/1/1.25/1.5 ATR.
- Management tested: none, breakeven, 1.5 ATR trailing and the M15 50%-to-20% dynamic stop.
- Sessions tested: Asia, London, New York, London–New York overlap and UTC all-day.
- Timeframes tested: M5, M15, M30 and H1.
- Directions tested: both, long-only and short-only.

![RR sensitivity](Charts/rr-sensitivity.png)

![Session and timeframe sensitivity](Charts/session-timeframe-sensitivity.png)

The surviving pre-lock configurations all selected **no trailing**. In this strategy, trailing and breakeven generally cut the intended return-to-VWAP path before it completed. Full comparison rows are saved in `rr-sensitivity.csv`, `session-timeframe-sensitivity.csv`, `stop-sensitivity.csv`, and `management-sensitivity.csv`.

## Regime and news handling

The regime layer tested no gate, ADX ceilings, normalized EMA-slope flatness, their intersection, and a causal 20-day three-state return filter. This last filter follows the regime skill's 20-bar / ±5% framework and was used only as a veto, never as an entry signal. The frozen winners chose ADX ceilings, but that did not hold in the locked year.

MT5's economic calendar is unavailable in Strategy Tester. The research EA includes an optional live high-impact USD-event block, but it is disabled in these tests so live and historical rules are not falsely presented as identical. No claim is made that a historical news filter was tested.

## Evidence and implementation notes

- 8,630 pre-lock configurations were evaluated across five assets.
- Native locked runs have 99–100% history quality; native three-year context runs have 98–100% quality.
- Exness CFDs provide broker tick activity, not centralized futures volume. USTEC/US30 should later be revalidated using NQ/YM exchange volume if migrated to NinjaTrader.
- The research EA compiles with 0 errors and 0 warnings and refuses live/demo-chart attachment by default (`InpTesterOnly=true`).
- Backtests and Monte Carlo are historical diagnostics, not expected future returns.

## Files

- `all-screen-results.csv`: all 8,630 pre-lock evaluations.
- `selection-lock.json`: configurations frozen before the locked year was read.
- `screen-final.json`: saved screen results and trades.
- `native-results.csv` / `Native/`: native reports, graphs and reconciled trade ledgers.
- `rolling-stability.csv`: frozen six-month slices.
- `EA/Calyx Session VWAP Snapback EA.mq5`: tester-only source.
'''
    (ROOT/'REPORT.md').write_text(report,encoding='utf-8')
    progress=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'));progress.update(status='complete',native_locked_runs=5,native_full_runs=5,rolling_periods=len(rolling),monte_carlo_paths=10000,recommendation='Reject all; XAGUSD watch-only due to 15 native locked trades',production_changed=False);(ROOT/'progress.json').write_text(json.dumps(progress,indent=2),encoding='utf-8')
    print('REPORT COMPLETE',flush=True)

if __name__=='__main__':main()
