"""Create a local research report and balance chart, without publishing."""
from pathlib import Path
from datetime import datetime
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
NAMES={'baseline':'Current rules','di':'DI agreement','adx20':'ADX >=20','adx25':'ADX >=25','adx20-di':'ADX >=20 + DI','adx25-di':'ADX >=25 + DI','adx20-di-rising':'ADX >=20 + DI + rising ADX','exit24h':'Wait 24h after exit','fresh-signal':'Wait for fresh momentum signal','adx20-di-exit24h':'ADX >=20 + DI + wait 24h','adx20-di-fresh':'ADX >=20 + DI + fresh signal'}
def table(rows):
 s='| Version | Return | PF | Equity DD | Win rate | Trades / month / weekday | Max W / L streak |\n|---|---:|---:|---:|---:|---:|---:|\n'
 for r in rows:
  m=r['metrics'];pf=f"{m['profit_factor']:.2f}" if m['profit_factor'] is not None else 'n/a'
  s+=f"| {NAMES[r['variant']]} | {m['return_pct']:+.2f}% | {pf} | {m['equity_dd_pct']:.2f}% | {m['win_rate_pct']:.2f}% | {m['trades']} / {m['trades_per_month']:.2f} / {m['trades_per_weekday']:.3f} | {m['max_win_streak']} / {m['max_loss_streak']} |\n"
 return s
