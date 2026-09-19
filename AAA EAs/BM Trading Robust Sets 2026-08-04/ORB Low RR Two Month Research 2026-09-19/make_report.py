"""Build a readable comparison only after all frozen native runs reconcile."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def pct(value):
    return f'{value:+.2f}%'


def pf(row):
    if row['net_pf'] is None:
        return 'no losing trades' if row['net_wins'] else 'n/a'
    return f'{row["net_pf"]:.2f}'


def money(value):
    return ('-' if value<0 else '+')+f'${abs(value):,.2f}'


def main():
    results=json.loads((ROOT/'results.json').read_text())
    verification=json.loads((ROOT/'verification.json').read_text())
    verified={r['case']:r for r in verification}
    assert len(results)==21
    assert len(verified)==21 and {r['case'] for r in results}==set(verified)
    groups={}
    for row in results:
        groups.setdefault(row['ea'],{})[row['variant']]=row
    assert len(groups)==7 and all(set(g)=={'current','rr050','rr075'} for g in groups.values())
    lines=['# Seven active ORBs — below-1R comparison, latest two months','',
           'Window: **19 July–18 September 2026**. Each configuration starts separately with **$10,000** and a **1% current-equity risk input**. This is not a combined portfolio.',
           '', '## Side-by-side results','',
           'Numbers below are uninterrupted strategy results over the window, not a challenge cash balance after a breach or phase reset.', '',
           '| EA | Current target / return | 0.5R return / win rate | 0.75R return / win rate | Trades: current / 0.5R / 0.75R |',
           '|---|---:|---:|---:|---:|']
    for label,g in groups.items():
        a,b,c=g['current'],g['rr050'],g['rr075']
        lines.append(f'| {label} | {a["target_rr"]:g}R / {pct(a["return_pct"])} | {pct(b["return_pct"])} / {b["net_win_rate"]:.2f}% | {pct(c["return_pct"])} / {c["net_win_rate"]:.2f}% | {a["trades"]} / {b["trades"]} / {c["trades"]} |')
    low=[r for r in results if r['variant']!='current']
    passing=[r for r in low if r['ftmo_outcome']=='both_phases_passed']
    phase1=[r for r in low if r['phase_outcome']=='passed']
    failed=[r for r in low if r['ftmo_outcome'] in ('failed','verification_failed')]
    lines+=['','## FTMO rule replay','',
            f'Of the 14 below-1R configurations, **{len(passing)} completed both phases**, **{len(phase1)} reached the first-phase objective without an earlier breach**, and **{len(failed)} breached a modeled loss limit**.',
            '', '[Official FTMO 2-Step rules, checked 19 September 2026](https://ftmo.com/en/trading-objectives/): +10% Phase 1, +5% Verification, four entry days per phase, $500 daily equity-loss amount and $9,000 static equity floor on a $10K account. Days reset at Prague midnight. No two-month deadline is imposed.',
            '', 'Phase 2, when reached, is a fresh native test at $10K from the next business day. This optimistically assumes no additional administrative handover delay. Phase outcomes use the first target/breach timestamps; a later breach in an uninterrupted comparison does not invalidate an already completed phase.',
            '', '## Detailed statistics','',
            '| EA | Target | Trades | Net wins / losses | WR | Net USD | Net PF | Native max equity DD | Worst daily equity loss | Max initial price risk | Win/loss streak | Challenge outcome |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for row in results:
        tag='current' if row['variant']=='current' else 'comparison'
        lines.append(f'| {row["ea"]} | {row["target_rr"]:g}R ({tag}) | {row["trades"]} | {row["net_wins"]} / {row["net_losses"]} | {row["net_win_rate"]:.2f}% | {money(row["net_profit"])} | {pf(row)} | {row["equity_dd_pct"]:.2f}% | ${float(row["audit"]["worst_daily_loss"]):,.2f} | {row["max_initial_risk_pct"]:.2f}% | {row["longest_wins"]} / {row["longest_losses"]} | {row["ftmo_outcome"]} |')
    lines+=['','## Costs and monthly results','',
            '| EA / target | July partial net | August net | September partial net | Commission total | Swap total |',
            '|---|---:|---:|---:|---:|---:|']
    for row in results:
        months=json.loads((ROOT/'cases'/row['case']/'months.json').read_text())
        bymonth={m['month']:m for m in months}
        vals=[money(bymonth.get(m,{}).get('net_profit',0)) for m in ('2026-07','2026-08','2026-09')]
        lines.append(f'| {row["ea"]} / {row["target_rr"]:g}R | '+ ' | '.join(vals)+f' | {money(row["commission"])} | {money(row["swap"])} |')
    lines+=['','## Known tick-gap exposure','',
            'The tester reports two entire days without real ticks: **14 and 15 September 2026**. It generated ticks from bars for those days. The counts below identify entries on those dates; they do not assert that every other minute has complete ticks. No trades are removed from the comparison.',
            '', '| EA | Entries on full-gap dates: current / 0.5R / 0.75R |',
            '|---|---:|']
    for label,g in groups.items():
        counts=[verified[g[v]['case']]['entries_on_known_full_tick_gap_days'] for v in ('current','rr050','rr075')]
        lines.append(f'| {label} | '+ ' / '.join(str(c) for c in counts)+' |')
    lines+=['','## Interpretation and limitations','',
            '- Seven configurations came from the active installer: two gold Volume Profile variants, gold New York M30, gold London/NY overlap M30, US100 New York M30, US100 H1 13UTC, and US100 Selective ORB V3. Archived raw research ORBs were not included.',
            '- Entry logic, initial stop logic, breakeven/trailing and session rules are unchanged across each EA\'s three runs. Only TP RR is changed, with risk input standardized to 1% and the portfolio adaptive overlay disabled.',
            '- The two Volume Profile versions retain Dynamic 50/20 management. It references TP distance: 0.5R brings its trigger to 0.25R and lock to 0.10R; 0.75R brings them to 0.375R and 0.15R. The code evaluates the closed M15 candle; these are thresholds, not guaranteed exit prices.',
            '- These EAs retain the current round-up/minimum-lot sizing policy. Therefore 1% is an INPUT, not a hard risk cap. Actual initial price risk is shown above, and fees/slippage can increase the eventual loss further. This differs from the saved Nasdaq executable, which rounded down.',
            '- All runs use the isolated Exness-MT5Trial16 tester, model 4 (real-tick mode), not the connected FTMO account. MT5 can generate ticks where real ticks are absent; diagnostics are retained per case. A 100% history-quality report is not a certificate of 100% real ticks.',
            '- Spread and historical fill-price gaps are reflected in native fills. Native recorded commission and swap are included in every trade\'s net P/L. No additional latency/slippage stress was applied (execution delay 0).',
            '- Tester leverage is configured at 1:30, but Exness symbol-specific margin specifications still apply. This is not verified FTMO Swing execution/margin behavior.',
            '- A read-only audit wrapper observes native tester equity before and after strategy tick/timer events. It records floating daily equity losses, Prague-day resets and first rule/target timestamps without changing trade decisions.',
            '- This is a short, user-selected historical window. Ranking the alternatives here is hindsight comparison, not optimization, a passing probability estimate, or evidence of future profitability.',
            '- No production EA, installer/BAT, website, active portfolio or live trade was changed. Research-only sources, case inputs, reports and ledgers were saved.',
            '', '## Evidence','',
            '`results.json` contains all summaries. Each `cases/<case>/` contains its native MT5 HTML report, full inputs, reconciled `trades.json`, `months.json`, `daily-equity.csv` and `tester-journal.txt`. `frozen-plan.json` records the comparison scope. `verification.json` records independent cash/equity reconciliation, unchanged source-set hashes, tick-gap exposure and observed native margin.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[:22]))


if __name__=='__main__':
    main()
