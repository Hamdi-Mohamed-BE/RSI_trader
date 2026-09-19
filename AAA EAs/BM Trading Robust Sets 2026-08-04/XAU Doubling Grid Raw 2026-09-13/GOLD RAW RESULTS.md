# Gold doubling grid — raw native MT5 results

## Verdict

**Not suitable for a $3,000 account as specified. All four native tests ended in stop-out.**

In the requested three-year system window, the account made **$502.28 net**, then lost **$3,603.38** on the next basket. Equity was exhausted after **23.62 calendar days**, before securing another $3,000 in closed profit.

These are four separate $3,000 starts, not four successful completed horizons, not four repeated attempts within each horizon, and not an estimated liquidation probability. BTC was not tested. No optimization, live orders, portfolio installation, website replacement, or Git push was performed for this strategy.

## Frozen rules

- Buy 0.02 lots immediately at the first available ask. For each $10 fall in the **quoted gold price** from the first actual entry, add 0.04, 0.08, 0.16 lots, and so on.
- A lone position exits when bid reaches first entry +$10. After an addition, close the entire basket when bid returns to the original first entry. This is price breakeven for the first position, not net breakeven after charges.
- Restart when flat, unless net cash profit since broker midnight is at least $300. A basket is closed in full and may exceed $300. The daily target is not a floating-equity take-profit or a loss cap.
- Hold baskets across days and weekends. No voluntary stop loss, equity stop, ladder cap, withdrawals or recapitalization. Rejected prescribed additions remain rejected; no smaller replacement order or imaginary fill.
- Initial balance $3,000 USD. Native tester settings: Exness-MT5Trial16, XAUUSD in the Zero symbol group, 100 oz per lot, hedging, fixed 1:2000 leverage, 30% margin call, 0% stop-out. Model 4, fixed 1 ms execution delay. Commission, swap and bid/ask spread are included under the loaded tester specifications.

See [complete frozen rules](RULES.md).

## Dates and survival

The tests use the existing system windows ending **5 September 2026, exclusive**. They are not rolling windows ending on the report date of 13 September. Trading ended much earlier in every case because the account failed. Times below are the historical MT5 timestamps, not the user's local time.

For survival, use **first observed equity at or below zero**, not a recovery the tester allows after that point.

| Requested window | Actual first tick | First nonpositive equity | Time to equity exhaustion | Closed balance reached $6,000 first? | Highest flat balance before exhaustion |
|---|---|---|---:|---|---:|
| 6 months | 2026-03-05 00:00:00 | 2026-03-05 06:12:21 | 6h 12m | No | $3,120.26 |
| 1 year | 2025-09-05 00:00:00 | 2025-10-21 08:14:42 | 46.34 days | Yes, 2025-09-15 15:50:37 | $245,609.58 [1] |
| 3 years | 2023-09-05 00:00:00 | 2023-09-28 14:58:19 | 23.62 days | No | $3,502.28 |
| 5 years | 2021-09-05 22:05:00 | 2021-09-16 12:15:39 | 10.59 days | No | $3,000.00 |

