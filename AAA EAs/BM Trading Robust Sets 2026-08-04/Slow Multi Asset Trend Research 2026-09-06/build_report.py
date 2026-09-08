"""Build the honest evidence report, graphs, portfolio and Monte Carlo summaries."""
from pathlib import Path
from datetime import datetime
import csv,json,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT=Path(__file__).resolve().parent
SYMBOLS=('XAUUSD','XAGUSD','BTCUSD','ETHUSD','USTEC','US30','EURUSD','GBPJPY')
KEEP=('XAUUSD','US30')

def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def native(symbol,stage='test',label='selected',model=None):
    if model is None:model=0 if stage=='test' else 1
    p=ROOT/'Native'/f'{symbol.lower()}-{label}-{stage}-model{model}'/'result.json'
    return json.loads(p.read_text())
def trades(symbol):return json.loads((ROOT/'Native'/f'{symbol.lower()}-selected-test-model0'/'trades.json').read_text())

def stats_from_returns(items,risk_scale=1.0):
    if not items:return dict(return_pct=0,profit_factor=0,win_rate=0,max_dd_pct=0,trades=0,sharpe=0,recovery=0,final_balance=10000)
    rs=np.array([x['return_fraction']*risk_scale for x in items]);curve=10000*np.cumprod(1+rs);full=np.r_[10000,curve];pnl=np.diff(full)
    loss=-pnl[pnl<0].sum();pf=pnl[pnl>0].sum()/loss if loss else 99.;dd=np.max(1-full/np.maximum.accumulate(full))*100;ret=(curve[-1]/10000-1)*100
    idx=pd.to_datetime([x['exit_time'] for x in items],utc=True);daily=pd.Series(rs,index=idx).groupby(level=0).sum().resample('1D').sum();sd=daily.std(ddof=1);sh=float(daily.mean()/sd*math.sqrt(252)) if sd>0 else 0
    return dict(return_pct=float(ret),profit_factor=float(min(99,pf)),win_rate=float(np.mean(rs>0)*100),max_dd_pct=float(dd),trades=len(rs),sharpe=sh,recovery=float(ret/dd if dd else 0),final_balance=float(curve[-1]),avg_trade_pct=float(rs.mean()*100),avg_win_pct=float(rs[rs>0].mean()*100 if np.any(rs>0) else 0),avg_loss_pct=float(rs[rs<0].mean()*100 if np.any(rs<0) else 0))

def portfolio(symbols):
    candidates=[]
    for symbol in symbols:
        for t in trades(symbol):candidates.append(dict(t,symbol=symbol))
    # The selected basket only has two markets, so the four-position cap cannot bind;
    # the implementation remains explicit for reproducibility.
    candidates.sort(key=lambda x:x['entry_time']);accepted=[];open_exits=[]
    for t in candidates:
        when=pd.Timestamp(t['entry_time']);open_exits=[x for x in open_exits if x>when]
        if len(open_exits)>=4:continue
        accepted.append(t);open_exits.append(pd.Timestamp(t['exit_time']))
    accepted.sort(key=lambda x:x['exit_time'])
    return accepted,stats_from_returns(accepted)

