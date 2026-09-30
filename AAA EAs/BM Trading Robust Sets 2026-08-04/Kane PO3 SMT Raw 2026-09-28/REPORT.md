# Trader Kane PO3 / SMT — raw research result

28 September 2026. Decision: **REJECT for deployment. No raw candidate passed the long-window gate.**

This tests explicitly labelled mechanical approximations of the supplied interview, not Kane’s complete discretionary model, claimed payouts or trading record. His intuition, swing selection and exceptions cannot be recovered from the transcript. USTEC/US500 are Exness CFDs, not NQ/ES futures.

## What survived scrutiny

- Daily/H4/H1 location plus SMT improved on the very weak basic control, but the effect was not enough for long-window profitability.
- Structural breakeven reduced drawdowns and five-year losses, while reducing recent profits. That is a risk/return trade-off, not evidence of a profitable edge.
- The static and 1R variants happened to have identical one-year net outcomes despite eight 1R stop modifications; a modification does not necessarily change the eventual exit.
- All aligned variants made zero simulated eligible payout requests across the tested account horizons. Low trade frequency and conservative account constraints matter.

## Frozen implementation

10:00–11:30 New York entries, M3 closed-candle inversion, paired previous-hour sweep divergence, prior-day midpoint and custom 06:00–10:00 H4 range context. Stop beyond the current-hour extreme; target combined prior/current-hour midpoint; maximum two entries daily; flat at noon. Both directions, no PM discretionary re-entry or runner.

The midpoint is an arithmetic level, not a guarantee of fair value or a required market destination. Exact assumptions and deviations from the interview are in [RULES.md](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/RULES.md>). Four variants were frozen before outcomes; no losing rule was optimized afterwards.

## Native tester performance

Each case starts with $10,000 and targets fixed $100 initial stop-risk, rounded down to lot step; fills may change actual risk slightly. Native broker spread/costs and 150ms execution delay. Research leverage is not prop-account leverage. PF is computed from complete net position outcomes. Win rate includes tiny net-positive BE exits. DD is MT5 equity peak-relative drawdown.

Frequency per day uses all weekdays in the window, not only days with a trade, and is not a promise of daily opportunities. Window end: 27 September 2026; start dates are in the table headings.

### 6 months — 27 March 2026; Model 4

| Version | Trades | /month | /weekday | Return | PF | Win % | Equity DD % | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sweep/inversion control | 73 | 12.08 | 0.557 | 1.65% | 1.04 | 47.95 | 8.04 | 4/8 |
| Aligned SMT — static | 11 | 1.82 | 0.084 | 6.43% | 3.07 | 72.73 | 2.58 | 6/2 |
| Aligned SMT — structural BE | 11 | 1.82 | 0.084 | 3.88% | 2.85 | 45.45 | 1.57 | 3/3 |
| Aligned SMT — 1R BE | 11 | 1.82 | 0.084 | 6.43% | 3.07 | 72.73 | 2.58 | 6/2 |

### 1 year — 27 September 2025; Model 4, mixed ticks

| Version | Trades | /month | /weekday | Return | PF | Win % | Equity DD % | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sweep/inversion control | 158 | 13.18 | 0.608 | -15.55% | 0.82 | 42.41 | 25.16 | 4/8 |
| Aligned SMT — static | 25 | 2.08 | 0.096 | 4.55% | 1.40 | 56.00 | 5.80 | 6/3 |
| Aligned SMT — structural BE | 25 | 2.08 | 0.096 | 3.75% | 1.60 | 52.00 | 3.30 | 3/3 |
| Aligned SMT — 1R BE | 25 | 2.08 | 0.096 | 4.55% | 1.40 | 56.00 | 5.80 | 6/3 |

### 3 years — 27 September 2023; Model 1 screen

