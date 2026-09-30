from pathlib import Path
import json,zipfile,hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent

def table(rows):
    lines=['| Version / window | Net return | PF | Win rate | Equity DD | Trades | /month | /weekday | W/L streak |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        m=r['metrics'];pf='—' if m['profit_factor'] is None else f"{m['profit_factor']:.3f}"
        label=r['tag'].split('-control-')[0].split('-raw-')[0]+(' control' if r['control'] else '')+' / '+r['window']
        lines.append(f"| {label} | {m['return_pct']:+.2f}% | {pf} | {m['win_rate_pct']:.1f}% | {m['equity_dd_pct']:.2f}% | {m['trades']} | {m['trades_per_month']:.2f} | {m['trades_per_weekday']:.3f} | {m['win_streak']}/{m['loss_streak']} |")
    return '\n'.join(lines)

def main():
    audit=json.loads((R/'AUDIT.json').read_text());cfg=json.loads((R/'run-config.json').read_text());rows=audit['rows']
    by={(r['mode'],r['window'],r['model'],r['control']):r for r in rows}
    gates=[]
    for bot in cfg['bots']:
        reasons=[];overlap=[]
        for w in ['3y','5y']:
            raw=by[bot['mode'],w,4,False];control=by[bot['mode'],w,4,True];m=raw['metrics'];c=control['metrics']
            if m['net_profit']<=0:reasons.append(w+': nonpositive net')
            if (m['profit_factor'] or 0)<1.15:reasons.append(w+': PF below 1.15')
            if m['trades']<30:reasons.append(w+': fewer than 30 trades')
            if m['mean_net_R'] is None or c['mean_net_R'] is None or m['mean_net_R']<=c['mean_net_R']:reasons.append(w+': does not beat direction control mean R')
            if any(raw['flags'].values()) or any(control['flags'].values()):reasons.append(w+': execution/carry flags')
            aa=pd.read_csv(R/'native'/raw['tag']/'signals.csv.gz');bb=pd.read_csv(R/'native'/control['tag']/'signals.csv.gz')
            aset=set(zip(aa.ready,aa.signal_time));bset=set(zip(bb.ready,bb.signal_time))
            overlap.append(dict(window=w,raw_opportunities=len(aset),control_opportunities=len(bset),shared=len(aset&bset)))
        if by[bot['mode'],'1y',4,False]['metrics']['net_profit']<=0:reasons.append('Latest year not positive')
        gates.append(dict(version=bot['name'],passed=not reasons,reasons=reasons,control_overlap=overlap))
    (R/'FINAL GATES.json').write_text(json.dumps(gates,indent=2))
    passed=[g['version'] for g in gates if g['passed']]
    selected=[by[b['mode'],'5y',4,False] for b in cfg['bots']]
    recent=[by[b['mode'],w,4,False] for b in cfg['bots'] for w in ['6m','1y','3y']]
    controls=[r for r in rows if r['model']==4 and r['control'] and r['window']!='smoke']
    screens=[r for r in rows if r['model']==1]
    all_confirm=selected+recent+controls
    report=['# US100 unfilled-FVG exhaustion: raw test',
      '\nVerdict: '+(', '.join(passed)+' passed the raw gate; optimization still requires approval.' if passed else '**No tested version passed the raw gate. Do not promote these settings.**'),
      '\nThe clip is incomplete. Six frozen interpretations were tested: M1/M5/M15 parent setups, each with M1 IFVG or CISD confirmation. Results apply to these explicit rules, not every possible interpretation or the creator’s account. The 72% claim is not independently verified.',
      '\nReturns, profit factors, win rates and streaks below use native closed-position P&L net of commission, swap and fees. Net cash reconciles to each MT5 report. Equity drawdown uses MT5’s native tick-level statistic; it is not inferred from closed trades.',
      '\n## Main five-year results — native MT5 Model 4\n',table(selected),
      '\n## Recent and three-year results — native MT5 Model 4\n',table(recent),
      '\n## What was actually tested\n',
      'USTEC, Exness US Tech 100 CFD, USD10,000 initial balance, 1% equity stop sizing rounded UP, 150ms simulated execution delay, broker-configured commissions and historical spread data. Not NQ futures. Commission settings are not a reconstruction of every historical fee schedule. Windows end 2026-09-27; 5y begins 2021-09-27, 3y 2023-09-27, 1y 2025-09-27, 6m 2026-03-27. A 90-day indicator warm-up adds no trades. Windows overlap and are not untouched holdouts.',
      '\nNY 09:30–15:30 entries, 15:55/time/session exits. Closed-candle displacement and exhaustion, then a later one-minute trigger; target the gap midpoint, equal-distance initial stop. No volume condition is inferred from an OHLC gap. No trailing stop, martingale or optimization. See [frozen rules](RULES.md).',
      '\nTime alignment uses broker GMT+0 with New York daylight-saving conversion; [Exness documents its MetaTrader server timezone here](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader).',
      '\nAn M1 CISD confirmation can lie beyond the target: the original displacement-leg open is commonly below a bullish gap (above a bearish gap). Such setups are rejected; zero/few trades are insufficient evidence, not a winning version. The IFVG must be a distinct eligible gap whose inversion leaves the parent target ahead.',
      '\nNominal 1:1 is measured from the decision quote. Delayed fills, spread, commissions and timed exits alter realized reward/risk. Stops are not guaranteed, and rounding UP can exceed 1% initial risk.',
      '\nIf the simulated account is depleted, margin/minimum-lot constraints can suppress later trades; its full-window trade frequency then understates unconstrained signal frequency. No capital resets were inserted to conceal losses.',
      '\n## Gate decisions\n']
    for g in gates:report.append('- '+g['version']+': '+('PASS' if g['passed'] else '; '.join(g['reasons'])))
    report+=['\n## Audit and execution\n',f"{audit['executed_entry_checks']:,} executed signals passed an independent Python rule check against native saved parent/M1 candles (includes overlapping windows and smoke tests; not independent trades). All completed ledgers reconcile to native report net P&L, position volume and recorded fees. This audits executed entries, not exhaustive candidate discovery.",
      '\nPer-run spread/cost/risk/holding diagnostics:\n']
    report.append('Audit timestamp correction: the signals CSV column named `fill_time` stores the handled-quote time, whereas the deals ledger stores actual execution time. The initial exact-equality assertion was corrected to allow a 0–1 second later deal timestamp under the configured 150ms delay. No earlier fills are allowed; fill prices/position IDs still reconcile. Trading rules and results were not changed. [MQL5 documents the OnTick clock behavior](https://www.mql5.com/en/docs/dateandtime/timecurrent).\n')
    for r in selected:
        m=r['metrics'];report.append(f"- {r['tag']}: gross P&L ${m['gross_profit']:,.2f}; commission ${m['commission']:,.2f}; swap ${m['swap']:,.2f}; median entry spread {m['median_spread']}; median commission/initial risk {m['median_commission_R']}; maximum measured initial risk {m['max_initial_risk_pct']}% of equity; maximum hold {m['max_hold_minutes']} minutes; flags {r['flags']}.")
    report.append('\nSetup lifecycle counters (native, five-year confirmation):\n')
    for r in selected:
        detail=json.loads((R/'native'/r['tag']/'run.json').read_text())
        report.append('- '+r['tag']+': '+'; '.join(detail['summaries']))
    report+=['\n## Tick-data limitation\n',
      'Broker journals state real ticks begin 2026-01-01. Earlier Model-4 history uses generated ticks where recorded ticks are absent. This is particularly material to scalping; these results are not five years of recorded tick execution. [MetaQuotes documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation) confirms the fallback and spread differences.',
      '\nNative reported history quality (includes warm-up):\n']
    for r in selected:report.append(f"- {r['tag']}: {r['metrics'].get('history_quality','unavailable')}")
    report+=['\n## Directional control\n',
      'One reproducible random-direction seed, same signal-generation rules and stop/target distance. Different exits can alter later eligible setups, so it is not a fully time-matched random-entry benchmark. This is a diagnostic, not a significance test. Shared (setup time, trigger time) counts follow.',
      table(controls)]
    for g in gates:
        for o in g['control_overlap']:report.append(f"- {g['version']} {o['window']}: raw {o['raw_opportunities']}, control {o['control_opportunities']}, shared {o['shared']}.")
    report+=['\n## Fast screens — native Model 1, not tick confirmations\n',table(screens),
      '\n## Decision and scope\n',f"Six strategy definitions. {len(rows)} completed native tests including smoke checks and direction controls. No performance-driven parameter changes. Frequency/month uses elapsed calendar days /30.4375; frequency/weekday uses Monday–Friday dates, not exchange-holiday-adjusted sessions. W/L streaks use net results; equity drawdown comes from native tick-level MT5 statistics, not the sampled chart.",
      '\nNo full optimization, Monte Carlo promotion, production changes, live orders, installer/website changes or publication. Gold and other strategies were left unchanged. Backtest returns are not forecasts.',
      '\nThe research ZIP includes source, tester-only executable, settings and sanitized native ledgers/signal snapshots for audit. Private terminal configuration, credentials, raw account-identifying HTML reports and journals are excluded. Re-running MT5 requires the existing isolated local tester configuration; the EA refuses to run outside the tester.']
    (R/'REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    recovery=R/'LAUNCH RECOVERY.json'
    if recovery.exists():
        rec=json.loads(recovery.read_text())
        with (R/'REPORT.md').open('a',encoding='utf-8') as f:
            f.write(f"\n\nInfrastructure note: {rec['failed_launch_attempts']} local tester-agent authorization failures occurred before strategy execution. They are retained privately, excluded from completed performance trials, and were retried without changing parameters. Recovery status: {rec['recovery_result']}.\n")
    fig,axes=plt.subplots(2,1,figsize=(12,8),gridspec_kw={'height_ratios':[2,1]},layout='constrained')
    colors=plt.cm.tab10.colors
    for i,r in enumerate(selected):
        d=pd.read_csv(R/'native'/r['tag']/'trace.csv.gz')
        if len(d):
            d=d.iloc[::30];axes[0].plot(pd.to_datetime(d.time,unit='s'),(d.equity/10000-1)*100,label=cfg['bots'][i]['name'],color=colors[i],linewidth=1.2)
    axes[0].axhline(0,color='#999',linewidth=.7);axes[0].set_title('US100 unfilled-FVG: six frozen raw interpretations');axes[0].set_ylabel('Sampled equity return (%)');axes[0].legend(ncol=3,fontsize=9);axes[0].grid(alpha=.15)
    x=np.arange(6);axes[1].bar(x-.18,[r['metrics']['return_pct'] for r in selected],width=.36,label='5 years')
    axes[1].bar(x+.18,[by[b['mode'],'1y',4,False]['metrics']['return_pct'] for b in cfg['bots']],width=.36,label='Latest year')
    axes[1].set_xticks(x,[b['name'] for b in cfg['bots']]);axes[1].axhline(0,color='#999',linewidth=.7);axes[1].set_ylabel('Net return (%)');axes[1].legend();axes[1].grid(axis='y',alpha=.15)
    fig.suptitle('CFD broker simulation · 1% nominal risk/trade · earlier ticks generated · no optimization',fontsize=10)
    fig.savefig(R/'comparison.png',dpi=160);plt.close(fig)
    safe=['REPORT.md','RULES.md','run-config.json','UnfilledFVG.mq5','UnfilledFVG.ex5','logic.mqh','prepare.py','run.py','audit.py','test_audit.py','pipeline_run.py','report.py','BUILD.json','PLUMBING.json','AUDIT.json','FINAL GATES.json','compile.log','comparison.png']
    with zipfile.ZipFile(R/'US100 Unfilled FVG research.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in safe:z.write(R/p,p)
        if recovery.exists():z.write(recovery,recovery.name)
        for p in (R/'native').glob('*/*.set'):z.write(p,p.relative_to(R))
        for pattern in ['*/trades.csv.gz','*/signals.csv.gz','*/audit.csv.gz','*/run.json']:
            for p in (R/'native').glob(pattern):z.write(p,p.relative_to(R))
    print(json.dumps(dict(passed=passed,gates=gates),indent=2))
if __name__=='__main__':main()
