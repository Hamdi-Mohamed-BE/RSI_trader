"""Generate the comparison from verified native evidence; no terminal access."""
from pathlib import Path
import gzip, hashlib, json

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
rows = json.loads((ROOT/'RESULTS.json').read_text())
assert len(rows) == 8
config = json.loads((ROOT/'run-config.json').read_text())
selection = json.loads((BASE/'Nasdaq 5M DI ATR Deployment 2026-09-28/SELECTION.json').read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(BASE/selection['expert']) == config['binary_sha256'] == selection['expert_sha']
assert digest(BASE/selection['settings']) == selection['settings_sha']
assert [k for k,v in config['inputs']['DI_ON'].items() if v!=config['inputs']['DI_OFF'][k]] == ['InpRequireDIAgreement']

table = ['| Window | DI | Return | Win rate | PF | Max equity DD | Trades (per month / weekday) | Max W / L streak |',
         '|---|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
    m=r['metrics']; f=r['trade_frequency']; s=r['net_streaks']
    table.append(f"| {r['period']} | {'ON — current' if r['variant']=='DI_ON' else 'OFF'} | {m['return_pct']:+.2f}% | {m['win_rate_pct']:.2f}% | {m['profit_factor']:.2f} | {r['equity_relative_dd_pct']:.2f}% | {m['trades']} ({f['per_month']:.2f} / {f['per_weekday']:.2f}) | {s['win']['max']} / {s['loss']['max']} |")

deltas=[]; overlap=[]
for period in config['periods']:
    on=next(r for r in rows if r['period']==period and r['variant']=='DI_ON')
    off=next(r for r in rows if r['period']==period and r['variant']=='DI_OFF')
    # Every input reported by MT5, not merely the submitted subset, must differ only in DI.
    changed=[k for k in on['actual_inputs'] if on['actual_inputs'][k]!=off['actual_inputs'].get(k)]
    assert changed==['InpRequireDIAgreement'], (period, changed)
    m,n=on['metrics'],off['metrics']
    deltas.append(f"- **{period}, DI OFF minus DI ON:** return {n['return_pct']-m['return_pct']:+.2f} percentage points; win rate {n['win_rate_pct']-m['win_rate_pct']:+.2f} points; PF {n['profit_factor']-m['profit_factor']:+.2f}; equity DD {off['equity_relative_dd_pct']-on['equity_relative_dd_pct']:+.2f} points; trades {n['trades']-m['trades']:+d}.")
    entries=[]
    for r in (on,off):
        ts=json.loads(gzip.decompress((ROOT/'native'/r['case']/'trades.json.gz').read_bytes()))
        entries.append({(t['open_time'],t['side']) for t in ts})
    a,b=entries
    overlap.append(f"- {period}: {len(a&b)} common entry-time/direction pairs; {len(b-a)} only DI OFF; {len(a-b)} only DI ON. Different holdings can change subsequent eligible entries.")

parity=[f"- {r['period']}: exact archived trade parity = {r['archived_comparison']['exact_trade_parity']}; net P&L difference ${r['archived_comparison']['net_profit_difference']:.2f}." for r in rows if r['variant']=='DI_ON']
costs=[f"- {r['period']} {r['variant']}: commission ${r['recorded_commission']:.2f}, swap ${r['recorded_swap']:.2f}, stop-modification-failure messages {r['stop_modification_failures']}, upward lot-rounding messages {r['lots_rounded_up_messages']}." for r in rows]
drawdowns=[f"- {r['period']} {r['variant']}: maximum relative equity DD {r['equity_relative_dd_pct']:.2f}%; percentage accompanying maximum cash DD (website field) {r['metrics']['max_drawdown_pct']:.2f}%." for r in rows]

content='''# Nasdaq 5M — DI ON versus DI OFF

Both versions use the same selected executable, wider stop and ATR trailing. The only changed input is `InpRequireDIAgreement` (true → false). No other tuning and no live deployment.

## Test basis

$10,000 starting balance; planned 1% of current equity per trade; USTEC M5; 0.60%-of-price initial stop; 6×ATR14 trailing after +1R; no fixed take profit; overnight holding allowed. MT5 Model 4 with 150 ms execution delay, identical broker feed and costs. Actual risk can exceed 1% because the existing EA rounds lots upward to the broker's valid step/minimum. This is standalone performance, not the adaptive/FTMO portfolio allocation.

All windows end **2026-09-25 exclusive** to match published evidence: 6m begins 2026-03-25, 1y 2025-09-25, 3y 2023-09-25, 5y 2021-09-25. Today’s 28 September move is NOT in these results. Weekday frequency includes all Monday–Friday dates, including holidays with no entry; it is not one guaranteed trade every day.

## Native results

'''+ '\n'.join(table)+'''

Win rate and PF are the native MT5 report fields. Streaks are calculated from net closed-trade P&L after recorded costs; a flat trade resets a streak. Equity DD is the report's **maximum relative** drawdown, not merely the percentage at the largest cash drawdown.

## Effect of removing DI

'''+ '\n'.join(deltas)+'''

## Entry overlap

'''+ '\n'.join(overlap)+'''

## Replay of currently published version

'''+ '\n'.join(parity)+'''

## Execution and evidence limitations

- Real ticks start in January 2026 on this feed. The 1y/3y/5y runs include generated older history even though Model 4 was selected. Do not label all five years real-tick evidence.
- Spreads are embedded in fills. The tester recorded the commission/swap below; zero recorded commission does not mean every broker charges zero. A 150 ms delay is not a guarantee of live slippage, latency or news execution.
- The windows overlap and have already been examined. This is a retrospective two-configuration comparison, not independent out-of-sample proof, a full optimization, or an FTMO pass-probability estimate.
- Trailing-stop modification failures are counted below rather than hidden. The tested production executable is unchanged; both versions share its management implementation.
- One initial replay completed in the terminal, but the wrapper searched the wrong output directory. The report-path wrapper was corrected and that identical replay repeated; no trading parameters were changed. There are two distinct parameter configurations, eight verified final cases, and one extra execution of the same six-month DI-on control.
- All submitted inputs were checked against the reports; all reported inputs differ only in DI within each pair. Closed-trade counts and net P&L reconcile with the native summaries. Current selected binary and preset hashes are unchanged.

### Recorded costs / journal diagnostics

'''+ '\n'.join(costs)+'''

### Drawdown metric cross-check

'''+ '\n'.join(drawdowns)+'''

## Files

`run-config.json` freezes the comparison; `RESULTS.json` includes verified metrics and inputs; `native/` contains compressed MT5 reports and trade ledgers. Private tester INIs are excluded from Git. `run.py` runs tests; `report.py` builds this report without terminal access.
'''
(ROOT/'REPORT.md').write_text(content,encoding='utf-8')
print('\n'.join(table))
print('\n'.join(deltas))
print('Exact archived parity:',all(r['archived_comparison']['exact_trade_parity'] for r in rows if r['variant']=='DI_ON'))
print('Active selected binary and SET unchanged.')