| Version | Trades | /month | /weekday | Return | PF | Win % | Equity DD % | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sweep/inversion control | 427 | 11.86 | 0.545 | -48.85% | 0.79 | 42.15 | 58.27 | 5/8 |
| Aligned SMT — static | 47 | 1.31 | 0.060 | -1.62% | 0.94 | 46.81 | 10.85 | 6/6 |
| Aligned SMT — structural BE | 50 | 1.39 | 0.064 | -1.63% | 0.90 | 68.00 | 8.45 | 6/3 |
| Aligned SMT — 1R BE | 47 | 1.31 | 0.060 | 0.08% | 1.00 | 51.06 | 9.12 | 6/3 |

### 5 years — 27 September 2021; Model 1 screen

| Version | Trades | /month | /weekday | Return | PF | Win % | Equity DD % | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sweep/inversion control † | 724 | 12.07 | 0.555 | -100.03% | 0.75 | 41.85 | 100.03 | 6/9 |
| Aligned SMT — static | 78 | 1.30 | 0.060 | -11.01% | 0.75 | 43.59 | 21.97 | 6/6 |
| Aligned SMT — structural BE | 84 | 1.40 | 0.064 | -4.98% | 0.82 | 67.86 | 13.24 | 10/4 |
| Aligned SMT — 1R BE | 78 | 1.30 | 0.060 | -9.48% | 0.78 | 46.15 | 20.44 | 6/6 |

† The five-year control exhausted its native research balance; final recorded exit 2026-07-23T15:22:40+00:00. Its full-window trade opportunity count and profitability comparison are not valid after exhaustion. The small negative balance is the tester outcome, not an approved prop loss allowance.

Gate: positive net, PF >=1.15, >=30 trades, and outperform the named viable control on BOTH three and five years. Static and structural BE fail profitability; 1R BE barely breaks even on three years (PF about 1.004) and loses on five years. Even ignoring the exhausted five-year control, all candidates fail their own profitability/PF conditions.

No long Model4 confirmation, stage-5 parameter optimization, promotion Monte Carlo, portfolio addition or production build was performed after this failure. Model1 screens are not marketed as real-tick proof.

## Breakeven changes

Recorded one-way stop modifications (performance is shown in the complete tables above):

- Aligned SMT — static, 1y: 0 stop modifications across 25 entries.
- Aligned SMT — static, 5y: 0 stop modifications across 78 entries.
- Aligned SMT — structural BE, 1y: 17 stop modifications across 25 entries.
- Aligned SMT — structural BE, 5y: 50 stop modifications across 84 entries.
- Aligned SMT — 1R BE, 1y: 8 stop modifications across 25 entries.
- Aligned SMT — 1R BE, 5y: 16 stop modifications across 78 entries.

Stops only moved toward reduced risk, with a fee/spread allowance. They cannot guarantee a zero-loss exit. Early exits can free a slot for a second trade, so the five-year comparison includes changed opportunity availability (84 structural-BE entries versus 78 static), not just repricing an identical ledger.

## Standalone planned-account replay

Offline replay of the ONE-YEAR native opportunity stream, with smaller lots, target-account leverage, conservative margin/risk limits and withdrawal rules. This is not a test on either firm’s server. [Account rules, sources and assumptions](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/PROP_RULES.md>) are part of these results.

**Aligned SMT static, structural BE and 1R BE: 0 payouts, 0 FTMO phase-one passes and 0 modeled loss-limit breaches in all tested 30/60/120/180-day base and stress replays.** The result is unresolved, not successfully funded. Instant accounts begin directly funded; that status is not an achievement in this table.

There are 48 / 44 / 35 / 27 matured weekly starts at 30 / 60 / 120 / 180 days. Starts overlap and are not independent future-probability estimates.

### 180-day account scenarios