def monte_carlo(items,paths=10000,seed=20260906):
    r=np.array([x['return_fraction'] for x in items]);rng=np.random.default_rng(seed);block=5;n=len(r)
    starts=rng.integers(0,n,size=(paths,(n+block-1)//block));ix=(starts[:,:,None]+np.arange(block))%n;sample=r[ix.reshape(paths,-1)[:,:n]]
    curves=np.ones((paths,n+1))*10000;curves[:,1:]=10000*np.cumprod(1+sample,axis=1)
    ends=(curves[:,-1]/10000-1)*100;dd=np.max(1-curves/np.maximum.accumulate(curves,axis=1),axis=1)*100
    return curves,dict(paths=paths,return_p5=float(np.percentile(ends,5)),return_median=float(np.median(ends)),return_p95=float(np.percentile(ends,95)),dd_median=float(np.median(dd)),dd_p95=float(np.percentile(dd,95)),profitable_probability_pct=float(np.mean(ends>0)*100),loss_probability_pct=float(np.mean(ends<0)*100))

def money(x):return f"{x:+.2f}%"
def main():
    charts=ROOT/'Charts';charts.mkdir(exist_ok=True)
    locked={s:native(s) for s in SYMBOLS};full={s:native(s,'full') for s in SYMBOLS};baseline={s:native(s,'test','baseline') for s in SYMBOLS}
    wf=json.loads((ROOT/'walk-forward.json').read_text());selection=json.loads((ROOT/'selection-lock.json').read_text())
    rows=[]
    decisions={'XAUUSD':'Demo candidate','XAGUSD':'Watch only: 6 trades / high DD','BTCUSD':'Reject','ETHUSD':'Reject: 1/4 positive WF folds','USTEC':'Reject','US30':'Demo only: high DD at 1%','EURUSD':'Reject','GBPJPY':'Reject'}
    for s in SYMBOLS:
        r=locked[s];f=full[s]
        rows.append(dict(symbol=s,decision=decisions[s],locked_return=r['return_pct'],locked_pf=r['profit_factor'],locked_win_rate=r['win_rate'],locked_equity_dd=r['equity_dd_pct'],locked_trades=r['trades'],locked_sharpe=r['sharpe_ratio'],locked_recovery=r['recovery_factor'],full_return=f['return_pct'],full_pf=f['profit_factor'],full_win_rate=f['win_rate'],full_equity_dd=f['equity_dd_pct'],full_trades=f['trades'],wf_positive_folds=wf[s]['positive_folds'],wf_folds=4,wf_compounded_return=wf[s]['compounded_test_return_pct']))
    pd.DataFrame(rows).to_csv(ROOT/'native-summary.csv',index=False)
    # Native asset comparison.
    x=np.arange(len(SYMBOLS));fig,ax=plt.subplots(2,1,figsize=(13,8),constrained_layout=True)
    ax[0].bar(x,[locked[s]['return_pct'] for s in SYMBOLS],color=['#22a879' if locked[s]['return_pct']>0 else '#d95f5f' for s in SYMBOLS]);ax[0].axhline(0,color='black',lw=.7);ax[0].set_ylabel('Locked-year return %');ax[0].set_xticks(x,SYMBOLS)
    ax[1].bar(x,[locked[s]['equity_dd_pct'] for s in SYMBOLS],color='#c47a34');ax[1].set_ylabel('MT5 equity drawdown %');ax[1].set_xticks(x,SYMBOLS)
    fig.suptitle('Frozen settings — native MT5 locked-year evidence');fig.savefig(charts/'native-locked-summary.png',dpi=150);plt.close(fig)
    # Eight selected balance curves.
    fig,axes=plt.subplots(4,2,figsize=(14,13),constrained_layout=True)
    for ax,s in zip(axes.flat,SYMBOLS):
        r=locked[s];series=r['series'];dates=[datetime.fromisoformat(p['date']) for p in series];vals=[p['balance'] for p in series]
        ax.step(dates,vals,where='post',color='#18a878' if r['return_pct']>0 else '#cc5c5c');ax.axhline(10000,color='gray',lw=.6);ax.grid(alpha=.2);ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        ax.set_title(f"{s}: {r['return_pct']:+.1f}% | PF {r['profit_factor']:.2f} | WR {r['win_rate']:.1f}% | DD {r['equity_dd_pct']:.1f}% | n={r['trades']}")
    fig.savefig(charts/'native-locked-equity-curves.png',dpi=150);plt.close(fig)
    # Walk-forward heatmap.
    matrix=np.array([[f['test']['return_pct'] for f in wf[s]['folds']] for s in SYMBOLS]);fig,ax=plt.subplots(figsize=(10,6),constrained_layout=True);im=ax.imshow(matrix,cmap='RdYlGn',aspect='auto',vmin=-max(10,np.nanpercentile(abs(matrix),85)),vmax=max(10,np.nanpercentile(abs(matrix),85)))
    ax.set_xticks(range(4),['2024-09→2025-03','2025-03→09','2025-09→2026-03','2026-03→09']);ax.set_yticks(range(len(SYMBOLS)),SYMBOLS)
    for i in range(len(SYMBOLS)):
        for j in range(4):ax.text(j,i,f'{matrix[i,j]:+.1f}%',ha='center',va='center',fontsize=8,color='black')
    ax.set_title('Rolling walk-forward test returns (settings re-selected from prior year)');fig.colorbar(im,ax=ax,label='Return %');fig.savefig(charts/'walk-forward-heatmap.png',dpi=150);plt.close(fig)
    # Combined research-candidate basket.
    items,pstats=portfolio(KEEP);curve=10000*np.cumprod(1+np.array([x['return_fraction'] for x in items]));dates=pd.to_datetime([x['exit_time'] for x in items]);peak=np.maximum.accumulate(np.r_[10000,curve]);dd=(1-np.r_[10000,curve]/peak)*100
    fig,ax=plt.subplots(2,1,figsize=(12,8),sharex=True,constrained_layout=True);ax[0].step(dates,curve,where='post',color='#18a878');ax[0].axhline(10000,color='gray',lw=.6);ax[0].set_ylabel('Closed balance USD');ax[0].set_title('XAUUSD + US30 candidate basket — locked year, 1% per trade');ax[0].grid(alpha=.2)
    ax[1].fill_between([dates[0]]+list(dates),dd,color='#cc5555',alpha=.45);ax[1].set_ylabel('Closed-balance DD %');ax[1].grid(alpha=.2);fig.savefig(charts/'candidate-portfolio.png',dpi=150);plt.close(fig)
    curves,mc=monte_carlo(items);lo,q25,med,q75,hi=np.percentile(curves,[5,25,50,75,95],axis=0);fig,ax=plt.subplots(figsize=(11,5),constrained_layout=True);xx=np.arange(len(lo));ax.fill_between(xx,lo,hi,color='#3c75aa',alpha=.18,label='5–95%');ax.fill_between(xx,q25,q75,color='#3c75aa',alpha=.3,label='25–75%');ax.plot(xx,med,color='white',lw=1.5,label='Median');ax.set(title='Candidate basket: 10,000 five-trade block-bootstrap paths',xlabel='Closed trade',ylabel='USD balance');ax.grid(alpha=.15);ax.legend();fig.patch.set_facecolor('#101820');ax.set_facecolor('#101820');ax.tick_params(colors='white');ax.xaxis.label.set_color('white');ax.yaxis.label.set_color('white');ax.title.set_color('white');fig.savefig(charts/'candidate-monte-carlo.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
    risk=[dict(risk_percent=r,**stats_from_returns(items,r)) for r in (.5,1.,1.5)];stress_items=[dict(x,return_fraction=x['return_fraction']-.0005) for x in items];stress=stats_from_returns(stress_items)
    dump(ROOT/'portfolio-summary.json',dict(included=list(KEEP),excluded=[s for s in SYMBOLS if s not in KEEP],locked= pstats,monte_carlo=mc,risk_sensitivity=risk,additional_cost_stress_0_05pct_per_trade=stress,trades=items))
    # Configuration scatter from the complete screen.
    screen=pd.read_csv(ROOT/'all-screen-results.csv');d=screen[screen.stage=='development'];fig,ax=plt.subplots(figsize=(11,6),constrained_layout=True);sc=ax.scatter(d.max_dd_pct,d.return_pct,c=np.clip(d.profit_factor,0,3),s=8+np.sqrt(np.maximum(d.trades,0))*2,cmap='viridis',alpha=.55);ax.axhline(0,color='gray',lw=.6);ax.set(xlabel='M15 mark-to-market drawdown %',ylabel='Development return %',title=f'All {len(d):,} development-stage configuration evaluations');fig.colorbar(sc,ax=ax,label='Profit factor (capped at 3)');fig.savefig(charts/'all-configurations.png',dpi=150);plt.close(fig)
    fields=['symbol','decision','locked_return','locked_pf','locked_win_rate','locked_equity_dd','locked_trades','locked_sharpe','locked_recovery','full_return','full_pf','full_win_rate','full_equity_dd','full_trades','wf_positive_folds','wf_compounded_return']
    lines=['# Step 3 — Slow Multi-Asset Trend Basket','',
      '**Decision: retain XAUUSD and US30 as demo-forward-test candidates only. Do not add this strategy to the live/recommended portfolio yet.** XAU has the cleanest locked result. US30 is weaker in its single locked year but is the only market with four positive rolling walk-forward folds. XAG is too sparse and suffers high open-equity drawdown; the other five markets fail robustness or the locked year.','',
      '## Native MT5 locked-year results','',
      'Frozen settings were tested from 2025-09-01 through 2026-09-01 on the isolated Exness demo terminal using generated Every Tick, random execution delay, broker spread, commission and swap. Risk is hard-locked at 1% of current equity. History quality is 99–100%.','',
      '| Asset | Decision | Return | PF | Win rate | Equity DD | Trades | Sharpe | Recovery | WF positive folds |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['symbol']} | {r['decision']} | {r['locked_return']:+.2f}% | {r['locked_pf']:.2f} | {r['locked_win_rate']:.2f}% | {r['locked_equity_dd']:.2f}% | {r['locked_trades']} | {r['locked_sharpe']:.2f} | {r['locked_recovery']:.2f} | {r['wf_positive_folds']}/4 |")
    lines+=['','![Native locked-year summary](Charts/native-locked-summary.png)','','![Native locked-year equity curves](Charts/native-locked-equity-curves.png)','','## Frozen configurations','',
      '| Asset | TF | Momentum | Trend | Direction | Entry | Stop | Exit | Management |','|---|---|---|---|---|---|---|---|---|']
    stop={0:'ATR',1:'swing',2:'chandelier'};exitn={0:'signal reversal',1:'fixed RR',2:'adaptive RR',3:'time'};manage={0:'none',1:'breakeven',2:'ATR trail',3:'chandelier trail',4:'M15 50→20 dynamic stop'}
    for s in SYMBOLS:
        c=selection[s]['config'];exit_label=f"{c['rr']:g}R" if c['exit_mode']==1 else (f"{c['max_hold_days']} days" if c['exit_mode']==3 else exitn[c['exit_mode']])
        lines.append(f"| {s} | {c['tf']} | {c['horizon']} | {c['trend']} | {c['direction']} | {c['session']} | {stop[c['stop_mode']]} / {c['stop_atr']:g} ATR floor | {exit_label} | {manage[c['manage']]} |")
    lines+=['','## Rolling walk-forward','',
      'Each fold re-selected a configuration using only the preceding one-year window, then traded the next six months. This is a stronger stability check than the single frozen split. The candidate grid was fixed in advance.','',
      '| Asset | Positive folds | Compounded four-fold return | Test trades |','|---|---:|---:|---:|']
    for s in SYMBOLS:lines.append(f"| {s} | {wf[s]['positive_folds']}/4 | {wf[s]['compounded_test_return_pct']:+.2f}% | {wf[s]['total_test_trades']} |")
    lines+=['','![Walk-forward test heatmap](Charts/walk-forward-heatmap.png)','','## Three-year native context (not out-of-sample)','',
      'These M1-OHLC native runs include the development sample. They describe behavior and costs but must not be presented as independent validation.','',
      '| Asset | Return | PF | Win rate | Equity DD | Trades |','|---|---:|---:|---:|---:|---:|']
    for s in SYMBOLS:lines.append(f"| {s} | {full[s]['return_pct']:+.2f}% | {full[s]['profit_factor']:.2f} | {full[s]['win_rate']:.2f}% | {full[s]['equity_dd_pct']:.2f}% | {full[s]['trades']} |")
    lines+=['','## Candidate basket: XAUUSD + US30','',
      f"Applying the standalone net trade returns chronologically at 1% risk produced {pstats['return_pct']:+.2f}% closed-balance return, PF {pstats['profit_factor']:.2f}, {pstats['win_rate']:.2f}% wins, {pstats['max_dd_pct']:.2f}% closed-balance DD, {pstats['trades']} trades, Sharpe {pstats['sharpe']:.2f} and recovery {pstats['recovery']:.2f}. This reconstructed portfolio DD excludes synchronized intratrade equity and should not replace the larger standalone MT5 equity-DD numbers above.",'',
      f"Monte Carlo (10,000 five-trade block bootstraps): median return {mc['return_median']:+.2f}%, P5 {mc['return_p5']:+.2f}%, P95 {mc['return_p95']:+.2f}%, median DD {mc['dd_median']:.2f}%, DD P95 {mc['dd_p95']:.2f}%, profitable paths {mc['profitable_probability_pct']:.2f}%.",'',
      f"Adding 0.05% extra account cost to every trade changes the reconstructed return to {stress['return_pct']:+.2f}% and PF to {stress['profit_factor']:.2f}.",'',
      'Risk sensitivity is included for research, but the EA and all reported primary tests remain fixed at 1%.','',
      '| Risk/trade | Return | PF | Win rate | Closed DD | Trades |','|---:|---:|---:|---:|---:|---:|']
    for r in risk:lines.append(f"| {r['risk_percent']:.1f}% | {r['return_pct']:+.2f}% | {r['profit_factor']:.2f} | {r['win_rate']:.2f}% | {r['max_dd_pct']:.2f}% | {r['trades']} |")
    lines+=['','![Candidate portfolio](Charts/candidate-portfolio.png)','','![Candidate Monte Carlo](Charts/candidate-monte-carlo.png)','','## Evidence limitations','',
      '- XAUUSD produced a real-tick comparison, but MT5 reported only 66% history quality. Its partial result (+32.49%, PF 2.21, 31.58% wins, 9.46% DD, 38 trades) is corroborative only—not the primary full-year result.','- XAGUSD and US30 real-tick synchronization did not finish within the five-minute safety bounds. ETH/BTC real ticks were already unavailable in the immediately preceding pairs study, so no fresh real-tick claim is made.','- The broad screen uses recorded M15 bid OHLC and spread floors plus conservative friction; native MT5 results supersede screen estimates.','- Session labels use the research terminal clock. They must be remapped if a broker uses a different server offset.','- The fixed 1% risk produced 23.33% native equity DD on US30. Because risk must remain at 1%, US30 stays in demo rather than weakening the risk rule to make it look safer.','- Backtests and Monte Carlo are not forecasts or guarantees.','',
      '## Files','',
      '- `native-summary.csv`: final per-market table.','- `all-screen-results.csv`: every development configuration result.','- `selection-lock.json`: frozen inputs selected before the corrected validation pass.','- `walk-forward.json`: fold-by-fold re-selection and tests.','- `portfolio-summary.json`: reconstructed basket trades, stress and Monte Carlo summary.','- `EA/Calyx Slow Trend EA.mq5`: tester-only EA; it refuses normal live-chart initialization.','',
      '![All configuration evaluations](Charts/all-configurations.png)']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    dump(ROOT/'summary.json',dict(protocol='development 2023-09-01..2025-09-01; locked test 2025-09-01..2026-09-01',risk_percent=1.0,decision='demo candidates only; no production change',recommended_demo_candidates=list(KEEP),native=rows,portfolio=pstats,monte_carlo=mc,risk_sensitivity=risk,cost_stress=stress,real_tick_note='XAU partial 66%; XAG and US30 timed out; no complete real-tick validation'))
    dump(ROOT/'progress.json',dict(step=3,title='Slow Multi-Asset Trend Basket',status='complete',screens=len(pd.read_csv(ROOT/'all-screen-results.csv')),native_locked_runs=16,native_full_runs=8,walk_forward_folds=32,monte_carlo_paths=10000,production_changed=False,recommendation='XAUUSD and US30 demo forward test only'))
    print('REPORT COMPLETE',pstats,mc,flush=True)

if __name__=='__main__':main()