[1] The one-year start overshot $6,000: the first qualifying basket closed at **$15,804.22** on 15 September. It subsequently reached a large balance, then lost everything on 21 October. No profits were withdrawn. The large peak is a model outcome, **not a credible income forecast**: its later trades relied on generated ticks, extremely large doubled exposure and fixed 1:2000 leverage. Actual Exness equity-based leverage tiers and historical high-margin periods were not reconstructed. Exness currently documents lower maximum leverage as equity rises. [Exness leverage rules](https://get.exness.help/hc/en-us/articles/360014529380-Leverage).

## Complete native-run statistics

These figures continue to the **native tester's recorded liquidation**, which can lag the first nonpositive-equity tick. They are retained for reproducibility, not used to claim survival after insolvency. Win rate and profit factor below are recomputed per individual position **after commission, swap and other recorded fees**.

| Window | Individual positions | Net win rate | Net PF | Baskets | Profitable baskets | Net P/L | Native final balance | Native return |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 months | 13 | 38.46% | 0.026 | 5 | 4 / 5 (80.00%) | -$4,553.76 | -$1,553.76 | -151.79% |
| 1 year | 236 | 73.31% | 0.948 | 119 | 118 / 119 (99.16%) | -$13,376.68 | -$10,376.68 | -445.89% |
| 3 years | 11 | 27.27% | 0.143 | 2 | 1 / 2 (50.00%) | -$3,101.10 | -$101.10 | -103.37% |
| 5 years | 7 | 0.00% | 0.000 | 1 | 0 / 1 (0.00%) | -$3,299.78 | -$299.78 | -109.99% |

Negative tester balances mean the modeled liquidation overshot zero. **They do not establish that these amounts would be personally owed to the broker.** Negative-balance protection was not simulated; neither were broker-specific historical interventions. All four exhausted the original deposit.

The native HTML may show a higher win rate because its win/loss classification does not match this all-cost position aggregation. For example, the one-year report displays 90.68%, while the verified net position win rate is 73.31%. A high basket win rate still did not prevent total loss.

### Equity drawdown and costs

| Window | Peak equity, full native path | Minimum equity | Native reported equity DD | Independently logged per-tick maximum DD | Maximum cash drawdown, per-tick | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|
| 6 months | $14,488.12 [2] | -$1,553.76 | 110.78% | 120.82% | $16,041.88 | -$14.85 | $0.00 |
| 1 year | $251,562.17 | -$13,571.17 | 105.39% | 105.39% | $265,133.34 | -$1,137.95 | -$2,670.27 |
| 3 years | $3,535.78 | -$114.05 | 103.23% | 103.23% | $3,649.83 | -$15.62 | -$404.43 |
| 5 years | $3,521.64 | -$711.51 | 120.20% | 120.20% | $4,233.15 | -$13.97 | -$348.80 |

Drawdown includes floating losses. Per-tick DD is the maximum of `(prior equity high - current equity) / prior equity high`. Maximum cash and percentage drawdowns need not occur at the same time. Values exceed 100% because simulated equity went negative. They are **not limited-loss percentages**.

[2] The six-month peak occurred after equity had already gone negative. It is not credited as recoverable profit or valid survival. The strategy never secured $6,000 flat in that run.

### Native stop-out timing limitation found during verification

| Window | First nonpositive-equity observation | First native stop-out deal | Delay |
|---|---|---|---:|
| 6 months | 2026-03-05 06:12:21 | 2026-03-05 13:21:00 | 7h 08m 39s |
| 1 year | 2025-10-21 08:14:42 | 2025-10-21 08:15:00 | 18s |
| 3 years | 2023-09-28 14:58:19 | 2023-09-28 14:59:00 | 41s |
| 5 years | 2021-09-16 12:15:39 | 2021-09-16 12:31:00 | 15m 21s |

An observer-only replay reproduced every original deal exactly and logged these earlier equity breaches. In the six-month case, equity fell to -$658.41 at 06:12:25 from a previous $3,163.13 high, producing the 120.8151% drawdown omitted from the native summary. The tester then let the basket continue. This is an observed limitation of these tests; it is not a claim that a live broker would permit that recovery or that every MT5 version checks liquidation on the same schedule.

Native stop-out is confirmed by deal reason `DEAL_REASON_SO` and the tester journal. Once the tester ended, residual positions were closed as **end of test**, not misclassified as additional broker stop-out deals: 4 stop-out + 3 residual exits for 6m/3y/5y, and 7 + 6 for 1y. [MetaQuotes deal reasons](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties).

## Three-year start: every basket

| Basket | Opened | Closed | Legs | Net result | Flat balance after closure |
|---|---|---|---:|---:|---:|
| 1 | 2023-09-05 00:00:00 | 2023-09-20 13:43:12 | 4 | +$502.28 | $3,502.28 |
| 2 | 2023-09-21 00:00:00 | 2023-09-28 14:59:00 | 7 | -$3,603.38 | -$101.10 |

Basket 1 paid $1.65 commission and $176.55 swap. Basket 2 paid $13.97 commission and $227.88 swap. Total costs were **$420.05**. The successful first basket took over 15 days to return to its initial entry, so the proposed $300 target did not create a daily income stream.

The losing basket started at **1929.591** and accumulated **0.02 + 0.04 + 0.08 + 0.16 + 0.32 + 0.64 + 1.28 = 2.54 lots**. At that exposure, a further $1 gold-price fall costs about **$254** before charges. Equity first crossed zero at bid **1866.194**, a **$63.397** decline from the original entry. Native liquidation finished at 1865.801.

In an idealized seven-leg ladder, merely reaching $60 below the original entry already creates about **$2,400 floating loss before spread, commission and swap**. With a $3,000 starting balance, the next doubling is not a recovery mechanism that can continue indefinitely.

## Data-quality limits

- The tester journal says historical real ticks begin **1 January 2026**. The six-month run was on real ticks according to its 100% native report. The actual traded parts of the 1y, 3y and 5y tests all ended before that date and therefore used **generated ticks**.
- The native headers of 67%, 22% and 13% real ticks refer to broader requested history. They must not be presented as real-tick coverage of these shortened executed tests.
- Bid/ask spread and recorded commission/swap are included. The loaded historical bar spread and current tester charge specifications are not a verified reconstruction of every historical brokerage fee, swap rate or leverage regime. Fixed 1 ms delay is not a realistic news-slippage stress test. [MetaQuotes spread and execution behavior](https://www.metatrader5.com/en/terminal/help/algotrading/testing_features).
- Stop-out timing, leverage changes, rejected additions under different broker margin rules, liquidity and execution can change the exact path. These results show the raw model is unsafe; they do not establish an exact future time-to-liquidation.
- One starting date per window cannot estimate the probability of doubling before failure. No replacement-account, withdrawal or rolling-start simulation has been performed.

## Evidence and verification

- [Three-year native report with full deals](Backtest%20Reports/xau-grid-3y-model4.htm)
- [Six-month native report](Backtest%20Reports/xau-grid-6m-model4.htm)
- [One-year native report](Backtest%20Reports/xau-grid-1y-model4.htm)
- [Five-year native report](Backtest%20Reports/xau-grid-5y-model4.htm)
- [Independent verification](verification.json)
- [Original native results and hashes](results.json)
- [Three-year position-level breakdown](Audit/xau-grid-3y-model4-trades.json)
- [Three-year native deal ledger](Audit/xau-grid-3y-model4-deals.csv)

Four original native tests plus four observer-only replays; identical execution ledgers across each pair. All four passed cash reconciliation, exact doubling/rung checks, actual fill checks, exit-trigger checks, daily cutoff checks, net-cost aggregation and milestone reconstruction. Both original and diagnostic EAs compiled with zero errors and zero warnings. Test code refuses to initialize outside the MT5 Strategy Tester.

**Recommendation: reject this uncapped raw version for deployment.** The $300 daily profit target stops future entries after wins; it does not limit the loss of the basket currently open.
