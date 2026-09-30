"""Evidence-backed side-by-side report; never changes trading or website state."""
from __future__ import annotations
import datetime as dt
import gzip
import json
from pathlib import Path
import native_engine as e

ROOT=e.ROOT
SYMBOLS=['USTEC','XAUUSD','XAGUSD','BTCUSD','ETHUSD','EURUSD','USDJPY','GBPJPY']
NAMES={'POC':'POC bounce','REV':'VA reversal','BRK':'VA breakout','ALL':'3 Way combined'}
TF={1:'M1',3:'M3',5:'M5',15:'M15',30:'M30',16385:'H1',16388:'H4'}

def decode(path):
    b=gzip.decompress(path.read_bytes())
    return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')

def streaks(pnls):
    mw=ml=w=l=0
    for pnl in pnls:
        if pnl>0: w+=1; l=0; mw=max(mw,w)
        elif pnl<0: l+=1; w=0; ml=max(ml,l)
        else: w=l=0
    return dict(max_win_streak=mw,max_loss_streak=ml)

def raw(symbol,variant):
    folder=e.q.RAW/'native'/f'3wvp-{symbol}-{variant}-1y'
    original=json.loads((folder/'run.json').read_text())
    trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
    trades.sort(key=lambda t:t['close_time'])
    text=decode(next(folder.glob('*.htm.gz')))
    m=original['metrics'].copy()
    m['relative_equity_dd_pct']=e.h._number(e.h._metric(text,'Equity Drawdown Relative'))
    m['win_rate_pct']=100*sum(t['net_profit']>0 for t in trades)/max(1,len(trades))
    m['trades']=len(trades)
    gains=sum(max(0,t['net_profit']) for t in trades)
    losses=-sum(min(0,t['net_profit']) for t in trades)
    m['profit_factor']=gains/losses if losses else 100 if gains else 0
    m.update(streaks([t['net_profit'] for t in trades]))
    m['trades_per_week']=len(trades)/(365/7)
    m['history_quality']=original['metrics']['history_quality']
    return m

def normalize(result,folder):
    m=result['metrics'].copy(); p=result['position_metrics']
    m.update({k:p[k] for k in ['trades','win_rate_pct','profit_factor','net_profit']})
    m['relative_equity_dd_pct']=p['equity_dd_pct']
    positions=json.loads((folder/'positions.json').read_text())
    m.update(streaks([x['pnl'] for x in positions]))
    m['trades_per_week']=p['trades']/(365/7)
    m['exit_legs']=result['metrics']['trades']
    m['order_warning_count']=len(result['failures'])
    return m

def settings(p):
    modes={
      'entry':['market','closed-bar confirmation','0.25 ATR limit','asset-fixed limit','signal breakout stop'],
      'stop':['raw structure','ATR distance','price %','fixed price','signal extreme','5-bar swing'],
      'trail':['none','break-even','ATR','price %','EMA50','swing','chandelier','step-lock'],
      'exit':['fixed RR','no TP','next profile level','24-bar exit','session exit','partial 1R + trail'],
      'session':['full day','00-08 UTC','07-16 UTC','NY 09:30-16','12-16 UTC','NY 09:30-11'],
      'direction':['both','long only','short only'],
      'filter':['none','EMA slope','H1 EMA','ADX20','DI alignment','ATR percentile','spread/ATR'],
      'day':['all days','skip Monday','skip Friday','skip Mon+Fri'],
    }
    out={k:(modes[k][int(v)] if k in modes else TF.get(v,str(v)) if k=='tf' else v) for k,v in p.items()}
    return '; '.join(f'{k}={v}' for k,v in out.items())