def main():
 rows=[json.loads(p.read_text()) for p in sorted((ROOT/'native').glob('*/result.json'))]
 sel=json.loads((ROOT/'SELECTION.json').read_text());audit=json.loads((ROOT/'AUDIT.json').read_text());account=json.loads((ROOT/'account-audit.json').read_text())
 chosen=sel['chosen'];recent=[r for r in rows if r['model']==4]
 assert len(recent)==4
 tests={r['case']:r for r in rows}
 current1=tests['baseline-1y-m4']['metrics'];new1=tests[f'{chosen}-1y-m4']['metrics']
 current6=tests['baseline-6m-m4']['metrics'];new6=tests[f'{chosen}-6m-m4']['metrics']
 improved=new1['return_pct']>current1['return_pct'] and new6['return_pct']>current6['return_pct']
 positive=new1['return_pct']>0 and new6['return_pct']>0
 verdict=('Improved versus the baseline in both recent windows.' if improved else 'Does not improve both recent windows.')+' '+('Positive in both recent windows, but not yet fully validated.' if positive else 'At least one recent window loses: not a deployment candidate.')
 header=f'''# XAU Slow Trend — account diagnosis and filter comparison

Research date: 29 September 2026. No live changes, installation, website update or orders.

## Outcome

The frozen selection was **{NAMES[chosen]}**. {verdict}

This is a focused eleven-version filter/re-entry study, not the full optimization/Monte Carlo/promotion pipeline. Risk and exits were not optimized.

## What actually happened on the active account

- Connected normal MT5: Exness-MT5Trial15 **demo**, USD, account ending {account['account_suffix']}; XAUUSD; magic 969060311, comment `Calyx slow trend`.
- Snapshot {account['asof']}: **{account['entries']} entries, {account['closed_positions']} fully closed positions and {account['open_positions']} open** since the first available matching entry on 21 September. Closed net **${account['closed_net']:,.2f}**; all six closed positions involved manual desktop/mobile exits (one partial-close pair). These profits are from **bot entries plus your manual exits**, not unattended EA performance. The open position is excluded.
- On 23 September a short closed at **13:04:21 UTC** and another short opened at **13:04:23 UTC**. The preceding entry was on 22 September at 04:00:02, so more than 24 hours had already passed.
- Source permits one position but checks cooldown from **last entry**, not last close; its monthly momentum remains valid across many H4 candles. A manual close does not clear that signal or request a pause. Therefore an immediate replacement is permitted once the old entry is over 24h old. This is not evidence of multiple simultaneous positions or a new independent signal every time.
- The open trade's stop distance was 52.581 gold-price units, closed-H4 ATR14 was 35.053786, and target distance 315.484: consistent with **1.5ATR stop / 6R target**. All three momentum votes were bearish.

## Baseline identity and execution assumptions

Saved chart/SET specifies H4, 1/3/6-month momentum majority, EMA100 trading days (=600 H4 bars), ATR14 x1.5 stop, 6R TP, both directions, no trail, 1% current-equity risk rounded upward, minimum lot permitted, and original 24h entry-to-entry cooldown. Portfolio adaptation is off for the standalone test.

Saved chart still names XAUUSDr while actual trades are XAUUSD; Python MT5 cannot read active chart input values. Treat saved settings as an assumption, corroborated by the live trade geometry, not an exhaustive live configuration readout. Installed EX5 is older and its hash differs from repository EX5. We tested a copy of that installed binary: **all 38 trade records exactly matched the current-source research clone with filters off** on 2025-09-27 to 2026-09-27, Model1. That is bounded parity, not proof of identical code under every possible condition.

All new backtests: isolated **Exness-MT5Trial16**, XAUUSD CFD, USD10,000 starting balance, 1% nominal risk, 150ms delay, broker spread/swap/commission. The live account is Trial15: same broker but a different demo server/account, not exact live fills. Existing account deposits, other bots, interventions and account-wide risk are not replayed. Minimum-lot rounding can exceed nominal risk. End dates below are exclusive. Current six-month website screenshot ends 2026-09-05, so its -7.13% is not the same window as these new tests.

## Recent native confirmation — one year

2025-09-27 to 2026-09-27. Native Model4, real ticks where available and platform-generated fallback where not. Recent baseline was already seen in parity; this is **not an untouched holdout**.

'''
 text=header+table([tests['baseline-1y-m4'],tests[f'{chosen}-1y-m4']])
 text+='\n## Recent native confirmation — six months\n\n2026-03-27 to 2026-09-27. Native Model4; overlapping subset of the year, not independent validation.\n\n'+table([tests['baseline-6m-m4'],tests[f'{chosen}-6m-m4']])
 text+='\n## Development comparison — all eleven versions\n\n2021-09-27 to 2024-09-27, native Model1 OHLC screen. Generated ticks; fast screening evidence, not real-tick execution proof. All thresholds and selection rules were fixed before the screen.\n\n'+table(sorted([r for r in rows if r['window']=='dev'],key=lambda r:list(NAMES).index(r['variant'])))
 text+='\n## Separate validation — frozen finalists\n\n2024-09-27 to 2025-09-27, native Model1. Best three eligible development return/DD ratios advanced; selection required >=10 validation trades, positive return and PF>=1.1, then ranked return/DD.\n\n'+table([r for r in rows if r['window']=='val'])
 text+='''
## Filter definitions and the manual-close problem

All indicator decisions use **closed H4 candles**. Native iADX(14): ADX strength >=20 or25; direction agreement is +DI>-DI for a buy and -DI>+DI for a sell. Rising means ADX[1]>ADX[2]. Original stop/target, direction and sizing do not change.

ADX/DI is an **entry-quality filter**, not a manual override. It can still permit a replacement immediately after a manual close. The targeted operational remedy is a persisted manual-close pause (e.g. block until the next H4 close, 24h after manual close, or explicit manual re-arm), identifying the bot by original position ID even when the closing deal has magic0. That remains a recommendation, not installed code.

The historical cooldown comparisons wait24h after **any full exit** (including SL/TP); the fresh-signal comparison waits until the original momentum signal changes after the exit. They are not the same as manual-only lockouts. We cannot assign a trustworthy profit improvement to a manual-only pause without specifying a reproducible manual-exit rule. Fresh-signal locking substantially reduced trade count but failed the development profit requirement.

Keep risk/exit research separate from entry filtering. The current 6R target and slow monthly signal can hold trades through large adverse moves; promising ADX results do not certify this stop/exit design or guarantee future profitability.

## Evidence checks and limits

'''
 text+=f"- {len(rows)} completed native tests; {audit['unique_parameter_vectors']} distinct parameter versions including baseline; installed-versus-source parity counted as a separate execution, not a new parameter choice.\n"
 text+='- Every tested source/include hash stayed frozen. Clean research compile: zero errors/warnings. All reports checked for symbol, expert, dates and every input; all closed-deal cash totals reconcile. Independent ledger audit checks prices/contract-size P&L, no overlap, entry-to-entry minimum24h and post-exit24h where enabled.\n'
 text+='- DD is native maximum relative **equity** drawdown, not a closed-balance proxy. Plot below is explicitly closed balance, so it omits floating excursions. Rates use calendar-month equivalents and Mon-Fri weekdays, not exact broker sessions. Win/loss streaks use cost-inclusive net cash.\n'
 text+='- Trade counts are small, especially recent six-month results. Older strategy-development history has been used in previous research; even new filter splits do not erase that prior exposure. Selection across eleven versions inflates optimism; no Monte Carlo, multiple-testing-adjusted significance, independent-broker validation or forward test completed here.\n'
 text+='- Each window starts flat with $10,000 and ends with tester liquidation of any remaining position; six-month results are a fresh simulation, not merely the last half of the yearly balance curve.\n'
 text+='- Historical swaps are tester broker specifications, not a verified point-in-time schedule. Generated ticks and modeled150ms delay cannot reproduce all real slippage.\n'
 flags=[(r['case'],{k:v for k,v in r['flags'].items() if v}) for r in rows if any(r['flags'].values())]
 text+=f'- Execution log flags: {flags if flags else "no invalid stops/volume, insufficient funds, stop-outs or market-closed errors detected"}.\n'
 coverage=[]
 for r in recent:
  coverage.extend(r['tick_coverage'])
 text+='\nRetained tick-coverage messages:\n\n'+ '\n'.join('- '+line.split('\t')[-1] for line in sorted(set(coverage)))+'\n'
 text+='''
Sources: [official native ADX buffers](https://www.mql5.com/en/docs/indicators/iadx); [official deal reasons and position IDs](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties); [real/generated tick behavior](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation). Account diagnosis comes from the local deal ledger, not the webpage screenshot.

## Closed-balance comparison

![Closed-balance comparison](balance-comparison.png)

Local evidence: `PROTOCOL.md`, `BUILD.json`, `PARITY.json`, `SELECTION.json`, `AUDIT.json`, `account-audit.json`, and per-case native reports/deal ledgers in `native/`. Private tester configurations and account deal files are not packaged or published. Normal MT5 and production packages were left untouched.
'''
 (ROOT/'REPORT.md').write_text(text,encoding='utf-8')
 fig,axes=plt.subplots(1,2,figsize=(13,4.7),layout='constrained')
 for ax,w in zip(axes,['1y','6m']):
  for v,color in [('baseline','#c95d5d'),(chosen,'#15857c')]:
   r=tests[f'{v}-{w}-m4'];ts=json.loads((ROOT/'native'/r['case']/'trades.json').read_text());dates=[datetime.strptime(r['start'],'%Y.%m.%d')];balance=[10000.]
   for t in ts:dates.append(datetime.fromisoformat(t['close_time']));balance.append(balance[-1]+t['net_profit'])
   ax.step(dates,balance,where='post',color=color,label=NAMES[v],linewidth=2)
  ax.axhline(10000,color='#777',ls=':',lw=1);ax.set_title('Recent year' if w=='1y' else 'Recent six months');ax.set_ylabel('Closed balance (USD)');ax.grid(alpha=.15);ax.tick_params(axis='x',rotation=25);ax.legend(fontsize=8,loc='best')
 fig.suptitle('XAU Slow Trend — native Model4, $10,000, nominal 1% risk\nClosed balance only; floating-equity drawdown is larger',fontsize=13)
 fig.savefig(ROOT/'balance-comparison.png',dpi=155);plt.close(fig)
 save=dict(selected=chosen,verdict=verdict,one_year_baseline=current1,one_year_candidate=new1,six_month_baseline=current6,six_month_candidate=new6,completed_tests=len(rows),unique_versions=audit['unique_parameter_vectors'])
 (ROOT/'SUMMARY.json').write_text(json.dumps(save,indent=2));print(json.dumps(save,indent=2))
if __name__=='__main__':main()