| Version | Account | Costs | Starts | Phase 1 / 2 passes | Payouts | Loss breaches | Compliance blocks | Mean eligible cash |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Sweep/inversion control | FTMO | Base | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Sweep/inversion control | FTMO | Stress | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Sweep/inversion control | Instant | Base | 27 | n/a | 2 | 0 | 0 | $3.18 |
| Sweep/inversion control | Instant | Stress | 27 | n/a | 1 | 0 | 0 | $1.35 |
| Aligned SMT — static | FTMO | Base | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Aligned SMT — static | FTMO | Stress | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Aligned SMT — static | Instant | Base | 27 | n/a | 0 | 0 | 0 | $0.00 |
| Aligned SMT — static | Instant | Stress | 27 | n/a | 0 | 0 | 0 | $0.00 |
| Aligned SMT — structural BE | FTMO | Base | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Aligned SMT — structural BE | FTMO | Stress | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Aligned SMT — structural BE | Instant | Base | 27 | n/a | 0 | 0 | 0 | $0.00 |
| Aligned SMT — structural BE | Instant | Stress | 27 | n/a | 0 | 0 | 0 | $0.00 |
| Aligned SMT — 1R BE | FTMO | Base | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Aligned SMT — 1R BE | FTMO | Stress | 27 | 0/0 | 0 | 0 | 0 | $0.00 |
| Aligned SMT — 1R BE | Instant | Base | 27 | n/a | 0 | 0 | 0 | $0.00 |
| Aligned SMT — 1R BE | Instant | Stress | 27 | n/a | 0 | 0 | 0 | $0.00 |

The weak control sometimes makes a small Instant withdrawal in a favourable subperiod. This does not repair its negative full-period expectancy or qualify it for use. Cash excludes purchase, reset, add-on fees, tax and actual approval/processing delay.

### Entire-year account-risk diagnostic (no withdrawals or evaluation phases)

| Version | Account | Costs | Accepted trades | /month | /weekday | Net return | PF | Win % | Equity-envelope DD % | Max W/L | Margin rejects |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aligned SMT — 1R BE | FTMO | Base | 20 | 1.67 | 0.077 | 3.59% | 2.00 | 65.00 | 1.94 | 6/2 | 5 |
| Aligned SMT — 1R BE | FTMO | Stress | 20 | 1.67 | 0.077 | 2.08% | 1.51 | 65.00 | 2.17 | 6/2 | 5 |
| Aligned SMT — 1R BE | Instant | Base | 9 | 0.75 | 0.035 | 1.19% | 3.41 | 77.78 | 0.70 | 3/1 | 16 |
| Aligned SMT — 1R BE | Instant | Stress | 9 | 0.75 | 0.035 | 0.76% | 2.37 | 77.78 | 0.77 | 3/1 | 16 |
| Aligned SMT — static | FTMO | Base | 20 | 1.67 | 0.077 | 3.59% | 2.00 | 65.00 | 1.94 | 6/2 | 5 |
| Aligned SMT — static | FTMO | Stress | 20 | 1.67 | 0.077 | 2.08% | 1.51 | 65.00 | 2.17 | 6/2 | 5 |
| Aligned SMT — static | Instant | Base | 9 | 0.75 | 0.035 | 1.19% | 3.41 | 77.78 | 0.70 | 3/1 | 16 |
| Aligned SMT — static | Instant | Stress | 9 | 0.75 | 0.035 | 0.76% | 2.37 | 77.78 | 0.77 | 3/1 | 16 |
| Aligned SMT — structural BE | FTMO | Base | 20 | 1.67 | 0.077 | 2.08% | 2.01 | 50.00 | 1.50 | 3/5 | 5 |
| Aligned SMT — structural BE | FTMO | Stress | 20 | 1.67 | 0.077 | 1.02% | 1.40 | 35.00 | 1.70 | 2/6 | 5 |
| Aligned SMT — structural BE | Instant | Base | 9 | 0.75 | 0.035 | 0.91% | 4.54 | 55.56 | 0.60 | 3/3 | 16 |
| Aligned SMT — structural BE | Instant | Stress | 9 | 0.75 | 0.035 | 0.60% | 2.90 | 44.44 | 0.66 | 3/4 | 16 |
| Sweep/inversion control | FTMO | Base | 48 | 4.00 | 0.185 | -7.69% | 0.48 | 35.42 | 8.11 | 2/6 | 12 |
| Sweep/inversion control | FTMO | Stress | 34 | 2.83 | 0.131 | -7.44% | 0.34 | 38.24 | 7.82 | 2/6 | 7 |
| Sweep/inversion control | Instant | Base | 129 | 10.75 | 0.496 | -2.85% | 0.74 | 42.64 | 3.98 | 7/7 | 21 |
| Sweep/inversion control | Instant | Stress | 103 | 8.58 | 0.396 | -4.79% | 0.42 | 39.81 | 4.79 | 4/6 | 14 |

