# XAU Slow Trend — weekly entry limit results

29 September 2026. Isolated research only. **Active MT5, installed EA, portfolio and website were not changed.**

## Outcome

Selected on the older development/validation windows, before any new recent tests: **ADX/DI + seven-day cooldown**. Older-window eligibility passed: **True**. The older-window selection still loses in at least one recent window: no deployment recommendation.

The highest recent six-month return among the four weekly variants was **Seven-day entry cooldown**: **+1.57%**, PF **1.10**, **14 trades**. Its older three-year result was **+0.92%**, PF **1.01**. Reporting this retrospective winner is not a new selection or proof of a durable edge.

This follow-up is exploratory after the previous ADX study failed the latest six months. Those periods and the baseline were already seen; do not call this a fresh holdout, an optimized production bot, or a completed full validation pipeline. We tested four predefined variants, without weekday selection, stop/target changes or increased position risk.

## Recent six months — all variants, native Model4

2026-03-27 to 2026-09-27 (end exclusive). Same USD10,000 start and nominal 1% risk. “Once/week” is a maximum, not an instruction to force trades.

| Version | Return | PF | Equity DD | Win rate | Trades / month / weekday | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|
| Current rules | -12.14% | 0.43 | 20.23% | 10.53% | 19 / 3.14 / 0.145 | 1 / 14 |
| ADX/DI + rising ADX | -15.92% | 0.47 | 18.52% | 11.54% | 26 / 4.30 / 0.198 | 2 / 15 |
| Once/calendar week | -11.64% | 0.45 | 16.60% | 10.53% | 19 / 3.14 / 0.145 | 1 / 11 |
| Seven-day entry cooldown | +1.57% | 1.10 | 11.10% | 21.43% | 14 / 2.32 / 0.107 | 2 / 7 |
| ADX/DI + once/week | -11.35% | 0.38 | 13.50% | 6.67% | 15 / 2.48 / 0.115 | 1 / 8 |
| ADX/DI + seven-day cooldown | -5.47% | 0.71 | 11.09% | 12.50% | 16 / 2.65 / 0.122 | 2 / 9 |

## Recent year — previously selected weekly candidate

2025-09-27 to 2026-09-27. Native Model4; the six-month window overlaps this one and is not independent evidence. Other weekly variants were not tested over this recent year.

| Version | Return | PF | Equity DD | Win rate | Trades / month / weekday | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|
| Current rules | -3.23% | 0.94 | 29.97% | 17.95% | 39 / 3.25 / 0.150 | 2 / 14 |
| ADX/DI + rising ADX | +19.10% | 1.31 | 22.17% | 22.22% | 45 / 3.75 / 0.173 | 3 / 15 |
| ADX/DI + seven-day cooldown | +13.55% | 1.33 | 18.78% | 21.21% | 33 / 2.75 / 0.127 | 2 / 10 |

## Older development — full comparison

2021-09-27 to 2024-09-27. Native Model1 1-minute OHLC screening, not real-tick proof.

| Version | Return | PF | Equity DD | Win rate | Trades / month / weekday | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|
| Current rules | -1.02% | 0.99 | 34.23% | 17.53% | 154 / 4.28 / 0.196 | 2 / 22 |
| ADX/DI + rising ADX | +34.48% | 1.32 | 19.66% | 21.82% | 110 / 3.05 / 0.140 | 3 / 17 |
| Once/calendar week | -7.71% | 0.92 | 33.87% | 16.38% | 116 / 3.22 / 0.148 | 3 / 18 |
| Seven-day entry cooldown | +0.92% | 1.01 | 24.53% | 17.09% | 117 / 3.25 / 0.149 | 2 / 17 |
| ADX/DI + once/week | +0.43% | 1.00 | 26.14% | 17.65% | 102 / 2.83 / 0.130 | 2 / 19 |
| ADX/DI + seven-day cooldown | +29.48% | 1.34 | 17.88% | 22.22% | 90 / 2.50 / 0.115 | 3 / 14 |

## Older validation — full comparison

2024-09-27 to 2025-09-27. Native Model1. Require development >=20 trades, positive return, PF>=1.15; validation >=10 trades, positive return, PF>=1.10. Rank eligible candidates by validation return/equity drawdown.

