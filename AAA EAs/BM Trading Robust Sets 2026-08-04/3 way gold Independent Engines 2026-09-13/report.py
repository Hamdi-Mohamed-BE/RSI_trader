import csv,hashlib,json
from collections import defaultdict
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from params import *
from native import group_stats,hashes
from audit_management import audit

def money(x):return f'${x:,.2f}' if x>=0 else f'-${-x:,.2f}'
def pf(x):return 'N/A' if x is None else f'{x:.3f}'
def ledger(r):return json.loads((ROOT/'Audit'/f"{r['period']}-engine{r['engine']}-d{r['execution_delay_ms']}-trades.json").read_text())
def main():
    new=json.loads((ROOT/'main-results.json').read_text());old=json.loads((OPT/'main-results.json').read_text())
    raw={p:json.loads((RAW/'Runs'/f'{p}-engine0-d1.json').read_text()) for p in WINDOWS}
    assembled=json.loads((ROOT/'assembled-selection.json').read_text());choice=json.loads((ROOT/'individual-selection.json').read_text());c=assembled['config']
    diag=json.loads((ROOT/'diagnostics.json').read_text());assert len(diag['standalone'])==3 and len(diag['delay'])==2
    proof=json.loads((ROOT/'inheritance-parity.json').read_text());assert proof['raw_ledger_exact'] and proof['shared_ledger_exact']
    selection_audit=json.loads((ROOT/'native-selection-verification.json').read_text())
    assert selection_audit['all_ledgers_reconciled'] and len(selection_audit['native_runs'])==22
    checks=[];allruns=[json.loads(p.read_text()) for p in (ROOT/'Runs').glob('*.json')]
    assert len(allruns)==14,('Incomplete final native evidence',len(allruns))
    for r in allruns:
        assert r['source_hashes']==hashes();assert hashlib.sha256((ROOT/r['report']).read_bytes()).hexdigest()==r['report_sha256']
        a=audit(r);ts=ledger(r);s=group_stats(ts);assert abs(s['net_profit']-r['net_profit'])<.01 and s['trades']==r['trades'];checks.append(dict(period=r['period'],model=r['model'],delay=r['execution_delay_ms'],**a))
    save(ROOT/'verification.json',dict(native_runs=checks,parameter_isolation_unit_tests=10,selection_audit=selection_audit,parity=proof,source_hashes=hashes()))
    names={1:'Momentum',2:'Trend change',3:'Breakout'};shortnames={1:'Momentum',2:'Change',3:'Breakout'}
    modes={0:'Fixed SL/TP',1:'BE',2:'ATR trail',3:'BE + ATR trail'};sides={0:'Both',1:'Long only',-1:'Short only'}
    lines=['# 3 way gold — independently optimized engines','',
      '**Research only. Nothing deployed or changed on the website/BATs.** Each engine now retains its own settings; ATR, direction and exit management no longer have to match. All three run on one shared simulated account.',
      '', '## What was tested','',
      'Reused the 5,152 engine parameter searches; shortlisted 24 candidates per engine using development data, compared them on validation, and ran three per engine natively on both splits (18 selection tests). A deduplication audit found that the first three trend-change configurations had identical ledgers because their 0.5R TP preceded the 1.5R management trigger. Two additional effective parameter sets were tested on both splits before final selection (four more native tests). Identical ledgers are not independent robustness evidence. The independent EA then received two exact inheritance parity tests, two combined split tests, five combined windows, three standalone five-year tests and two delay stresses.',
      'Development: 2021-09-05 to 2024-09-05. Validation: 2024-09-05 to 2025-09-05. Latest year: 2025-09-05 to 2026-09-05, not used to choose the new settings. Prior historical aggregates had already been seen; this is additional exploratory multiple testing, not pristine unseen out-of-sample evidence.',
      f"Individual settings frozen **{choice['frozen_at_utc']}**; assembled configuration **{assembled['config_id']}**. All three meet the stated individual development/validation criteria: **{assembled['all_three_qualified']}**.",
      '', '## Native shared-account comparison','',
      'Independent $10,000 starts; nominal 0.30% equity per engine; H1 closed candles; max one position per engine, three total. Exness Zero demo, leverage 1:2000. All periods end 2026-09-05 exclusive (last market tick September 4). Returns are total-period and include native recorded spread, commission and swap. Equity DD is native/every-tick, not only balance drawdown.',
      '', '| Period | Raw return | Shared-settings optimized | Independent engines | Independent final USD | Independent trades | Independent WR |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for p in WINDOWS:
        r=new[p];lines.append(f"| {p} | {raw[p]['return_pct']:+.2f}% | {old[p]['return_pct']:+.2f}% | {r['return_pct']:+.2f}% | {money(r['final_balance'])} | {r['trades']} | {r['net_win_rate']:.2f}% |")
    lines+=['','| Period | Raw PF | Shared PF | Independent PF | Raw equity DD | Shared equity DD | Independent equity DD |','|---|---:|---:|---:|---:|---:|---:|']
    for p in WINDOWS:lines.append(f"| {p} | {pf(raw[p]['net_pf'])} | {pf(old[p]['net_pf'])} | {pf(new[p]['net_pf'])} | {raw[p]['max_equity_dd_pct']:.2f}% | {old[p]['max_equity_dd_pct']:.2f}% | {new[p]['max_equity_dd_pct']:.2f}% |")
    lines+=['','## Decision','',
      f"The independent combination is not a universal upgrade. Over five years it raises win rate from {old['5y']['net_win_rate']:.2f}% to {new['5y']['net_win_rate']:.2f}% and reduces equity DD from {old['5y']['max_equity_dd_pct']:.2f}% to {new['5y']['max_equity_dd_pct']:.2f}%, but lowers return from {old['5y']['return_pct']:+.2f}% to {new['5y']['return_pct']:+.2f}% and PF from {pf(old['5y']['net_pf'])} to {pf(new['5y']['net_pf'])}.",
      f"The longer 2019–2026 diagnostic is less favorable: independent return {new['2019-2026']['return_pct']:+.2f}% versus {old['2019-2026']['return_pct']:+.2f}%, with DD {new['2019-2026']['max_equity_dd_pct']:.2f}% versus {old['2019-2026']['max_equity_dd_pct']:.2f}%. Both versions lose money in the latest six-month window.",
      'Recommendation: keep the preceding jointly optimized preset as the primary research candidate and save the independently selected version as an alternative, not a replacement. Higher standalone validation scores and a higher combined win rate did not translate into a better full-history portfolio. Forward demo comparison is more useful now than further tuning to these already-seen windows. Neither preset is approved for live or prop-firm use.',
      '', '## Independently selected inputs','', '| Engine | Direction | Signal | ATR period | Stop | TP | Management |','|---|---|---|---:|---:|---:|---|']
    for e,n in names.items():
        v=effective(c,e);nn=shortnames[e]
        rule=(f"EMA{c['InpPullbackEMA']} reclaim; EMA{c['InpTrendFastEMA']}/{c['InpTrendSlowEMA']}; ADX{c['InpADXPeriod']}>={c['InpADXMin']:g}, DI agreement" if e==1 else
          f"EMA{c['InpChangeFastEMA']}/{c['InpChangeSlowEMA']} cross; RSI{c['InpRSIPeriod']} confirmation{c['InpRSIThreshold']:g}" if e==2 else
          f"{c['InpBreakoutBars']}-hour channel; range>={c['InpExpansionATR']:g} prior ATR; risingATR={c['InpRisingATR']}")
        management=modes[v['InpManagement']]
        if v['InpManagement']:management+=f" after closed H1 reaches {v['InpTriggerR']:g}R"
        if v['InpManagement'] in (2,3):management+=f"; {v['InpTrailATR']:g} ATR distance"
        lines.append(f"| {n} | {sides[v['InpDirection']]} | {rule} | {v['InpATRPeriod']} | {c['Inp'+nn+'StopATR']:g} ATR | {c['Inp'+nn+'RR']:g}R | {management} |")
    lines+=['','Targets remain fixed. Stops only tighten based on completed H1 candles. BE means entry-price SL, not fee-free break-even. RSI thresholds are symmetric for shorts (100 minus the shown threshold). Each engine owns its ATR period and management state.','',
      '## Each engine standalone — previous versus independently selected settings, five years','',
      'Each standalone test starts at $10,000 and uses 0.30% nominal risk. Standalone returns cannot be added to recreate the combined account, because position sizing uses changing shared equity.','',
      '| Engine | Previous return | New return | Previous/new trades | Previous/new WR | Previous/new PF | Previous/new equity DD |','|---|---:|---:|---:|---:|---:|---:|']
    alloc=json.loads((OPT/'stress-results.json').read_text())['allocations']
    for r in diag['standalone']:
        e=r['engine'];nn=shortnames[e]
        prev=next(a for a in alloc if a['config']['Inp'+nn+'RiskWeight']>0 and sum(a['config']['Inp'+n+'RiskWeight']>0 for n in shortnames.values())==1)
        lines.append(f"| {names[e]} | {prev['return_pct']:+.2f}% | {r['return_pct']:+.2f}% | {prev['trades']}/{r['trades']} | {prev['net_win_rate']:.2f}%/{r['net_win_rate']:.2f}% | {pf(prev['net_pf'])}/{pf(r['net_pf'])} | {prev['max_equity_dd_pct']:.2f}%/{r['max_equity_dd_pct']:.2f}% |")
    lines+=['','## Actual five-year contributions in the new combined account','', '| Engine | Trades | Win rate | Net USD | PF | Commission | Swap |','|---|---:|---:|---:|---:|---:|---:|']
    for n,r in new['5y']['by_engine'].items():lines.append(f"| {n} | {r['trades']} | {r['net_win_rate']:.2f}% | {money(r['net_profit'])} | {pf(r['net_pf'])} | {money(r['commission'])} | {money(r['swap'])} |")
    assert abs(sum(r['net_profit'] for r in new['5y']['by_engine'].values())-new['5y']['net_profit'])<.01
    lines+=['','## Individual native selection results','', '| Engine | Qualified | Train trades / return / PF / DD | Validation trades / return / PF / DD |','|---|---|---|---|']
    for e,n in names.items():
        x=choice['engines'][str(e)];a=x['train'];b=x['validation']
        lines.append(f"| {n} | {x['eligible']} | {a['trades']} / {a['return_pct']:+.2f}% / {pf(a['net_pf'])} / {a['max_equity_dd_pct']:.2f}% | {b['trades']} / {b['return_pct']:+.2f}% / {pf(b['net_pf'])} / {b['max_equity_dd_pct']:.2f}% |")
    lines+=['','Qualification: >=50/15 trades in development/validation, both profitable with PF>1.05 and equity DD<=15%, no stopout. The weakest split determines ranking. A best standalone engine is not automatically the best joint portfolio; the combined comparison above tests that assumption.','',
      '## Native costs, risk and delay stress','', '| Period | Commission | Swap | Max actual initial risk/trade | Max concurrent | Max losing streak | Stopout | Rejected requests |','|---|---:|---:|---:|---:|---:|---|---:|']
    for p,r in new.items():lines.append(f"| {p} | {money(r['commission'])} | {money(r['swap'])} | {r['max_trade_risk_pct']:.2f}% | {r['max_concurrent_positions']} | {r['max_loss_streak']} | {r['native_stopout']} | {len(r['execution_errors'])} |")
    reasons=defaultdict(int)
    for e in new['5y']['execution_errors']:reasons[(e['event'],e['note'])]+=1
    lines+=['','Five-year rejected requests: '+(', '.join(f'{count} {event}: {note}' for (event,note),count in sorted(reasons.items())) or 'none')+'. These are not filled trades. A rejected entry is not retried within the same H1 bar; a rejected stop modification leaves the prior SL in place until a subsequent valid management check. The recorded results include that behavior.','',
      '| Latest-year delay | Trades | Return | PF | Equity DD |','|---|---:|---:|---:|---:|']
    for r in [new['1y'],*diag['delay']]:lines.append(f"| {r['execution_delay_ms']}ms | {r['trades']} | {r['return_pct']:+.2f}% | {pf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% |")
    lines+=['','## Interpretation and limitations','',
      '- The round-UP/minimum-lot rule is retained. Nominal 0.30% is not a hard cap. Small-account minimum-lot risk can exceed it substantially; no prop-firm or daily-loss protection has been applied.',
      '- Native real ticks start 2026-01-01; MT5 generates earlier missing real ticks. The 1ms baseline is optimistic; 100/500ms tests are latency checks, not proof of live-news execution quality.',
      '- Native recorded commission/swap are included once. Historical broker fee changes, dynamic leverage and high-margin requirements were not independently reconstructed.',
      '- Selection uses overlapping historical research. Long-only success can reflect the gold trend sample. It is not a guarantee or a replica of the creator\'s unknown bot.',
      '- Earlier period aggregates were known; latest-year results were not used to change these new parameters after freezing. Recent losses and weaker variants remain visible.',
      '- Both inheritance parity tests match exactly: 185 raw six-month trades and 44 preceding optimized six-month trades. Independent signals, fill risk, management ratchets, cost ledgers and native report hashes are audited.',
      '', '## Monthly new combined five-year closed-trade results','',
      'Trade net P/L belongs to its close month, including full recorded costs. This is not MTM monthly return or payouts. Edge months are partial.','',
      '| Month | Trades | Win rate | Net USD | Closed return | Ending balance | Commission | Swap |','|---|---:|---:|---:|---:|---:|---:|---:|']
    ts=ledger(new['5y']);months=[];date=datetime(2021,9,1);bal=10000.
    while date<datetime(2026,10,1):
        key=date.strftime('%Y.%m');stats=group_stats([t for t in ts if t['close_time'].startswith(key)]);rr=100*stats['net_profit']/bal;bal+=stats['net_profit']
        r=dict(month=key,return_pct=rr,ending_balance=bal,**stats);months.append(r)
        lines.append(f"| {key} | {r['trades']} | {r['net_win_rate']:.2f}% | {money(r['net_profit'])} | {rr:+.2f}% | {money(bal)} | {money(r['commission'])} | {money(r['swap'])} |")
        date=date.replace(year=date.year+1,month=1) if date.month==12 else date.replace(month=date.month+1)
    assert abs(bal-new['5y']['final_balance'])<.01;save(ROOT/'monthly-breakdown.json',months)
    with (ROOT/'monthly-breakdown.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(months[0]));w.writeheader();w.writerows(months)
    save(ROOT/'yearly-breakdown.json',[dict(year=y,**group_stats([t for t in ts if t['close_time'].startswith(str(y))])) for y in range(2021,2027)])
    lines+=['','![Raw, shared and independent comparison](three-way-comparison.png)','',
      'See [PROTOCOL.md](PROTOCOL.md), [assembled-selection.json](assembled-selection.json), [individual-selection.json](individual-selection.json), [diagnostics.json](diagnostics.json) and [verification.json](verification.json). Both optimized versions and their raw baseline remain saved.','']
    (ROOT/'INDEPENDENT ENGINE RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained',sharex=True)
    for label,r,folder,color in [('Raw',raw['5y'],RAW,'#8a909c'),('Shared settings',old['5y'],OPT,'#b68728'),('Independent engines',new['5y'],ROOT,'#008f79')]:
        filename='5y-engine0-d1-equity.csv' if label=='Raw' else f"{r['period']}-engine0-d1-equity.csv"
        with (folder/'Audit'/filename).open() as f:eq=list(csv.DictReader(f))
        eq.append(dict(time=r['actual_last_tick'],equity=r['final_balance']));dates=[datetime.strptime(x['time'],'%Y.%m.%d %H:%M:%S') for x in eq];vals=np.array([float(x['equity']) for x in eq]);peak=np.maximum.accumulate(np.r_[10000,vals])[1:]
        axes[0].plot(dates,vals,label=f"{label}: {r['return_pct']:+.2f}% | PF{r['net_pf']:.2f}",color=color,lw=.9)
        axes[1].plot(dates,100*(vals/peak-1),label=f"{label}: native DD{r['max_equity_dd_pct']:.2f}%",color=color,lw=.8)
    axes[0].set_title('3 way gold | native MT5 | independent USD 10,000 starts\nEach combined system runs all three engines simultaneously at nominal 0.30% each')
    axes[0].set_ylabel('Equity USD (hourly samples)');axes[1].set_ylabel('Sampled equity drawdown (%)')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.supxlabel('Recorded costs included. Real-tick coverage limited before 2026. Historical research, not live/prop-firm proof.',fontsize=9)
    fig.savefig(ROOT/'three-way-comparison.png',dpi=150);plt.close(fig)
    files=[ROOT/name for name in ['INDEPENDENT ENGINE RESULTS.md','assembled-selection.json','individual-selection.json','main-results.json','diagnostics.json','verification.json','PROTOCOL.md','monthly-breakdown.json','monthly-breakdown.csv','yearly-breakdown.json','three-way-comparison.png','native-selection-verification.json']]
    files.extend([*ROOT.glob('*.py'),*(ROOT/'EA').glob('*'),*(ROOT/'Sets').glob('3 way gold - *.set')])
    save(ROOT/'manifest.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    print('INDEPENDENT REPORT READY',len(allruns),'native combined/standalone/parity runs',flush=True)

if __name__=='__main__':main()
