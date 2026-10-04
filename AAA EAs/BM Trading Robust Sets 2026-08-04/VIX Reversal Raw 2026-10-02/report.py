from pathlib import Path
import base64,html,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
BG='#091713';FG='#e9f5ef';GRID='#29443a';COLORS=['#79f2cd','#f3be68','#75a4ff','#dc93e4']

def read(name):return json.loads((ROOT/name).read_text())
def fmt(x,n=2):return '—' if x is None else f'{x:.{n}f}'
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def theme(axes):
    for ax in np.ravel(axes):
        ax.set_facecolor(BG);ax.tick_params(colors=FG);ax.xaxis.label.set_color(FG);ax.yaxis.label.set_color(FG);ax.title.set_color(FG);ax.grid(alpha=.4,color=GRID)
        for spine in ax.spines.values():spine.set_color(GRID)
def image(name):return '<img alt="VIX research '+html.escape(name)+'" src="data:image/png;base64,'+base64.b64encode((ROOT/name).read_bytes()).decode()+'">'

def main():
    rows=read('SUMMARY.json');controls=read('CONTROLS.json');boot=read('BOOTSTRAP.json');decision=read('DECISION.json');verification=read('VERIFICATION.json');lock=read('DATA LOCK.json')
    raw={x['window']:x for x in rows if x['execution_bps_each_side']==0};windows=['5y','3y','1y','6m']
    fig,axes=plt.subplots(2,1,figsize=(13,8),facecolor=BG,sharex=True);theme(axes)
    for w,color in zip(windows,COLORS):
        e=pd.read_csv(ROOT/'runs'/f'{w}-gross'/'equity.csv',parse_dates=['date']);dates=pd.concat([pd.Series([pd.Timestamp(raw[w]['start'])]),e.date],ignore_index=True);eq=np.r_[10000,e.equity.to_numpy()];peak=np.maximum.accumulate(eq)
        axes[0].plot(dates,eq,color=color,label=w+' gross',lw=1.6);axes[1].fill_between(dates,100*(eq/peak-1),0,color=color,alpha=.10);axes[1].plot(dates,100*(eq/peak-1),color=color,lw=1)
    axes[0].set_title('VIX confirmed reversal → long SVXY | independently reset $10,000 cash accounts');axes[0].set_ylabel('Daily-close account equity ($)');axes[1].set_ylabel('Daily-close equity drawdown (%)');axes[0].legend(facecolor=BG,labelcolor=FG,edgecolor=GRID);fig.tight_layout();fig.savefig(ROOT/'vix-equity.png',dpi=145);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,4.8),facecolor=BG);theme(axes)
    for ax,w in zip(axes,['5y','3y']):
        c=pd.read_csv(ROOT/f'CONTROL-{w}.csv');ax.hist(c.return_pct,bins=35,color='#527f70',alpha=.9);ax.axvline(raw[w]['return_pct'],color=COLORS[0],lw=2,label='VIX model');ax.axvline(controls[w]['random_return_p95'],color=COLORS[1],ls='--',label='Random p95');ax.set_title(w+' matched random-entry diagnostic');ax.set_xlabel('Gross return (%)');ax.set_ylabel('Schedules (1,000)');ax.legend(facecolor=BG,labelcolor=FG,edgecolor=GRID)
    fig.tight_layout();fig.savefig(ROOT/'vix-controls.png',dpi=145);plt.close(fig)
    stats=table(['Window','Return','PF','Win rate','Close equity DD','OHLC assumed-path DD','Trades','Trades/month','Trades/session','Sharpe','Max W/L'],[[w,fmt(raw[w]['return_pct'])+'%',fmt(raw[w]['pf'],3),fmt(raw[w]['win_rate_pct'],1)+'%',fmt(raw[w]['max_close_equity_dd_pct'])+'%',fmt(raw[w]['assumed_path_intraday_dd_pct'])+'%',raw[w]['trades'],fmt(raw[w]['trades_per_month'],3),fmt(raw[w]['trades_per_session'],4),fmt(raw[w]['sharpe_daily_252']),f"{int(raw[w]['max_win_streak'])}/{int(raw[w]['max_loss_streak'])}"] for w in windows])
    annual=table(['Annual start → end','Return','PF','Win rate','Trades','Max W/L'],[[r['start']+' → '+str(pd.Timestamp(r['end_exclusive'])-pd.Timedelta(days=1))[:10],fmt(r['return_pct'])+'%',fmt(r['pf'],3),fmt(r['win_rate_pct'],1)+'%',r['trades'],f"{int(r['max_win_streak'])}/{int(r['max_loss_streak'])}"] for k,r in raw.items() if k.startswith('annual')])
    costs=table(['Window','Gross return','5 bps/side (illustrative)','10 bps/side (illustrative)'],[[w,fmt(raw[w]['return_pct'])+'%']+[fmt(next(r for r in rows if r['window']==w and r['execution_bps_each_side']==c)['return_pct'])+'%' for c in [5,10]] for w in windows])
    ct=table(['Window','Observed return','Random median','Random p95','Above p95?','Rank tail fraction'],[[w,fmt(raw[w]['return_pct'])+'%',fmt(controls[w]['random_return_median'])+'%',fmt(controls[w]['random_return_p95'])+'%',str(controls[w]['observed_above_random_p95']),fmt(controls[w]['random_ge_observed_fraction_plus_one'],3)] for w in ['5y','3y']])
    bt=table(['Window','Block-bootstrap return p05','Median return','PF p05'],[[w,fmt(boot[w]['return_p05_pct'])+'%',fmt(boot[w]['return_median_pct'])+'%',fmt(boot[w]['pf_p05'],3)] for w in ['5y','3y']])
    gate=table(['Window','Positive','PF ≥1.15','≥30 trades','Above random p95'],[[w]+[str(v) for v in decision['gates'][w].values()] for w in ['5y','3y']])
    # Buy-and-hold context is deliberately not included in the same-risk gate.
    d=pd.read_csv(ROOT/'data/joined.csv',parse_dates=['date']).set_index('date');buyhold=[]
    for w in windows:
        z=d[d.index>=raw[w]['start']];q=int(10000//z.open.iloc[0]);cash=10000-q*z.open.iloc[0];e=cash+q*z.close.to_numpy();peak=np.maximum.accumulate(np.r_[10000,e])[1:]
        buyhold.append([w,fmt((e[-1]/10000-1)*100)+'%',fmt(np.max((peak-e)/peak)*100)+'%',q])
    bh=table(['Window','Buy-and-hold return','Close DD','Cash-funded shares'],buyhold)
    limits=[
      'One frozen daily interpretation, not a published rule set or proof that every volatility mean-reversion strategy fails. All thresholds are ours; no optimisation.',
      'VIX >=25 and >=1.25x its PREVIOUS 20-session average arms a five-session window. Confirm a close below the prior low and close; buy SVXY at next session open.',
      'SVXY stop is 2x prior Wilder ATR(14), target 2R; VIX return to the frozen mean or 10 held bars requests next-open exit. One trade at a time; no trailing, pyramiding or short borrowing.',
      'Whole-share sizing floors to 1% closed-balance risk and caps by available cash. Gap losses can exceed the budget. No minimum-lot override; no leverage.',
      'SVXY tracks -0.5x daily short-term VIX FUTURES, not spot VIX. Its roll and fund economics are embedded in ETF prices; do not map these returns to an Exness VIX CFD or futures contract.',
      'Headlines are BEFORE broker commission, spread and slippage. 5/10bps each side are illustrative sensitivity assumptions, not measured costs. No measured-cost gate is passed.',
      'Daily OHLC bars cannot supply 150ms fill simulation, native tick equity DD, order-book liquidity, historical bid/ask costs, or FTMO pass/payout estimates. Exact intraday order is unknown; both-touch bars take SL first.',
      'Close equity DD includes marked open P&L at session closes. OHLC assumed-path DD follows a low-before-high convention and is not exact native equity DD.',
      'Official Cboe VIX replaces connector VIX as predeclared. Three overlapping closes differ by more than 0.02; largest is 2.61 on 6 Feb 2026. Their differences are saved; official observations on non-ETF sessions are omitted from joint-session signals.',
      'The test history has been seen in earlier research. Windows overlap; independent annual resets do not sum or compound to the continuous five-year run. No pristine prospective holdout.',
      'Matched random schedules match count, weekday mix and maximum observed holding-session horizons, with the same stops, targets and risk. VIX-mean exits are replaced with matched time exits in controls. This is a timing diagnostic, not an exact strategy twin.',
      '10,000 circular block-5 risk-unit resamples are historical diagnostics, not forecasts; small sample undermines inference. No future pass or payout probabilities are implied.',
      f"Independent reconstruction verified {verification['total_overlapping_closed_trades_verified']} overlapping closed trades across {len(rows)} runs, plus daily equity and prefix-causal signals. Eleven unit tests passed.",
      'No active EA, broker account, MT5 installation, website, portfolio, or FTMO settings changed for this research. Gold-only BAT policy was committed and pushed separately as 582175546.'
    ]
    verdict='Raw screen failed: insufficient trades and no confirmed edge over matched random timing.' if decision['status']=='RAW GATE FAILED' else 'Raw screen passed only; native execution and measured costs remain unvalidated.'
    content=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx | VIX reversal raw screen</title><style>body{{background:{BG};color:{FG};font:16px/1.6 system-ui;max-width:1350px;margin:auto;padding:32px}}h1{{font-size:42px;line-height:1.15}}h2,a{{color:#79f2cd}}section{{background:#0e211b;border:1px solid {GRID};border-radius:18px;padding:24px;margin:24px 0}}.warning{{border-color:#ac8855}}p,li{{color:#c1d7cf}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:11px;border-bottom:1px solid {GRID};text-align:right;white-space:nowrap}}td:first-child,th:first-child{{text-align:left}}.scroll{{overflow:auto}}img{{width:100%}}code{{color:#f3be68}}</style><body><h1>VIX spike → confirmed reversal</h1><p>Signal: official Cboe VIX. Trade vehicle: long SVXY. Frozen daily-bar screen through 1 October 2026; $10,000 independent cash accounts, 1% planned risk.</p><section class="warning"><h2>{verdict}</h2><p>Only {raw['5y']['trades']} trades in five years. High observed win rate is not proof of a reliable edge. NOT live eligible; no optimisation or deployment.</p></section><section><h2>Raw results — before broker execution costs</h2>{stats}</section><section><h2>Equity and drawdown</h2>{image('vix-equity.png')}</section><section><h2>Independent annual windows</h2>{annual}</section><section><h2>Random-entry control</h2>{ct}{image('vix-controls.png')}</section><section><h2>Raw gates</h2>{gate}<h2>Historical resampling diagnostic</h2>{bt}</section><section><h2>Illustrative cost sensitivity — not measured fees</h2>{costs}</section><section><h2>Buy and hold context — different exposure/risk</h2>{bh}</section><section><h2>Rules, verification and limitations</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in limits)}</ul><p><a href="https://www.proshares.com/our-etfs/strategic/svxy">SVXY issuer: objective and risks</a> · <a href="https://www.cboe.com/tradable-products/vix/vix-historical-data">Cboe VIX historical data</a></p><p><a href="SUMMARY.json">Result ledger</a> · <a href="PROTOCOL.txt">Frozen rules</a> · <a href="VERIFICATION.json">Independent verification</a> · <a href="DECISION.json">Decision</a> · <a href="DATA%20LOCK.json">Source hashes</a></p></section></body></html>'''
    (ROOT/'Results.html').write_text(content,encoding='utf-8')
    text='# VIX confirmed reversal / SVXY — raw daily screen\n\n'+verdict+'\n\n'
    for w in windows:
        r=raw[w];text+=f"{w}: return {r['return_pct']:+.2f}%, PF {fmt(r['pf'],3)}, WR {fmt(r['win_rate_pct'],1)}%, close equity DD {r['max_close_equity_dd_pct']:.2f}%, trades {r['trades']}, max W/L {int(r['max_win_streak'])}/{int(r['max_loss_streak'])}.\n\n"
    text+='\n'.join('- '+x for x in limits)+'\n'
    (ROOT/'REPORT.md').write_text(text,encoding='utf-8');print('Wrote offline results with two embedded graphs.')

if __name__=='__main__':main()
