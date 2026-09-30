# 3 Way Volume Profile — completed qualification and parameter search

**Conclusion: keep the raw gold breakout version for research. None of the optimized finalists passed validation. Nothing was deployed.**

Completed 415 native development optimization passes (385 distinct parameter vectors), nearby-parameter checks, three native validation runs and a matched raw validation run. A staged top-three search is not an exhaustive Cartesian search and does not prove a global optimum.

## 1. Longer-history raw qualification

| Version | 3y return | 3y PF | 5y return | 5y PF | 5y max equity DD | Decision |
|---|---:|---:|---:|---:|---:|---|
| BTCUSD REV | +34.31% | 1.09 | +25.95% | 1.04 | 38.35% | Did not qualify; no parameter search |
| XAUUSD BRK | +93.10% | 1.37 | +80.22% | 1.22 | 15.26% | Qualified; optimized |
| USDJPY ALL | +84.44% | 1.18 | +99.12% | 1.13 | 27.73% | Did not qualify; no parameter search |
| USDJPY BRK | +56.12% | 1.24 | +34.70% | 1.11 | 25.44% | Did not qualify; no parameter search |

The predeclared gate required positive return, PF >=1.15 and >=30 trades in BOTH 3y and 5y, plus beating the control. Gold beat the three-seed median random-control return/PF: -23.93% / 0.87 over 3y, -31.41% / 0.89 over 5y. Random controls use 2 ATR stops rather than structural stops; this is a sanity reference, not causal proof.

## 2. Fair out-of-development comparison

Same validation year: **26 September 2024 to 26 September 2025, end exclusive**. Native MT5 Model 4, $10,000, target 1% risk, 150ms configured delay. This older year has generated ticks, not broker real ticks.

| Version | Return | Net USD | Native PF | Whole-position win | Positions | Exit legs | Max equity DD | Longest W/L streak | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Raw M15 | +36.36% | $3,636.41 | 1.52 | 46.74% | 92 | 92 | 9.98% | 7/7 | Raw reference |
| Optimized finalist 1 | +2.15% | $214.89 | 1.07 | 53.23% | 62 | 95 | 8.81% | 4/7 | REJECT: PF below 1.15 |
| Optimized finalist 2 | +2.48% | $247.58 | 1.08 | 53.23% | 62 | 95 | 8.81% | 4/7 | REJECT: PF below 1.15 |
| Optimized finalist 3 | +2.48% | $247.58 | 1.08 | 53.23% | 62 | 95 | 8.81% | 4/7 | REJECT: PF below 1.15 |

Finalists 2 and 3 produced the same validation trades; they are not independent confirmations. Their only difference is the two-versus-three daily-entry cap.

**Win-rate warning:** the optimized finalists show 63.16% winning exit legs in the MT5 summary, but only 53.23% winning whole positions. Partial profit-taking splits a position into multiple exits; comparing that headline directly with the raw strategy would be misleading. Both figures and whole-position PF are preserved in FINAL RESULTS.json.

## 3. What was tested

| Development stage | Native passes | Best stage PF | Best stage return | Best stage equity DD |
|---|---:|---:|---:|---:|
| timeframe | 8 | 1.058 | +16.97% | 31.41% |
| entry | 15 | 1.085 | +17.05% | 13.41% |
| stop | 48 | 1.384 | +39.31% | 7.44% |
| trailing | 75 | 1.310 | +44.83% | 10.27% |
| rr_exit | 53 | 1.367 | +41.91% | 7.83% |
| session | 18 | 1.679 | +43.61% | 6.19% |
| direction | 9 | 1.679 | +43.61% | 6.19% |
| filters | 21 | 1.612 | +40.73% | 4.54% |
| management | 36 | 1.640 | +42.14% | 4.52% |
| profile | 51 | 1.394 | +48.37% | 6.33% |
| plateau | 81 | 1.463 | +58.56% | 5.82% |

Development window: 26 September 2021 to 26 September 2024. Development numbers are fitted results, not independent evidence.

Dimensions: eight timeframes; market/confirmation/limit/stop entries; structural/ATR/percent/fixed-price/signal/swing stops; seven trailing alternatives plus none; 0.5–6R and alternative exits; sessions, direction, filters, daily/position/holding limits; profile bins/value area/ATR/breakout/pullback parameters; 81 nearby-parameter cases. Exact vectors and rejected alternatives are in Optimization/SEARCH RESULTS.json.

News blackout was NOT tested: complete point-in-time calendar coverage was not verified. Signal-close and next-bar market entry are one causal implementation, not separate invented fills.

The development leaders converged on M30 breakout stop entries, a stop 0.5 ATR from the signal-time quote, 2R target, partial 50% close at 1R where lot rules permit, 1 ATR trailing starting at 1R, ATR-percentile filter and wider pullback proximity. These are rejected research candidates, not recommended live settings.

## 4. Integrity and limitations

- Raw parity passed twice: the qualification wrapper and optimization extensions with switches off reproduced the original 78 gold trades and all summary metrics.
- Both native builds compiled with zero errors and zero warnings. Native optimization XML contains every expected case index; per-batch source, binary, vector and report evidence is retained.
- Native cash-flow sums reconcile exactly to the report for all four validation runs. The position ledger allocates partial entry costs rounded to cents and can differ by a few cents; use native net P/L as authoritative.
- Trade-count-based development scoring includes partial exit legs, so partial-closing variants get an imperfect count advantage. Whole-position validation is reported separately; this does not rescue any failed finalist.
- Broker lots round upward; target 1% is not a strict maximum. The study uses saved Exness contract conditions and 1:2000 test leverage, not FTMO Swing margin rules.
- Broker real ticks begin January 2026. Older tests rely on generated ticks; historical slippage/order-book depth cannot be reconstructed. Fixed 150ms delay is not a guarantee of live fills.
- The reserved 2019–2021 holdout was NOT opened because all finalists failed validation. The already-inspected latest year is not an untouched holdout.
- No Monte Carlo/payout probabilities were generated for rejected candidates. No candidate passed the prerequisite validation gate. Additional measured cost stress and live forward evidence remain absent.
- No active terminal, live orders, BAT configuration, website, portfolio, or Git remote was changed.

## Decision

Do not replace raw gold breakout with these optimized variants. The higher exit-level win rate traded away too much profit and did not survive the separate validation year. BTC reversal and the two USDJPY versions remain unoptimized under the agreed longer-history cutoff.

## Evidence

- AUDITED RESULTS.md / AUDIT.json: full 3y/5y raw metrics, consistency, streaks, monthly records, controls and coverage.
- Optimization/SEARCH RESULTS.json: all development and plateau trials.
- Optimization/native/: per-batch source/binary snapshots, native XML/HTML, journals and exact parameters.
- FINAL RESULTS.json: reconciled validation comparison and monthly position/exit data.
- Optimization/PROTOCOL.md: frozen search rules, omissions and validation thresholds.

MT5 modes and command-line configuration: https://www.metatrader5.com/en/terminal/help/start_advanced/start
Maximum relative equity drawdown statistic: https://www.mql5.com/en/docs/constants/environment_state/Statistics
