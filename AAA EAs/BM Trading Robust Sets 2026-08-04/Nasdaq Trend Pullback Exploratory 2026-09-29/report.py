"""Review artifacts generated only from completed, independently audited tests."""
import json
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import search as s


def load(name):
    p=s.OUT/name/'results.json'
    return json.loads(p.read_text())[0] if p.exists() else None


def table(items):
    lines=['| Version / test | Return | PF | Equity DD | Trades | /month | /trading day | Win% | W/L streak |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label,r in items:
        if r is None:continue
        n=r['net'];day=n.get('trades_per_trading_day')
        d=f'{day:.3f}' if day is not None else 'n/a'
        lines.append(f"| {label} | {n['return_pct']:+.2f}% | {n['profit_factor']:.3f} | {n['equity_dd_pct']:.2f}% | {n['trades']} | {n['trades_per_month']:.2f} | {d} | {n['win_rate_pct']:.1f}% | {n['max_win_streak']}/{n['max_loss_streak']} |")
    return '\n'.join(lines)+'\n'


def describe(c):
    tf=f"M{c['tf']}" if c['tf']<60 else 'H1' if c['tf']==60 else 'H4'
    entries={0:'market at next executable quote',1:'extra closed-bar confirmation',2:f"limit retest {c['offset']} ATR",3:f"limit retest {c['offset']} index points",4:f"continuation stop {c['offset']} ATR"}
    stops={0:f"{c['sl']} ATR",1:f"{c['sl']}% of price",2:f"{c['sl']} index points",3:'signal candle extreme',4:'five-bar swing',5:'20-bar structure'}
    trails={0:'none',1:f"breakeven at {c['start']}R",2:f"{c['dist']} ATR from {c['start']}R",3:f"{c['dist']}% of price from {c['start']}R",4:f"pullback EMA from {c['start']}R",5:f"five-bar swing from {c['start']}R",6:f"chandelier {c['dist']} ATR from {c['start']}R",7:'completed-M15 50% trigger / 20% lock'}
    exits={0:f"{c['rr']}R target",1:'no target + trail',2:'known 20-bar extreme',3:'time only',4:f"50% at 1R, trail, final {c['rr']}R",5:'end of entry session'}
    sessions={0:'07:00–16:59 UTC',1:'00:00–07:59 UTC',2:'07:00–15:59 UTC',3:'09:30–15:59 New York',4:'12:00–15:59 UTC',5:'09:30–10:59 New York',6:'all quoted hours'}
    filters={0:'none',1:'price versus EMA200',2:'closed H4 EMA50 agreement',3:'ADX14 >= 20',4:'DI agreement',5:'ATR 20th–80th percentile',6:'spread <= 0.1 ATR',7:'causal Markov direction confirmation'}
    return '\n'.join([
        f"- Signal: **{tf}**, EMA{c['fast']} versus EMA{c['slow']}, fast-EMA slope over {c['slope']} bars, pullback touch at EMA{c['pullback']} within the prior {c['lookback']} bars, then a close beyond the previous bar and pullback EMA. ATR{c['atr']}; all inputs completed bars.",
        f"- Entry: {entries[c['entry']]}. Stop: {stops[c['stop']]}. Exit: {exits[c['exit']]}. Trailing rule: {trails[c['trail']]}. Indicator trails use the last computed closed-bar values and update at new signal bars; BE can update on ticks.",
        f"- New-order placement session: {sessions[c['session']]}; direction: {['both','long only','short only'][c['direction']]}; filter: {filters[c['filter']]}; weekday exclusion: {['none','Monday','Friday','Monday and Friday'][c['day']]}. Pending orders can fill later: expiry is four signal bars after placement, capped by the daily cutoff when enabled.",
        f"- Capacity: {c['max_day']} attempts/day, {c['max_pos']} position slot(s), {'one extra qualifying reentry after a negative-gross SL exit' if c['reentry'] else 'no extra stop-loss reentry'}. Holding limit: {str(c['hold'])+' minutes' if c['hold'] else 'none'}. Daily flat: {'on' if c['flat'] else 'off'}; cutoff {c['cutoff']}:00 UTC; weekend holding {'allowed' if c['weekend'] else 'disabled'}. Timed exits execute only when quotes are available.",
        '- Risk: nominal 1% equity across available position slots, rounded UP to lot step; minimum-lot, fills and gaps can cause oversizing. This is not a guaranteed loss cap or prop-firm-safe configuration.'
    ])


def chart(groups):
    fig,axs=plt.subplots(len(groups),1,figsize=(12,4*len(groups)),squeeze=False,layout='constrained')
    for ax,(title,pairs) in zip(axs[:,0],groups):
        for label,row,color in pairs:
            d=pd.read_csv(s.OUT/row['stage']/f"{row['index']}-trace.csv.gz")
            curve=pd.Series(d.equity.to_numpy(),index=pd.to_datetime(d.time,unit='s',utc=True)).resample('1h').last().dropna()
            ax.plot(curve.index,100*(curve/10000-1),label=label,color=color,lw=1.4)
        ax.set_title(title,loc='left',weight='bold');ax.set_ylabel('Equity change (%)');ax.axhline(0,color='#888',lw=.7)
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.legend(frameon=False)
    fig.suptitle('Nasdaq trend-pullback — exploratory optimization',fontsize=16,weight='bold')
    fig.savefig(s.ROOT/'comparison.png',dpi=160);plt.close(fig)


def main():
    verdict=json.loads((s.ROOT/'VERDICT.json').read_text());verification=json.loads((s.ROOT/'VERIFICATION.json').read_text());assert verification['passed']
    rows=[r for p in s.OUT.glob('*/results.json') for r in json.loads(p.read_text())]
    screens=json.loads((s.ROOT/'SEARCH RESULTS.json').read_text())
    stages=json.loads((s.ROOT/'STAGES.json').read_text())
    final_path=s.ROOT/'FROZEN FINAL.json';final=json.loads(final_path.read_text()) if final_path.exists() else None
    df=s.ROOT/'DEVELOPMENT FINALISTS.json';dev=json.loads(df.read_text()) if df.exists() else verdict.get('best',[])
    val=[load('validation-'+str(i)) for i in range(3)];val=[r for r in val if r]
    baseval=load('baseline-validation');recent=load('recent-frozen');base=load('parity')
    chosen=final if final else dev[0] if dev else None
    rejected=verdict['status'].startswith('REJECTED')
    accounting=dict(native_passes=len(rows),search_passes=len(screens),unique_parameter_vectors=len({r['parameters_sha'] for r in rows}),
        economically_distinct_parameters=len({s.effective_key(r['parameters']) for r in rows}),execution_flagged_passes=sum(not r['clean'] for r in rows),
        prior_raw_study_passes=64,additional_prior_nasdaq_confirmation_passes=4,conservative_observed_passes_for_multiplicity=len(rows)+68)
    s.save(s.ROOT/'TRIAL ACCOUNTING.json',accounting);s.save(s.ROOT/'ALL NATIVE RESULTS.json',rows)
    groups=[]
    if val and baseval:
        bestview=final if final else val[0]
        groups.append(('Validation: 27 Mar 2024 – 27 Sep 2025',[('Original',baseval,'#187a64'),('Selected' if final else 'Development leader',bestview,'#c35442')]))
    if recent:groups.append(('Recent confirmation: 27 Sep 2025 – 27 Sep 2026',[('Original',base,'#187a64'),('Frozen selection',recent,'#c35442')]))
    if groups:chart(groups)
    headline='No optimized version survived the frozen evaluation gates.' if rejected else 'Research evaluation requires the remaining recorded gates; no deployment approval.'
    txt=f"# Nasdaq trend-pullback — exploratory review\n\n**{headline}** Status: `{verdict['status']}`. The user explicitly authorized this search despite the original raw failure. That raw rejection remains on record. Gold, Bitcoin, GBPUSD and the separately deployed Nasdaq 5-minute bot were not changed.\n\n"
    txt+='## Like-for-like evaluation\n\nHistorical native MT5 tests on Exness USTEC CFD, USD10,000 per run, nominal 1% equity risk rounded UP, 150ms simulated delay and broker-model spread, swap, commission and fees. Model4 uses recorded ticks where present and generated ticks otherwise. Return is cumulative; PF and win rate are net of recorded costs; equity DD is from the full native tester. /month uses elapsed calendar months; /trading day uses UTC weekdays with archived quotes, irrespective of candidate session. Streaks use net closed positions, not full-risk-loss counts.\n\n'
    if val:
        txt+='### Validation — 2024-03-27 to 2025-09-27 exclusive\n\n'+table([('Original',baseval)]+[(f"Candidate {chr(65+int(r['stage'].split('-')[-1]))}",r) for r in val])+'\n'
        for r in val:
            why=[];n=r['net']
            if n['trades']<30:why.append('fewer than 30 positions')
            if n['net_profit']<=0:why.append('nonpositive net result')
            if n['profit_factor']<1.15:why.append('PF below 1.15')
            if not r['clean']:why.append('execution flags')
            txt+=f"- {r['stage']}: "+(', '.join(why) if why else 'passed the frozen validation thresholds')+'.\n'
    if recent:
        txt+='\n### Recent confirmation — 2025-09-27 to 2026-09-27 exclusive\n\n'+table([('Original',base),('Frozen selected candidate',recent)])+'\n'
        txt+='Only the validation-selected version was tested here. No failed candidate was retuned or replaced after viewing this result. This year was previously seen for the baseline and is not called an untouched holdout.\n\n'
        if verdict['status']=='REJECTED_RECENT_CONFIRMATION':
            txt+='**Why it failed:** the selected version lost money, PF 0.930 missed the frozen 1.15 minimum, and 27 positions fell below the 30-position floor. Lower drawdown came with much lower trading activity and did not establish an improved edge. The original performed better in this recent period, but its earlier raw-gate rejection remains valid; neither version is approved for promotion.\n\n'
    if groups:txt+=f"![Nasdaq evaluation comparison]({(s.ROOT/'comparison.png').as_posix()})\n\nChart lines are hourly samples of recorded equity; the table’s drawdowns come from full native tick paths.\n\n"
    if 'holdout' in verdict:
        txt+='### Older temporal transfer — 2019-09-27 to 2021-09-27\n\n'+table([('Original',load('baseline-older')),('Frozen selection',verdict['holdout'])])+'\nThis is earlier-time transfer, not future-forward testing or globally unseen repository data.\n\n'
    txt+='## Development finalists — fitted, not validated\n\n2021-09-27 to 2024-03-27 exclusive, faster Model1 one-minute-OHLC screening. Do not compare these figures with Model4 as if their execution quality were identical.\n\n'+table([(f'Candidate {chr(65+i)}',r) for i,r in enumerate(dev)])+'\n'
    if len(dev)>1:
        keys=['open_epoch','close_epoch','side','volume','open_price','close_price','net_profit','initial_sl','initial_tp']
        sig=lambda r:sorted(tuple(round(t[k],6) for k in keys) for t in s.read_trades(r['stage'],r['index']))
        if all(sig(r)==sig(dev[0]) for r in dev[1:]):
            txt+='The three finalists have identical development trade ledgers, not three independent edges. They differ only in holding/weekend settings that did not change these trades: A has no elapsed holding limit and allows weekends; B has a 960-minute limit and allows weekends; C has a 480-minute limit and disallows weekends. All retain daily-flat logic. The three validation ledgers are '+('also identical' if len(val)==3 and all(sig(r)==sig(val[0]) for r in val[1:]) else 'reported separately')+'. Candidate A won the deterministic first-in-order tie; later outcomes were not used to break it. No replacements were selected after seeing validation.\n\n'
    if chosen:
        txt+='## '+('Validation-selected version' if final else 'Development leader — not a validated recommendation')+'\n\n'+describe(chosen['parameters'])+'\n\n'
        s.save(s.ROOT/'REVIEW PARAMETERS.json',dict(status=verdict['status'],selection_basis='validation' if final else 'development_only',parameters=chosen['parameters'],deployment_authorized=False))
    txt+='## Search coverage\n\n'+f"{accounting['search_passes']} development/plateau screen passes; {accounting['native_passes']} native passes overall; {accounting['unique_parameter_vectors']} unique parameter vectors ({accounting['economically_distinct_parameters']} after removing explicitly inactive settings, not after deduplicating historical outcomes). Every repeated, losing, empty and execution-flagged test remains counted. Execution flags appeared in {accounting['execution_flagged_passes']} pass(es). Including 68 previous raw-study/Nasdaq-confirmation passes gives {accounting['conservative_observed_passes_for_multiplicity']} observed passes for conservative multiplicity accounting; they are not independent trials.\n\n"
    txt+=table([(stage['stage']+' stage leader',stage['leaders'][0]) for stage in stages])+'\n'
    txt+='This is a broad staged top-three search, not an exhaustive Cartesian search or a proven global optimum. D1 was excluded as a different daily-clock hypothesis; market-on-close and next-bar-open collapse to the same executable quote; news filtering was excluded without a verified point-in-time historical calendar. See PROTOCOL.md and DIMENSION COMPARISONS.md for the full tested scope.\n\n'
    pp=s.ROOT/'PLATEAUS.json'
    if pp.exists():
        txt+='Joint neighborhood checks (development only):\n\n'
        for p in json.loads(pp.read_text()):txt+=f"- Candidate {chr(65+p['index'])}: axes {', '.join(p['axes'])}; {p['positive_fraction']:.1%} profitable and execution-clean neighbors; median PF {p['median_pf']:.3f}; {'passed' if p['passed'] else 'failed'}. A plateau does not guarantee later profitability.\n"
    txt+='\n## Execution, risk and evidence\n\n'
    for label,r in [('Original recent year',base),('Original validation',baseval)]+[(r['stage'],r) for r in val]+([('Selected recent year',recent)] if recent else []):
        if not r:continue
        n=r['net'];flags={k:n[k] for k in s.FLAGS if n[k]}
        txt+=f"- {label}: native equity DD {n['equity_dd_pct']:.2f}%, balance DD {n['balance_dd_pct']:.2f}%; initial stop-risk maximum {n['max_actual_risk_pct']:.3f}%; {n['overnight_positions']} cross-date positions, {n['swap_positions']} with swap, {n['late_timed_exits']} delayed timed exits, longest hold {n['max_hold_hours']:.2f}h; execution flags {flags or 'none'}; partial-close skips {n['partial_skips']}.\n"
    txt+='\nDelayed-exit diagnostics compare explicit elapsed, daily and Friday cutoffs; they do not reconstruct the historical broker holiday calendar or every session-exit deadline. Quote-gap delays remain in P&L, with no invented calendar-time fills. The exploratory override does not certify a strictly intraday system. Any surviving version with unintended carryovers needs a separately specified execution remedy before such a claim. Negative net breakeven exits count as losses.\n\n'
    txt+=f"Baseline engine parity matched all 103 original recent-year positions and $2,521.70 net. Independent verification passed {verification['numerical_causal_windows']} numerical/causality windows, {verification['baseline_native_signals']} native baseline signal checks and {verification['native_cases']} archived native-case ledgers ({verification['positions']:,} position rows). Compile logs, exact case tables, source/EX5 and native cash reconciliation are retained. Signal checks do not independently reproduce every optional execution branch.\n\n"
    txt+='The regime skill influenced past-only state estimation and future-data mutation checks. Its packaged runner was absent; the local optional Markov filter uses 20-bar returns and past transitions as explicitly documented, not GARCH/HMM. An apparent regime or a profitable optimized backtest is not proof of predictive skill.\n\n'
    txt+='## Limitations and stop point\n\nRecorded real ticks on this broker feed begin 2026-01-01. Earlier tests use generated ticks, and displayed history percentages include warm-up. Broker fee schedules are not an independently verified historical series; the fixed delay is not measured live slippage. Selection after many variants creates bias. Previously seen baseline periods are not pristine holdouts.\n\n'
    if rejected:
        txt+='The pipeline stopped at the rejection above. No failed evaluation was optimized again. Any later holdout, full-window candidate confirmation, control, Monte Carlo/deflated-Sharpe, additional-cost stress, FTMO scenario, portfolio integration or deployment not recorded here **was not completed**. A development winner is not a surviving edge.\n\n'
    else:txt+='Additional gate outputs, if present, must be reviewed individually; this report alone does not grant trading readiness.\n\n'
    txt+='No normal MT5 session was restarted or configured, and no live orders, production SET, installer, website or Git push were made. Await user review before Bitcoin/GBPUSD.\n\n'
    txt+='Method references: [MT5 real/generated ticks](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation), [weekday session API](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade). Exact artifacts: ALL NATIVE RESULTS.json, SEARCH RESULTS.json, run-config-search.json, PARITY.json, VERIFICATION.json, VERDICT.json and native/. Private connection INIs and raw account-identifying reports are excluded from the review ZIP.\n'
    (s.ROOT/'REPORT.md').write_text(txt,encoding='utf-8')
    detail='# Nasdaq — complete staged dimension comparisons\n\nAll rows are development Model1 screens. Later stages condition on earlier selected settings, so this is not a balanced all-factor comparison. Every tested setting is retained, including inactive duplicates, empty cases and failures. Index maps to the full parameter vector in SEARCH RESULTS.json. The staged leader is chosen by PF/sample/equity-DD score, not return.\n\n'
    for stage in stages:
        r=json.loads((s.OUT/stage['stage']/'results.json').read_text())
        detail+='## '+stage['stage']+'\n\n'+table([(f"case {x['index']}"+(' — execution flags' if not x['clean'] else ''),x) for x in sorted(r,key=lambda x:x['index'])])+'\n'
    (s.ROOT/'DIMENSION COMPARISONS.md').write_text(detail,encoding='utf-8')
    allowed=['REPORT.md','PROTOCOL.md','DIMENSION COMPARISONS.md','TRIAL ACCOUNTING.json','ALL NATIVE RESULTS.json','SEARCH RESULTS.json','STAGES.json','PARITY.json','VERIFICATION.json','VERDICT.json','run-config-search.json','REVIEW PARAMETERS.json','DEVELOPMENT FINALISTS.json','PLATEAUS.json','FROZEN FINAL.json','comparison.png']
    package=s.ROOT/'Nasdaq-exploratory-review.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for name in allowed:
            p=s.ROOT/name
            if p.exists():z.write(p,name)
        if chosen:
            for p in (s.OUT/chosen['stage']).iterdir():
                if p.suffix in ['.mq5','.mqh','.ex5','.set'] or p.name in ['manifest.json','compile.log'] or p.name.endswith('-trades.csv.gz'):
                    z.write(p,('REJECTED-candidate/' if rejected else 'RESEARCH-candidate/')+p.name)
    with zipfile.ZipFile(package) as z:assert z.testzip() is None and not any(x.lower().endswith('.ini') for x in z.namelist())
    s.save(s.ROOT/'PACKAGE.json',dict(path=str(package),sha256=s.sha(package),private_connection_files_excluded=True))
    print(json.dumps(dict(status=verdict['status'],counts=accounting,report=str(s.ROOT/'REPORT.md')),indent=2))


if __name__=='__main__':main()
