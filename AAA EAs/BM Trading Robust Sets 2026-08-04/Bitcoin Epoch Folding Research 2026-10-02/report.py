"""Generate a standalone research report and static scientific figures from cached results."""
from pathlib import Path
import html
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
plt.rcParams.update({'figure.facecolor':'#0b1916','axes.facecolor':'#0b1916','text.color':'#e7f7f2',
                     'axes.labelcolor':'#b4cfcb','xtick.color':'#b4cfcb','ytick.color':'#b4cfcb',
                     'axes.edgecolor':'#33534b','grid.color':'#33534b','font.size':11,'savefig.facecolor':'#0b1916'})


def main():
    r=json.loads((ROOT/'RESULTS.json').read_text());p=r['profiles']
    qa=json.loads((ROOT/'VERIFICATION.json').read_text()) if (ROOT/'VERIFICATION.json').exists() else None
    m=pd.read_csv(ROOT/'MONTHLY SCORES.csv',index_col=0)
    f=pd.read_csv(ROOT/'FORECASTS.csv.gz',parse_dates=['time']).set_index('time')
    colors=['#8ca9a0','#c9a7ef','#f6c975','#7df3c7']
    fig,axes=plt.subplots(2,2,figsize=(13,8.5),layout='constrained')
    ax=axes[0,0]
    ax.plot(range(24),p['first_half_hour_profile'],label='First half of test year',color=colors[1])
    ax.plot(range(24),p['second_half_hour_profile'],label='Second half',color=colors[3])
    ax.axhline(1,color=colors[0],lw=1,alpha=.7)
    ax.set(title='Bitcoin daily rhythm: shifts over the year',xlabel='Hour of day (UTC)',ylabel='Day-normalized absolute return')
    ax.set_xticks(range(0,24,3));ax.legend(fontsize=9);ax.grid(alpha=.3)
    ax=axes[0,1]
    names=['Hourly','Daily','Daily + weekly'];v=r['primary_comparisons'][:3]
    point=np.array([x['reduction_pct'] for x in v]);ci=np.array([x['ci95_pct'] for x in v])
    ax.errorbar(point,np.arange(3),xerr=[np.maximum(0,point-ci[:,0]),np.maximum(0,ci[:,1]-point)],fmt='o',color=colors[3],capsize=5)
    ax.set_yticks(range(3),names);ax.axvline(0,color=colors[0],lw=1)
    for i,x in enumerate(point):ax.annotate(f'{x:+.2f}%',(x,i),xytext=(6,-16 if i==0 else 9),textcoords='offset points',fontsize=10)
    ax.set(title='Out-of-sample forecast improvement',xlabel='QLIKE loss reduction vs EWMA (%)\n95% paired 7-day-block bootstrap interval')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.3)
    ax=axes[1,0]
    ax.bar(np.arange(len(m)),m.daily_weekly_reduction_pct,color=[colors[3] if v>0 else '#ed8585' for v in m.daily_weekly_reduction_pct])
    ax.set_xticks(np.arange(len(m)),m.index,rotation=55,ha='right',fontsize=9)
    ax.axhline(0,color=colors[0],lw=1)
    ax.set(title='Monthly consistency: daily + weekly',xlabel='Month (first and last are partial)',ylabel='QLIKE reduction vs EWMA (%)');ax.grid(axis='y',alpha=.3)
    ax=axes[1,1]
    values=np.array([v['hour_profile'] for v in p['monthly']])
    im=ax.imshow(values,aspect='auto',cmap='viridis',vmin=np.min(values),vmax=np.max(values))
    ax.set_xticks(range(0,24,3));ax.set_yticks(range(len(values)),[v['month'] for v in p['monthly']],fontsize=9)
    ax.set(title='Epoch-folded hourly activity by month',xlabel='Hour of day (UTC)',ylabel='Month')
    fig.colorbar(im,ax=ax,label='Day-normalized absolute return',fraction=.045,pad=.025)
    fig.suptitle('BTCUSDT spot | 2 Oct 2025–1 Oct 2026 | Volatility prediction, not trading profit',fontsize=14)
    fig.savefig(ROOT/'Bitcoin Epoch Folding Results.png',dpi=155);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
    axes[0].plot(np.arange(60),p['minute_of_hour_profile'],color=colors[3]);axes[0].axhline(1,color=colors[0],lw=1)
    axes[0].set(title='Fine hourly rhythm (descriptive test-year fold)',xlabel='Minute within each UTC hour',ylabel='Day-normalized |return|');axes[0].grid(alpha=.3)
    axes[1].bar(range(7),p['weekday_profile'],color=colors[3]);axes[1].axhline(1,color=colors[0],lw=1)
    axes[1].set_xticks(range(7),['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
    axes[1].set(title='Weekday activity (descriptive test-year fold)',xlabel='UTC weekday',ylabel='Mean |return| / full-year mean');axes[1].grid(axis='y',alpha=.3)
    fig.savefig(ROOT/'Hourly and Weekly Profiles.png',dpi=155);plt.close(fig)
    daily=f[[f'qlike_{i}' for i in range(4)]].resample('D').mean()
    daily['cumulative_gain']=(daily.qlike_0-daily.qlike_3).cumsum()
    daily.to_csv(ROOT/'CUMULATIVE FORECAST GAIN.csv')
    modelrows=''.join(f'<tr><td>{x["model"]}</td><td>{x["mean_qlike"]:.4f}</td><td>{x["reduction_vs_baseline_pct"]:+.2f}%</td></tr>' for x in r['models'])
    comrows=''.join(f'<tr><td>{x["model"]} vs {x["versus"]}</td><td>{x["reduction_pct"]:+.2f}%</td><td>{x["ci95_pct"][0]:+.2f}% to {x["ci95_pct"][1]:+.2f}%</td><td>{x["p_holm"]:.4f}</td></tr>' for x in r['primary_comparisons'])
    searchrows=''.join(f'<tr><td>{x["period_minutes"]} min</td><td>{x["statistic"]:.5f}</td><td>{x["p_unadjusted"]:.3f}</td><td>{x["p_bonferroni"]:.3f}</td><td>{"Survives" if x["survives"] else "Not significant"}</td></tr>' for x in r['period_search_training_only'])
    sensrows=''.join(f'<tr><td>{x["lambda_"]:.2f}</td><td>{v["model"]}</td><td>{v["mean_qlike"]:.4f}</td><td>{v["reduction_pct"]:+.2f}%</td></tr>' for x in r['lambda_sensitivity'] for v in x['models'])
    monthlyrows=''.join(f'<tr><td>{month}</td><td>{row.qlike_0:.4f}</td><td>{row.qlike_3:.4f}</td><td>{row.daily_weekly_reduction_pct:+.2f}%</td></tr>' for month,row in m.iterrows())
    best=min(r['models'],key=lambda x:x['mean_qlike'])
    top=', '.join(f'{h:02d}:00–{h+1:02d}:00' for h in p['busiest_hours_utc'])
    quiet=', '.join(f'{h:02d}:00–{h+1:02d}:00' for h in p['quietest_hours_utc'])
    qatext='' if qa is None else f'<h2>Verification</h2><p>{qa["unit_tests_passed"]} automated tests passed, including changing future data without changing earlier forecasts. Every forecast loss was independently recalculated; {qa["checksum_verified_archives"]} source archives passed SHA256 checks. In one seeded, seasonality-free clustered-volatility simulation, {qa["null_raw_rejections"]} of 14 periods passed an unadjusted 5% screen and {qa["null_adjusted_rejections"]} passed after multiple-testing correction. This single simulation is a sanity check, not a calibration study of false-positive rates. <a href="VERIFICATION.json">Full verification record</a>.</p>'
    doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bitcoin Epoch Folding — Calyx Research</title>
<style>:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{background:#0b1916;color:#e7f7f2;font:16px/1.65 system-ui;margin:0}}main{{max-width:1200px;margin:auto;padding:40px 24px}}h1{{font-size:clamp(30px,5vw,56px);line-height:1.15}}h2{{margin-top:42px}}p{{max-width:1000px;color:#b4cfcb}}.tag{{color:#7df3c7;letter-spacing:.1em;font-size:13px}}.notice{{padding:20px;background:#25301c;border-left:3px solid #d0c783}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #33534b}}th{{color:#a3c0b4}}.scroll{{overflow-x:auto}}img{{max-width:100%;height:auto}}a{{color:#7df3c7}}code{{overflow-wrap:anywhere}}details{{margin:20px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}}.metric{{background:#10231d;padding:20px}}.value{{font-size:29px;color:#7df3c7}}</style>
<main><div class="tag">CALYX · BITCOIN VOLATILITY RESEARCH · NO LIVE TRADING</div><h1>Does Bitcoin have a repeating rhythm?</h1>
<p>Binance spot BTCUSDT · 2 October 2025–1 October 2026 (UTC). Earlier observations train the models; the displayed year is out of sample. Daily refit, 180-day history, fixed parameters.</p>
<div class="notice">This is a volatility forecast test, not an EA return backtest. Larger expected moves do not reveal their direction. No win rate, profit factor, trade return or Sharpe is inferred from forecast improvement.</div>
<div class="grid"><div class="metric">Lowest forecast loss<div class="value">{best['model']}</div>{best['reduction_vs_baseline_pct']:+.2f}% vs EWMA</div><div class="metric">Out-of-sample minute returns<div class="value">{r['test_minute_returns']:,}</div>{r['missing_minute_returns']} missing</div><div class="metric">15-minute forecasts<div class="value">{r['test_rv_bins']:,}</div>{r['excluded_rv_bins']} excluded</div><div class="metric">Complete months improved (weekly model)<div class="value">{r['better_complete_months_weekly']} / {r['complete_months']}</div>vs non-seasonal EWMA</div></div>
<h2>Last-year forecast results</h2><p>QLIKE = realized variance / forecast − log(realized variance / forecast) − 1. Lower is better. No baseline was selected after seeing the test results.</p><div class="scroll"><table><tr><th>Model</th><th>Mean QLIKE</th><th>Loss reduction vs EWMA</th></tr>{modelrows}</table></div>
<img src="Bitcoin Epoch Folding Results.png" alt="Out-of-sample forecast performance and changing intraday activity patterns">
<h2>Uncertainty and significance</h2><p>Paired 5,000-draw moving-block bootstrap of daily losses, 7-day blocks. Holm correction over four forecast comparisons. A confidence interval crossing zero is not a robust improvement.</p><div class="scroll"><table><tr><th>Comparison</th><th>Reduction</th><th>95% interval</th><th>Holm p</th></tr>{comrows}</table></div>
<h2>When movement was larger</h2><p>Descriptive test-year profile, not a hindsight-selected trading rule. Busiest hours: {top} UTC. Quietest: {quiet} UTC. Their average day-normalized absolute-return ratio: {p['busiest_vs_quietest_abs_return_ratio']:.2f}×. Lagos time is UTC+1. First-half / second-half hourly ranking correlation: {p['first_second_half_spearman']:.3f}.</p><img src="Hourly and Weekly Profiles.png" alt="Minute-within-hour activity and weekday differences">
<h2>Training-only period search</h2><p>Fourteen predefined trial periods; 999 independently shifted seven-day blocks retain volatility clustering except at wrap boundaries. Bonferroni adjusts for the full search. Daily/hourly/weekly multiples can be aliases of the same rhythm; this does not discover fourteen independent trading cycles.</p><div class="scroll"><table><tr><th>Trial period</th><th>Folded statistic</th><th>Raw p</th><th>Adjusted p</th><th>Verdict</th></tr>{searchrows}</table></div>
<h2>Robustness checks</h2><p>Alternative EWMA memory (lambda 0.94 and 0.99) was specified before the test. All variants are shown, including worse results. Fourteen-day shift / forecast-bootstrap results are retained in the downloadable JSON, not used to choose the winner.</p><div class="scroll"><table><tr><th>EWMA lambda</th><th>Model</th><th>QLIKE</th><th>Reduction</th></tr>{sensrows}</table></div>
<details><summary>Monthly forecast breakdown</summary><div class="scroll"><table><tr><th>Month</th><th>Baseline</th><th>Daily + weekly</th><th>Reduction</th></tr>{monthlyrows}</table></div></details>
<h2>How the experiment works</h2><p>One-minute close-to-close log returns are squared and summed into non-overlapping 15-minute realized-variance targets. Every day, the previous 180 days estimate hourly/daily/weekly clock factors. Weekly mean normalization reduces changing volatility-level effects; cyclic smoothing and weekly shrinkage reduce sparse-bin noise. Deseasonalized EWMA updates after each target is observed. A forecast never uses its own target or later observations. These are historical reconstructed forecasts, not a prospective live experiment.</p>
<p>The hourly forecast bins are 15 minutes wide, unlike the 60-bin descriptive minute-of-hour fold. The video’s exact model, horizon, baseline and dataset are unknown, so this is an independent test of the idea, not an exact replication of its claimed 25% gain.</p>
{qatext}<h2>Limits</h2><p>One exchange, one instrument, one test year. BTCUSDT spot is not BTCUSD on MT5 or a perpetual contract; the study does not causally attribute spikes to funding. Absolute-return seasonality and future directional profitability are different claims. No transaction-cost or strategy P&amp;L test was requested or performed. Any trading filter requires a separate frozen out-of-sample test.</p>
<p>Data: <a href="https://github.com/binance/binance-public-data">Binance official archive documentation</a>. Research context: <a href="https://arxiv.org/abs/2109.12142">Periodicity in Cryptocurrency Volatility and Liquidity</a>.</p>
<p>Saved evidence: <a href="RESULTS.json">Results JSON</a> · <a href="PROTOCOL.txt">Frozen protocol</a> · <a href="DATA MANIFEST.json">Verified source manifest</a> · <a href="FORECASTS.csv.gz">Every forecast and realized target</a> · <a href="PERIOD SEARCH.json">Full period search</a>.</p>
<p>Protocol SHA256: <code>{r['protocol_sha256']}</code><br>Forecast file SHA256: <code>{r['forecast_sha256']}</code></p></main></html>'''
    (ROOT/'Results.html').write_text(doc,encoding='utf-8')
    print('REPORT READY',ROOT/'Results.html')


if __name__=='__main__':main()