Account-envelope DD is measured as a percentage of initial capital, unlike the native peak-relative DD. The 10:00 NY entry window makes an incomplete news calendar particularly important for Instant: the replay has only 29 existing event timestamps. Cost stress uses explicit hypothetical haircuts, not measured target-broker execution.

## Data coverage and verification

- 20 completed native cases: four short smoke tests plus sixteen raw-window tests. Clean compile, 18 unit tests passed, cash reconciled to native deals and reports.
- Independent pre-existing M1 archives reconstructed 520 recorded decisions, with 9880 comparisons and zero mismatches. This overlapping archive ends 2026-08-10T00:00:00+00:00; repeated-window records are not independent observations.
- Six-month vs matching one-year trades reconcile exactly for all four variants, including prices, stops, target, lot size and cash.
- Actual real ticks for both symbols begin 1 January 2026. Six-month report quality is 100% real ticks; one-year and smoke percentages below include warm-up periods. Do not describe the entire one-year trade history as real ticks.

| Version | Smoke report quality | 6m report quality | 1y report quality |
|---|---|---|---|
| Sweep/inversion control | 62% real ticks | 100% real ticks | 63% real ticks |
| Aligned SMT — static | 62% real ticks | 100% real ticks | 63% real ticks |
| Aligned SMT — structural BE | 62% real ticks | 100% real ticks | 63% real ticks |
| Aligned SMT — 1R BE | 62% real ticks | 100% real ticks | 63% real ticks |

Older reference data are incomplete. The EA safely skipped insufficient reference windows or mismatched paired candles; it did not fabricate confirmation. Each variant rejected 80 reference checks in one year; 130 reference plus 58 synchronization checks in three years; 160 plus 148 in five years. These are repeated M3 checks, not unique missing days. Six-month checks had none. Execution verification passes, but complete-reference-history verification is explicitly FALSE.

- 3 tester connection/authorization failures were retained as rejected infrastructure attempts; only fresh reports with correct input hashes and cash reconciliation count. A process-level lease was added to the runner to serialize later batches.
- No invalid volume/stops or unexplained order failure occurred in successful runs. The control capital-exhaustion warning is preserved and disqualifying.
- Live MT5 PID 11196 and its creation timestamp are unchanged; no live API was used. Tracked Git diff remains empty; only dated research artifacts and the isolated tester were used.

## Files

- [Frozen rules](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/RULES.md>) and [configuration](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/run-config.json>)
- [Raw results](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/RAW_RESULTS.json>), [account replay results](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/NATIVE_PROP.json>), [gate decision](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/SELECTION.json>)
- [Verification](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/VERIFICATION.json>), [independent history audit](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/HISTORY_AUDIT.json>), [test results](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Kane PO3 SMT Raw 2026-09-28/TEST_RESULTS.txt>)
- Tester-only source/binary plus per-case native report, deals, groups, signal and management logs in this folder. They refuse operation outside Strategy Tester.

Bottom line: keep the research, not the deployment. Recovering exact discretionary range selection would require additional source material or an explicit new research protocol; it is not legitimate to present these failed proxies as Kane’s full strategy.
