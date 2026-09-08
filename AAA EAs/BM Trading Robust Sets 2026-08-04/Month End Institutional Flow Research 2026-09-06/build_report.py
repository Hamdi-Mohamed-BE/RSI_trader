from pathlib import Path
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CHARTS = ROOT / "Charts"


def monte_carlo(trades, paths=10000, seed=260906):
    returns = np.asarray([float(item["return_fraction"]) for item in trades], dtype=float)
    if not len(returns): return {}
    rng = np.random.default_rng(seed); endings = np.empty(paths); drawdowns = np.empty(paths); block = min(3, len(returns))
    for index in range(paths):
        starts = rng.integers(0, max(1, len(returns)-block+1), size=math.ceil(len(returns)/block)); sample = np.concatenate([returns[start:start+block] for start in starts])[:len(returns)]
        curve = np.r_[1.0, np.cumprod(1.0+sample)]; endings[index] = (curve[-1]-1.0)*100; drawdowns[index] = np.max(1.0-curve/np.maximum.accumulate(curve))*100
    return dict(paths=paths, profitable_probability=float(np.mean(endings>0)*100), return_p5=float(np.percentile(endings,5)), return_median=float(np.median(endings)), return_p95=float(np.percentile(endings,95)), dd_median=float(np.median(drawdowns)), dd_p95=float(np.percentile(drawdowns,95)), endings=endings, drawdowns=drawdowns)