def build():
    rows=[]
    for symbol in SYMBOLS:
        path=ROOT/f'confirmed-{symbol}.json'
        if not path.exists(): continue
        for c in json.loads(path.read_text()):
            variant=c['variant']; r=raw(symbol,variant)
            opt=normalize(c['last_year'],e.OUT/(symbol+'-'+variant+'-last-year'))
            val=normalize(c['validation'],e.OUT/(symbol+'-'+variant+'-validation-confirm'))
            rows.append(dict(symbol=symbol,variant=variant,raw=r,optimized=opt,validation=val,
                validation_qualified=c['validation_qualified'],parameters=c['last_year']['parameters'],
                stability=c['selection']['stability'],development_passes=c['passes'],unique_vectors=c['unique'],
                comparison_return_delta_pp=opt['return_pct']-r['return_pct']))
    e.dump(ROOT/'RESULTS.json',rows)
    lines=['# 3 Way Volume Profile — all 32 side by side','',
      f'Confirmed {len(rows)}/32 combinations. As of {e.h.now()}.','',
      '**Comparison: 26 Sep 2025–25 Sep 2026, $10,000 starting balance per independent test, target 1% equity risk.**',
      'These are independent strategy tests, NOT a portfolio running all EAs concurrently. Native MT5 Model 4, '
      'historical spread/costs and configured 150 ms execution delay. Earlier ticks can be generated; no claim of full real-tick coverage.',
      '', 'Parameters selected on older development/validation data, never on this comparison year. '
      'The last-year raw study was already observed, so this is not pristine out-of-sample evidence. '
      'No settings have been deployed.','',
      'Whole-position win rate/PF/trade count aggregate partial exits. Equity DD is maximum RELATIVE equity drawdown. '
      'Risk uses the original lot rounding UP; the effective risk can exceed 1%.','']
    for symbol in SYMBOLS:
        group=[r for r in rows if r['symbol']==symbol]
        if not group: continue
        lines += [f'## {symbol} — raw → optimized','',
          '| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |',
          '|---|---:|---:|---:|---:|---:|---:|---|---|']
        for r in group:
            a,b=r['raw'],r['optimized']
            lines.append(f"| {NAMES[r['variant']]} | {a['return_pct']:+.2f}% → {b['return_pct']:+.2f}% | "
              f"${a['net_profit']:,.2f} → ${b['net_profit']:,.2f} | {a['profit_factor']:.2f} → {b['profit_factor']:.2f} | "
              f"{a['win_rate_pct']:.1f}% → {b['win_rate_pct']:.1f}% | {a['trades']} → {b['trades']} | "
              f"{a['relative_equity_dd_pct']:.2f}% → {b['relative_equity_dd_pct']:.2f}% | "
              f"{a['max_win_streak']}/{a['max_loss_streak']} → {b['max_win_streak']}/{b['max_loss_streak']} | "
              f"{'PASS' if r['validation_qualified'] else 'FAIL'} |")
        lines.append('')
    lines += ['## Older validation and search depth','',
      'Validation window: 26 Sep 2024–25 Sep 2025. Pass requires positive P/L, whole-position PF ≥1.15, '
      '≥30 positions and relative equity DD ≤20%. A failed validation remains a failed candidate even if its latest-year result looks good.','',
      '| Asset / setup | Validation return | PF | Positions | DD | Development passes / unique vectors | Profitable nearby settings |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        v=r['validation']; s=r['stability']
        lines.append(f"| {r['symbol']} {NAMES[r['variant']]} | {v['return_pct']:+.2f}% | {v['profit_factor']:.2f} | "
          f"{v['trades']} | {v['relative_equity_dd_pct']:.2f}% | {r['development_passes']} / {r['unique_vectors']} | "
          f"{100*s['profitable_neighbor_fraction']:.1f}% |")
    lines += ['', '## Selected settings (research only)', '',
              'Search is staged with two survivors per step, not an exhaustive Cartesian grid. '
              'A saved selected configuration is not approval to trade it.']
    for r in rows:
        lines += ['',f"### {r['symbol']} — {NAMES[r['variant']]}",'',settings(r['parameters'])]
    lines += ['', '## Limitations and evidence','',
      '- Only one later comparison year; selection bias remains across 32 strategies and thousands of trials.',
      '- Original profiles use broker tick volume, not centralized exchange transaction volume.',
      '- Development uses M1 OHLC, which can favor intrabar stop/target/trailing behavior. Native Model 4 confirmation may reverse rankings.',
      '- No independent holdout, extra cost stress or Monte Carlo promotion approval is implied.',
      '- These runs use the isolated historical Exness research binding, not FTMO Swing margin/rules.',
      '- Spread and configured delay are modeled; execution quality during news is not guaranteed by a backtest.',
      '- All 32 raw references have separate parity evidence. Source, compiled binary, inputs, native reports and journals are under `native/`.',
      '- `positions.json` contains exact MT5 position-ID cash ledgers for final runs; commissions, fees and swap reconcile to native net P/L.',
      '- No live terminals, orders, BATs, production EAs, website data or deployment settings were changed.','']
    (ROOT/'SIDE BY SIDE.md').write_text('\n'.join(lines),encoding='utf-8')
    return rows

def plot():
    rows=build()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,4,figsize=(18,9),layout='constrained')
    for symbol,ax in zip(SYMBOLS,axes.flat):
        group=[r for r in rows if r['symbol']==symbol]
        if not group: ax.set_title(symbol+' — pending'); continue
        x=np.arange(len(group)); rawv=[r['raw']['return_pct'] for r in group]; optv=[r['optimized']['return_pct'] for r in group]
        a=ax.bar(x-.18,rawv,.36,color='#8493a5',label='Raw')
        b=ax.bar(x+.18,optv,.36,color='#087f8c',label='Optimized')
        ax.axhline(0,color='#444',lw=.7)
        ax.set_xticks(x,[r['variant'] for r in group]); ax.set_title(symbol,weight='bold')
        ax.set_ylabel('Return (%)'); ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
        ax.bar_label(a,fmt='%.1f',padding=3,fontsize=8); ax.bar_label(b,fmt='%.1f',padding=3,fontsize=8)
        lo=min(rawv+optv+[0]); hi=max(rawv+optv+[0]); gap=max(hi-lo,1)
        ax.set_ylim(lo-gap*.17,hi+gap*.23)
    axes.flat[0].legend(loc='upper left',fontsize=8)
    fig.suptitle('3 Way Volume Profile: all 32 comparisons\n26 Sep 2025–25 Sep 2026 • $10,000 • target 1% risk • independent tests',fontsize=15,weight='bold')
    fig.supxlabel('POC = bounce  |  REV = reversal  |  BRK = breakout  |  ALL = combined\nResearch only. Historical/generated tick mix. Selected on older data; not a future-performance promise.',fontsize=10)
    fig.savefig(ROOT/'side-by-side.png',dpi=170)
    plt.close(fig)

if __name__=='__main__':
    plot()