| Version | Return | PF | Equity DD | Win rate | Trades / month / weekday | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|
| Current rules | +27.52% | 1.64 | 14.55% | 25.00% | 48 / 4.00 / 0.184 | 3 / 8 |
| ADX/DI + rising ADX | +38.16% | 2.42 | 7.49% | 33.33% | 30 / 2.50 / 0.115 | 2 / 5 |
| Once/calendar week | +45.53% | 2.54 | 9.68% | 33.33% | 33 / 2.75 / 0.126 | 2 / 6 |
| Seven-day entry cooldown | +15.69% | 1.46 | 12.94% | 22.86% | 35 / 2.92 / 0.134 | 2 / 9 |
| ADX/DI + once/week | +44.10% | 3.03 | 7.63% | 38.46% | 26 / 2.17 / 0.100 | 2 / 4 |
| ADX/DI + seven-day cooldown | +35.85% | 2.80 | 7.33% | 34.78% | 23 / 1.92 / 0.088 | 2 / 4 |

## What the entry rules do — and do not do

- **Calendar week:** only the first qualifying entry after Monday 00:00 broker time is permitted that week. The existing 24-hour entry-to-entry guard remains. A position may stay open across multiple weeks. No forced Monday entry or Friday close.
- **Rolling seven days:** at least 168 hours from the preceding entry, regardless of when it exits. One open position maximum remains.
- **ADX/DI versions:** native ADX14 >=20, +DI>-DI for longs or -DI>+DI for shorts, and ADX[1]>ADX[2], all from closed H4 candles. Existing momentum/EMA rules still apply.
- **Manual closure:** closing a position does not reset the last-entry clock. That blocks replacements until the entry cap expires, but if the entry is already a week old, a replacement may be permitted immediately. A “pause after my manual close until I re-arm it” control is a separate operational safeguard, not tested profit enhancement here.
- **Risk:** no compensating increase in lot size. Original nominal 1% equity sizing rounds lots upward, so actual stop risk can exceed 1%. A lower drawdown with fewer trades is not by itself a stronger edge.

## Native execution and evidence limits

- Same isolated Exness-MT5Trial16 XAUUSD CFD tester as the previous study, H4, USD10,000, 150ms execution delay, broker spread/commission/swap. Active demo account is Trial15. This is not a replay of your manually closed trades or other portfolio bots.
- Baseline inputs follow the saved configuration, corroborated in the previous account audit by actual H4 ATR stop/6R target geometry. Active chart inputs cannot be read directly through the Python MT5 API; exact live configuration equivalence remains an assumption, not a newly verified fact.
- Stop remains 1.5 × ATR14, target 6R, both sides, no new exit management. Each window starts flat and liquidates remaining exposure at the tester end. Six-month results are independent simulations, not sliced yearly returns.
- Model4 real ticks begin 2026-01-01 in the retained broker history. One-year reports specify **73% real ticks**, with generated fallback earlier; six-month reports specify **100% real ticks**. These explicit real-tick percentages were checked in each native report, not inferred from a generic history-quality label.
- Fifteen new native tests completed: two off-switch parity runs, eight older-window screens, four recent six-month tests and one recent-year test. Existing control results are reused from the dated prior study where not rerun. The new default-off weekly EA reproduced the baseline's 38-trade one-year Model1 ledger and the ADX control's 45-trade one-year Model4 ledger exactly, including all prices, sizes, times and net costs. This is bounded parity, not proof under all live conditions.
- Native equity drawdown includes floating losses; it is not a closed-balance calculation. Trade/month uses calendar-month equivalents, and trade/weekday uses Monday-Friday counts rather than exact broker sessions. Win/loss streaks use net cash after costs.
- Calendar/rolling arithmetic self-tests passed inside the native EA. Independent ledger checks passed for cash totals, contract-size price P&L, no overlapping positions, 24-hour original spacing, and the selected calendar or rolling-week restriction. Source/include/binary hashes remained unchanged. Native compile: zero errors/warnings. No invalid stops/volumes, insufficient-funds, stop-out or market-closed errors detected.
- Only a small number of recent trades remain after throttling. There is no multiple-testing adjustment, Monte Carlo, extra-cost stress grid, independent-broker test, or new forward-test evidence here. Broker swap specifications are not a verified historical schedule. No promise of profitability or safe drawdown follows from this study.

## Sources and local evidence

Calendar conversion follows [MQL5 date/time fields](https://www.mql5.com/en/docs/constants/structures/mqldatetime); broker week uses [Exness MetaTrader GMT+0 time](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader). Native indicator definitions: [iADX buffers](https://www.mql5.com/en/docs/indicators/iadx). Testing limitations: [real/generated tick behavior](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).

Local protocol, build hashes, selection and audit are retained as PROTOCOL.md, BUILD.json, PARITY.json, SELECTION.json and AUDIT.json. Every native report and trade ledger is retained under native/. Private tester login settings are not included in this report. Prior control evidence is in the sibling XAU Slow Trend Filter Review 2026-09-29/native/ directory.

### Retained tick coverage messages

- XAUUSD : real ticks begin from 2026.01.01 00:00:00