def main():
    CHARTS.mkdir(exist_ok=True)
    native = json.loads((ROOT/"native-results.json").read_text(encoding="utf-8")); selections = json.loads((ROOT/"selection-lock.json").read_text(encoding="utf-8"))
    locked = {row["symbol"]:row for row in native if row["stage"]=="locked"}; full = {row["symbol"]:row for row in native if row["stage"]=="full"}
    monte_rows=[]; monte_raw={}
    for symbol,row in locked.items():
        trades=json.loads((ROOT/"Native"/row["case"]/"trades.json").read_text(encoding="utf-8")); result=monte_carlo(trades);monte_raw[symbol]=result
        monte_rows.append(dict(symbol=symbol,**{key:value for key,value in result.items() if key not in ("endings","drawdowns")},trades=len(trades)))
    pd.DataFrame(monte_rows).to_csv(ROOT/"native-monte-carlo-summary.csv",index=False)
    symbols=list(locked);fig,axes=plt.subplots(2,2,figsize=(13,8))
    metrics=(("return_pct","Return (%)"),("profit_factor","Profit factor"),("win_rate","Win rate (%)"),("equity_dd_pct","Max equity DD (%)"))
    for axis,(key,title) in zip(axes.flat,metrics):
        values=[locked[symbol][key] for symbol in symbols];axis.bar(symbols,values,color="#39e6a0" if key!="equity_dd_pct" else "#fb7185");axis.set_title(title);axis.grid(alpha=.2,axis="y")
        if key=="profit_factor":axis.axhline(1.1,color="#fbbf24",ls="--")
    fig.suptitle("Month-End Institutional Flow — native MT5 locked year");fig.tight_layout();fig.savefig(CHARTS/"native-locked-summary.png",dpi=170);plt.close(fig)
    fig,axis=plt.subplots(figsize=(12,6))
    for symbol,row in locked.items():
        series=row["series"];axis.plot([pd.Timestamp(point["date"]) for point in series],[point["balance"] for point in series],label=symbol,lw=1.7)
    axis.axhline(10000,color="#777",ls="--",lw=.8);axis.set_title("Native MT5 locked-year balance — fixed 1% risk");axis.set_ylabel("USD");axis.grid(alpha=.2);axis.legend();fig.tight_layout();fig.savefig(CHARTS/"native-locked-equity.png",dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for axis,symbol in zip(axes,symbols):
        result=monte_raw[symbol];axis.hist(result["endings"],bins=45,color="#60a5fa",alpha=.8);axis.axvline(np.median(result["endings"]),color="#fbbf24");axis.axvline(np.percentile(result["endings"],5),color="#fb7185",ls="--");axis.set_title(f"{symbol} locked-trade bootstrap");axis.set_xlabel("Ending return (%)");axis.grid(alpha=.2)
    fig.tight_layout();fig.savefig(CHARTS/"native-monte-carlo.png",dpi=170);plt.close(fig)
    rolling=pd.read_csv(ROOT/"rolling-stability.csv");fig,axes=plt.subplots(1,2,figsize=(13,5))
    for axis,symbol in zip(axes,symbols):
        group=rolling[rolling.symbol==symbol];axis.bar(range(len(group)),group.return_pct,color=["#39e6a0" if value>0 else "#fb7185" for value in group.return_pct]);axis.axhline(0,color="#888",lw=.8);axis.set_title(f"{symbol} rolling 6-month proxy return");axis.set_xlabel("3-month roll index");axis.set_ylabel("Return (%)");axis.grid(alpha=.2,axis="y")
    fig.tight_layout();fig.savefig(CHARTS/"rolling-stability.png",dpi=170);plt.close(fig)

    report=["# Step 5 — Month-End Institutional Flow", "", "## Decision", ""]
    report.append("**Recommend US100 for a separate fixed-1% demo-forward allocation; keep US30 out of the active system for now.** US100 passes every locked gate with contained drawdown. US30 is profitable in native MT5, but its 13.53% locked drawdown and negative Monte Carlo downside make it too fragile for promotion.")
    report += ["", "The calendar rule is known before entry and uses Monday-Friday calendar positions, so it does not inspect future bars to discover the final trading day. The research basis is the documented turn-of-the-month return concentration from the last business day through the first three business days; institutional liquidity and portfolio rebalancing are plausible mechanisms, not guarantees.", "", "## Native MT5 locked-year results", "", "| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in symbols:
        row=locked[symbol];report.append(f"| {symbol} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['sharpe_ratio']:.2f} | {row['recovery_factor']:.2f} |")
    report += ["", "Period: 2025-09-01 to 2026-09-01. Native MT5 generated Every Tick, random execution delay, broker spread, commission and swap; USD 10,000 start and fixed 1% equity risk.", "", "## Frozen configurations", ""]
    for symbol in symbols:
        config=selections[symbol]["config"];report += [f"### {symbol}", "", "- "+", ".join(f"{key}={value}" for key,value in config.items()), ""]
    report += ["## Three-year native context", "", "| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in symbols:
        row=full[symbol];report.append(f"| {symbol} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['sharpe_ratio']:.2f} | {row['recovery_factor']:.2f} |")
    report += ["", "The three-year rows include the development period and are context, not independent validation.", "", "## Native locked-trade Monte Carlo", "", "| Asset | Profit probability | Return P5 | Median return | Return P95 | Median DD | DD P95 | Trades |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in monte_rows:report.append(f"| {row['symbol']} | {row['profitable_probability']:.2f}% | {row['return_p5']:+.2f}% | {row['return_median']:+.2f}% | {row['return_p95']:+.2f}% | {row['dd_median']:.2f}% | {row['dd_p95']:.2f}% | {row['trades']} |")
    report += ["", "Bootstrap: 10,000 three-trade moving-block resamples of the same locked native trades. It estimates sequencing risk but cannot create new market regimes or solve a small sample.", "", "## Pipeline coverage", "", "The pre-lock search tested M5/M15/M30/H1, London open/New York open/first-hour/power-hour entries, eight turn-of-month windows, three direction modes, seven daily filters, three candle confirmations, 6/12/24/72/120-hour holds, seven stop variants, RR 0.5/0.75/1/1.5/2/2.5/3/4/6, and no management/break-even/ATR trail/Dynamic M15 50/20. The selected configurations both retained no trailing.", "", "## Evidence limits", "", "- CFD broker hours and D1 candles differ from exchange futures sessions.", "- The effect is calendar-based and can weaken as flows, index composition and execution costs change.", "- Native MT5 Sharpe can look unusually high on sparse event trades; PF, drawdown, trade count and Monte Carlo downside carry more decision weight.", "- US100 should remain demo-only until at least 30-50 forward trades confirm implementation and slippage.", "", "## Files", "", "- `selection-lock.json`: frozen pre-lock choices.", "- `all-screen-results.csv`: every staged pre-lock configuration.", "- `rr-sensitivity.csv`, `stop-sensitivity.csv`, `management-sensitivity.csv`, `calendar-session-timeframe-sensitivity.csv`: pipeline comparisons.", "- `native-results.csv`, `native-monte-carlo-summary.csv`, `rolling-stability.csv`: final evidence tables.", "- `Charts/`: locked equity, metrics, RR, rolling and Monte Carlo graphs."]
    (ROOT/"REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    progress=json.loads((ROOT/"progress.json").read_text(encoding="utf-8"));progress.update(status="complete",native_locked_runs=2,native_full_runs=2,monte_carlo_paths=10000,recommendation="US100 demo-forward at fixed 1%; reject US30",production_changed=False);(ROOT/"progress.json").write_text(json.dumps(progress,indent=2),encoding="utf-8")


if __name__=="__main__":main()
