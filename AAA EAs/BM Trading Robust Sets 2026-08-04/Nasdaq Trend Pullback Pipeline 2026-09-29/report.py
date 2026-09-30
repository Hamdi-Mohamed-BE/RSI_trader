"""Build a review report from verified native evidence; no further backtesting."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


def table(rows):
    text = '| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |\n'
    text += '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        m = r['metrics']
        label = r['window'] + (' control' if r['control'] else ' strategy')
        text += f"| {label} | {m['trades']} | {m['trades_per_month']:.2f} | {m['trades_per_eligible_day']:.3f} | {m['return_pct']:+.2f}% | {m['profit_factor']:.3f} | {m['win_rate_pct']:.1f}% | {m['equity_dd_pct']:.2f}% | {m['win_streak']}/{m['loss_streak']} | {m['mean_net_R']:.3f} |\n"
    return text


def main():
    results = json.loads((ROOT / 'RESULTS.json').read_text())
    gate = json.loads((ROOT / 'GATE.json').read_text())
    verification = json.loads((ROOT / 'VERIFICATION.json').read_text())
    carries = json.loads((ROOT / 'CARRYOVER_AUDIT.json').read_text())['positions']
    rows = results['runs']
    assert verification['passed']
    assert gate['status'] == 'RAW_GATE_REJECTED', 'Review wording before a different decision'
    get = lambda w, c=False, model=4: next(r for r in rows if (r['window'],r['control'],r['model']) == (w,c,model))
    five, three = get('5y'), get('3y')
    fm, tm = five['metrics'], three['metrics']
    carry = [x for x in carries if x['tag'] == five['tag']]
    txt = '# Nasdaq trend-pullback — pipeline review\n\n'
    txt += '**Decision: stop at the raw qualification gate. No optimized winner or live-ready version.** Gold remains unchanged. Bitcoin and GBPUSD have not been advanced.\n\n'
    txt += f"The unchanged Nasdaq H1 strategy returned **{fm['return_pct']:+.2f}% over five years**, but its profit factor was only **{fm['profit_factor']:.3f}**, below the required 1.15. The three-year result was weaker: **{tm['return_pct']:+.2f}%**, PF **{tm['profit_factor']:.3f}**, and below the frozen random-direction control. Recent strength does not erase the long-period failure. These are historical simulations, not expected future returns.\n\n"
    txt += '## Confirmed results\n\n'
    txt += 'Native MT5 Model 4; Exness USTEC CFD, not NQ futures. USD 10,000 starting balance, nominal 1% equity risk rounded UP, broker-model costs and 150ms simulated execution delay. All periods end 2026-09-27 exclusive. The 3y/5y confirmations are new; the 6m/1y results are reused unchanged from the original study.\n\n'
    txt += table([get(w) for w in ['5y','3y','1y','6m']])
    txt += '\nThe five-year window starts 2021-09-27; three years starts 2023-09-27; one year starts 2025-09-27; six months starts 2026-03-27. These overlapping, previously seen periods are not independent validations or untouched holdouts. /month uses elapsed calendar months (days / 30.4375); /day uses eligible quoted weekdays during the entry window, not only days with a trade. Streaks use net position P&L after recorded fees. Equity DD is the native report’s floating-equity relative maximum; it is not closed-balance DD.\n\n'
    txt += '## Control comparison\n\n'
    txt += 'The control retains the same qualifying opportunities, stop/target distances and sizing, but randomizes direction using the original frozen seed 290929. Every entry date matched; timing differences are recorded in RESULTS.json. Compare mean net R as well as cash because compounding paths differ. This tests the direction signal conditional on selected opportunities, not whether the selected entry times themselves outperform random times. One seed is not a significance test.\n\n'
    txt += table([get(w, True) for w in ['5y','3y','1y','6m']])
    txt += '\nRaw gate failures:\n\n'
    txt += ''.join('- ' + failure + '.\n' for failure in gate['failures'])
    txt += '\nEven if the carryover warnings were waived, the strategy still fails the performance gate. The conclusion is about this frozen implementation, not every Nasdaq trend strategy.\n\n'
    txt += '## Why the numbers differ from the earlier screen\n\n'
    txt += 'The original +58.66% headline used the faster one-minute-OHLC Model 1 screen. Below are the retained screens, not new parameter variants. Model 4 changes the intrabar path and modeled execution; the EA and inputs were not changed.\n\n'
    txt += table([get(w,c,1) for w in ['5y','3y'] for c in [False,True]])
    txt += '\n## Execution and overnight carryovers\n\n'
    txt += f"The five-year Model 4 strategy had **{len(carry)} positions closing more than two minutes past the eight-hour/20:00 UTC deadline**, including **{five['flags']['overnight_positions']} crossing a UTC date** and {five['flags']['swap_positions']} with nonzero swap. The longest hold was **{fm['max_hold_hours']:.2f} hours**. Native entry failures, close failures, invalid stops/volume and stopouts were zero; that does not make these carryovers acceptable for a strict intraday mandate. All of these delayed exits closed within one second of the first recorded minute trace at/after their deadline. The table lists the cross-date cases; the full audit also lists same-day delays.\n\n"
    txt += 'The unchanged EA closes on ticks and consults the broker’s weekday session schedule. Archived minute equity traces show whether there was tester activity around the intended deadlines. Gaps in that trace support missing modeled quote activity, but do not establish the exact holiday cause or prove a live fill would have been available. The session API describes sessions by weekday; it does not supply a full dated historical holiday calendar. [Official session API](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade).\n\n'
    txt += '| Position | Open UTC | Close UTC | Hours held | Minute-trace gap across deadline (h) | Net P&L | Swap |\n|---|---|---|---:|---:|---:|---:|\n'
    for x in carry:
        if not x['crossed_utc_date']:
            continue
        txt += f"| {x['position_id']} | {x['open_utc']} | {x['close_utc']} | {x['hours_held']:.2f} | {x['minute_trace_gap_hours']:.2f} | ${x['net_profit']:+.2f} | ${x['swap']:+.2f} |\n"
    txt += '\nAll carryovers and their P&L remain in the results. No hindsight removal, invented session-end fills or schedule fix was applied. Correcting this would require an explicitly specified new execution variant and separate validation. The complete timestamp audit covers both models and all windows; overlapping windows repeat the same historical situations.\n\n'
    txt += f"Five-year initial stop risk: median **{fm['median_initial_risk_pct']:.3f}%**, maximum **{fm['max_initial_risk_pct']:.3f}%** of entry equity. Lot rounding and fills explain departure from the 1% target. Gaps and costs can increase realized loss further. Five-year closed-balance DD was **{fm['balance_dd_pct']:.2f}%**, versus native floating-equity DD **{fm['equity_dd_pct']:.2f}%**.\n\n"
    txt += '## Data limitations\n\n'
    txt += 'The broker journal says recorded real ticks begin 2026-01-01. Model 4 is therefore mixed real/generated history, not five years of recorded real ticks. MT5 generates ticks when minute bars exist but their tick records are absent. [Official real/generated tick documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).\n\n'
    for w in ['5y','3y','1y','6m']:
        txt += f"- {w} strategy native history label: {get(w)['metrics']['history_quality']}.\n"
    txt += '\nThese labels include the 90-day warm-up, not just the trading window. Broker-specific spread, swap and commission modeling is not a verified historical fee time series. The 150ms setting is a simulation, not measured live slippage. No inference about another broker, futures contract or prop-firm account is warranted.\n\n'
    txt += '## Pipeline status and verification\n\n'
    txt += f"- Stages 1–2: original frozen rules and tester-only binary reused without strategy edits; original source, EX5, rules and configuration hashes matched.\n- Stage 3: four new serial long-window native confirmations plus eight retained raw/control screen and recent-period runs.\n- Verification: **{verification['signal_checks']:,} causal signal checks**, including **{verification['fresh_signal_checks']:,}** on fresh tests, with zero mismatches; deal/report cash, complete close volumes, risk sizing, input dates and matched-control dates reconciled. Repeated signals across overlapping tests are not independent observations.\n- Stage 4: **failed**. No further parameter trials, optimized SET, Monte Carlo, FTMO simulation or promotion. Those stages were not completed and no robustness claim is made.\n- Gold, the separately deployed Nasdaq 5-minute bot, installers, website and live trading were not changed.\n\n"
    txt += 'The canonical pipeline says to stop on a raw failure. Exploratory optimization would require an explicit override and would remain research, not validation of this failed baseline. **Awaiting user review before any next asset or exception.**\n\n'
    txt += 'Evidence: [frozen protocol](PROTOCOL.md), [full results](RESULTS.json), [gate](GATE.json), [verification](VERIFICATION.json), [carryover audit](CARRYOVER_AUDIT.json), [provenance](PROVENANCE.json). Private tester connection INIs are not intended for sharing.\n'
    (ROOT / 'REPORT.md').write_text(txt, encoding='utf-8')
    print(json.dumps(dict(report=str(ROOT/'REPORT.md'), gate=gate['status'], five_year=fm, three_year=tm), indent=2))


if __name__ == '__main__':
    main()
