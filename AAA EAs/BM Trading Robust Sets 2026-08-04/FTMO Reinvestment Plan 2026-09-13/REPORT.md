# $10K FTMO Swing challenge → payout-funded account purchases

## Read this first

This is a conditional retrospective cash-flow replay, not a forecast, verified FTMO backtest, promised investment return or real account transaction. No account was bought, and no live EA/BAT/website was changed.

Window: 5 September 2023 to 31 August 2026 (36 calendar rows; September 2023 and 2026 calendar year are partial). Current screenshot fees/current FTMO rule assumptions are applied counterfactually to historical EA trades. They are not claimed to be the offers or rules in effect in 2023.

The new simulated portfolio replaces the previously negative News Pulse XAU with DMC Fresh Reaction US100. BTC News stays excluded. The other nine EAs are unchanged. High win rate is a preference, not a requirement that every retained profitable EA exceeds 50%; this remains a mixed-strategy portfolio.

DMC replacement isolated stressed screen: 42 three-year trades, 66.7% win rate, PF 1.56; 82 trades in the source five-year ledger. That is a modest sample and was selected retrospectively. US100 Selective ORB V3 had only 19 executed three-year trades; Nasdaq Overnight lost after stress. Two high-win variants had incomplete commission/swap breakdowns and were not silently treated as cost-free.

## Buying and cash rules used

- Initial own cash is ONLY the $10K challenge fee, not $10,000 of your own trading capital. No additional external money is added later.
- Until total received trader rewards reach $2,000: after a payout/refund settles, buy one largest affordable offered challenge. Leftovers remain in the wallet. Thus small early rewards can buy additional $10K accounts instead of waiting for a bigger tier.
- At $2,000 cumulative trader rewards, switch to the growth stage. First growth batch is pending until an affordable batch is available; then another batch is eligible per further accumulated $2,500 of trader rewards. Refunds add spendable cash but do not count toward these reward thresholds.
- A growth batch spends UP TO $1,100 of available cash, includes at least one $100K challenge, and adds smaller tiers if that increases the total permitted allocation. Equal capital prefers fewer accounts. Unspent money stays in cash. The first growth batch may be smaller than $1,100 when cash is limited.
- If there is not room for a $100K challenge, further growth batches wait. No unrequested retirement, scaling approval, other prop firm, borrowing or additional registration is assumed.
- Reserve the $400K per-trader/strategy cap for all live challenges, verifications and funded accounts combined. This is conservative relative to funded-only interpretations. A simulated failed account releases its slot. Identical accounts use the SAME market history, not independent random returns.
- Each purchase starts a new evaluation on the next weekday. Initial account starts 5 Sep 2023. Both phases must independently achieve +10% / +5% with four distinct entry days. Two weekdays are allowed for phase transition, five for funded activation/KYC. These are modelling assumptions, not guaranteed FTMO processing times.
- 80% trader share. Keep a 2% initial-capital buffer on each funded account. Claim at month end or the first eligible flat opportunity afterward; at least 14 days after first funded trade / previous claim. All pending orders are assumed cancelled for a claim; their full history is not available.
- Cash arrives four weekdays after the claim. Trading pauses during those four weekdays. The base challenge fee is refunded once with the first settled reward; assumed FX/card costs are not refunded. Holidays, real banking delays, review rejection, taxes and VPS costs are not modelled.

## Prices

The screenshot shows fees in EUR and trading balances in USD. Conversion held constant at EUR 1 = USD 1.1592 (ECB 11 Sep 2026), plus a separately assumed 2% FX/card allowance. Actual checkout/card charges may differ.

| Challenge size | Screenshot EUR fee | USD base fee | FX/card allowance | Cash paid |
|---|---:|---:|---:|---:|
| $10,000 | €99 | $114.76 | $2.30 | $117.06 |
| $25,000 | €279 | $323.42 | $6.47 | $329.89 |
| $50,000 | €379 | $439.34 | $8.79 | $448.13 |
| $100,000 | €599 | $694.36 | $13.89 | $708.25 |
| $200,000 | €1,080 | $1,251.94 | $25.04 | $1,276.98 |

With $1,100 cash and sufficient headroom, the maximum face-value batch is $100K + $10K + $10K + $10K = $130K allocation for $1,059.43. This maximizes nominal account size, not probability of survival. Small copied accounts remain correlated and vulnerable to lot rounding.

## Trading and risk model

- Risk target 0.35% per trade for all ten EAs, including remaining XAG News. Each account independently scales its limits: 1% daily closed-loss gate for non-news, 3% planned-open-risk gate for non-news, 4%/7% drawdown and 3/5 loss-streak tapers. News bypasses adaptive gates/tapers, not broker margin constraints.
- Lot rounding is UP to the 0.01 step, including minimum lot. A small account may therefore risk materially more than 0.35%. Margin and risk are replayed separately at $10K/$25K/$50K/$100K, not scaled from a $100K profit chart.
- One shared balance and simultaneous positions within each account. Model Swing leverage: forex 1:30, indices 1:15, metals 1:9; 20% equity margin reserve; no offsetting hedge-margin credit. Exact current FTMO per-symbol terms remain unverified.
- Official 2-Step loss checks modelled at every trade event and midnight CE(S)T: 5% initial-capital daily equity loss relative to midnight balance; static 10% total-loss floor. Targets require all positions flat. No automatic restart or free funded account after a failure.
- Cash-deal checks do not observe real floating equity. The primary scenario treats a simultaneous planned-stop exposure crossing a limit as a hypothetical failure and stops the account. This is not proof the actual account would have breached.
- The exposure proxy uses full estimated initial stop risk even after trailing, news 1.25x/other 1.10x stress, unpaid commission, 0.15R/0.02R extra execution allowance and a fixed 0.05R carry reserve. Future realized swap is NOT used in entry/margin decisions.
- Execution stress: news gross winners x0.65, losers x1.25, extra 0.15R; regular winners x0.90, losers x1.10, extra 0.02R. Commission floor $7/lot round-trip for metals/FX. Double negative recorded swap and discard swap credits. These are sensitivity assumptions, not an FTMO fee quote or calibrated execution model.
- Source balance reconstructed from source risk cash/configured percentage, to avoid double-compounding existing source backtests. Costs scaled by actual rounded lots. Commission split half at entry/exit, swap booked at close. Same-second round trips ordered entry before exit.

## Evidence limitations

- Remaining News Pulse XAG source reports only 13% real ticks. Its historical news fills and the resulting payout path are not verified FTMO evidence.
- Saved native MT5 closed-deal ledgers lack continuous bid/ask equity, original SL histories, all pending orders and account-specific historical FTMO costs. Model failures can overstate actual losses after trailing; gaps can also exceed planned stops. Closed-only survival can miss real intraday breaches.
- Selection uses knowledge of the full historical period. Cached strategy settings were optimized retrospectively. This is not an out-of-sample business forecast and reinvestment magnifies source-model errors.
- Today's fixed prices, USD conversion and simplified weekday delays are deliberately explicit assumptions. Small timing or pricing changes can alter which challenge is bought and when, changing later outcomes.
- No probability of achieving the final cash amount is claimed. Repeated trades across copied accounts are not independent observations. Do not count simulated account allocations as personal wealth.

## Overall real-cash ledger — conservative stress scenario

| Item | USD |
|---|---:|
| External cash initially required | $117.06 |
| Trader rewards actually settled in the model | $34,864.18 |
| Challenge fees paid, including FX allowance | $4,052.08 |
| Base challenge fees refunded | $3,628.30 |
| Unrefunded fees on failed accounts | $344.28 |
| Non-refundable FX/card assumptions, all purchases | $79.50 |
| Total unrecovered cost | $423.78 |
| Net cash profit = rewards + refunds − all fees paid | $34,440.40 |
| Cash wallet = original seed + net cash profit | $34,557.46 |
| Further requested rewards not settled by the cutoff; excluded above | $3,215.45 |

13 challenges bought; 7 hypothetical failures; 6 funded accounts surviving, with $400,000 simulated allocation. That allocation is NOT withdrawable cash.

All seven flagged failures are $10K accounts on 9 January 2026. Four had already received fee refunds; three had not. The three unrecovered base fees total $344.28. Do not subtract this again from net cash: the fees were already counted when purchased.

## Yearly cash breakdown

| Year | Rewards received | Fees paid | Fee refunds | Failed fees not recovered | Net cash profit | Wallet at year end | Failures | Funded capital at year end |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | $0.00 | $117.06 | $0.00 | $0.00 | -$117.06 | $0.00 | 0 | $0 |
| 2024 | $2,460.70 | $2,188.63 | $344.28 | $0.00 | $616.35 | $616.35 | 0 | $30,000 |
| 2025 | $5,244.55 | $708.25 | $554.10 | $0.00 | $5,090.40 | $5,706.75 | 0 | $90,000 |
| 2026 | $27,158.93 | $1,038.14 | $2,729.92 | $344.28 | $28,850.71 | $34,557.46 | 7 | $400,000 |

2023 covers Sep–Dec; 2026 covers Jan–Aug. Fees on accounts later failed are recognised as unrecovered when failure occurs, but this is not a second cash payment.

## Monthly cash breakdown

| Month | Rewards received | Fees paid / invested | Fee refunds | Net real cash | Wallet end | Accounts bought | Failures | Funded allocation end |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-09 | $0.00 | $117.06 | $0.00 | -$117.06 | $0.00 | 1 | 0 | $0 |
| 2023-10 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $0 |
| 2023-11 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $0 |
| 2023-12 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $0 |
| 2024-01 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $0 |
| 2024-02 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $0 |
| 2024-03 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $0 |
| 2024-04 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0 | 0 | $10,000 |
| 2024-05 | $111.31 | $117.06 | $114.76 | $109.01 | $109.01 | 1 | 0 | $10,000 |
| 2024-06 | $25.34 | $117.06 | $0.00 | -$91.72 | $17.29 | 1 | 0 | $10,000 |
| 2024-07 | $202.88 | $117.06 | $0.00 | $85.82 | $103.11 | 1 | 0 | $10,000 |
| 2024-08 | $462.96 | $448.13 | $0.00 | $14.83 | $117.94 | 1 | 0 | $10,000 |
| 2024-09 | $0.00 | $0.00 | $0.00 | $0.00 | $117.94 | 0 | 0 | $10,000 |
| 2024-10 | $775.86 | $708.25 | $0.00 | $67.61 | $185.55 | 1 | 0 | $30,000 |
| 2024-11 | $171.82 | $564.01 | $229.52 | -$162.67 | $22.88 | 3 | 0 | $30,000 |
| 2024-12 | $710.53 | $117.06 | $0.00 | $593.47 | $616.35 | 1 | 0 | $30,000 |
| 2025-01 | $177.86 | $708.25 | $0.00 | -$530.39 | $85.96 | 1 | 0 | $40,000 |
| 2025-02 | $0.00 | $0.00 | $0.00 | $0.00 | $85.96 | 0 | 0 | $40,000 |
| 2025-03 | $399.55 | $0.00 | $114.76 | $514.31 | $600.27 | 0 | 0 | $40,000 |
| 2025-04 | $734.32 | $0.00 | $0.00 | $734.32 | $1,334.59 | 0 | 0 | $90,000 |
| 2025-05 | $791.68 | $0.00 | $0.00 | $791.68 | $2,126.27 | 0 | 0 | $90,000 |
| 2025-06 | $0.00 | $0.00 | $0.00 | $0.00 | $2,126.27 | 0 | 0 | $90,000 |
| 2025-07 | $0.00 | $0.00 | $0.00 | $0.00 | $2,126.27 | 0 | 0 | $90,000 |
| 2025-08 | $0.00 | $0.00 | $0.00 | $0.00 | $2,126.27 | 0 | 0 | $90,000 |
| 2025-09 | $468.16 | $0.00 | $0.00 | $468.16 | $2,594.43 | 0 | 0 | $90,000 |
| 2025-10 | $1,799.40 | $0.00 | $439.34 | $2,238.74 | $4,833.17 | 0 | 0 | $90,000 |
| 2025-11 | $873.58 | $0.00 | $0.00 | $873.58 | $5,706.75 | 0 | 0 | $90,000 |
| 2025-12 | $0.00 | $0.00 | $0.00 | $0.00 | $5,706.75 | 0 | 0 | $90,000 |
| 2026-01 | $2,923.46 | $1,038.14 | $0.00 | $1,885.32 | $7,592.07 | 2 | 7 | $175,000 |
| 2026-02 | $1,537.53 | $0.00 | $1,017.78 | $2,555.31 | $10,147.38 | 0 | 0 | $275,000 |
| 2026-03 | $6,878.87 | $0.00 | $694.36 | $7,573.23 | $17,720.61 | 0 | 0 | $275,000 |
| 2026-04 | $2,560.45 | $0.00 | $0.00 | $2,560.45 | $20,281.06 | 0 | 0 | $275,000 |
| 2026-05 | $6,161.47 | $0.00 | $0.00 | $6,161.47 | $26,442.53 | 0 | 0 | $275,000 |
| 2026-06 | $1,799.34 | $0.00 | $0.00 | $1,799.34 | $28,241.87 | 0 | 0 | $275,000 |
| 2026-07 | $357.72 | $0.00 | $0.00 | $357.72 | $28,599.59 | 0 | 0 | $400,000 |
| 2026-08 | $4,940.09 | $0.00 | $1,017.78 | $5,957.87 | $34,557.46 | 0 | 0 | $400,000 |

## Individual account lifecycle

| ID | Size | Purchased | Fee paid | Funded activation | End status | Refund received |
|---|---:|---|---:|---|---|---|
| 1 | $10,000 | 2023-09-05 | $117.06 | 2024-04-22 | Failed stop-exposure scenario 2026-01-09 | Yes |
| 2 | $10,000 | 2024-05-23 | $117.06 | 2024-10-25 | Failed stop-exposure scenario 2026-01-09 | Yes |
| 3 | $10,000 | 2024-06-07 | $117.06 | 2024-10-25 | Failed stop-exposure scenario 2026-01-09 | Yes |
| 4 | $10,000 | 2024-07-04 | $117.06 | 2025-01-10 | Failed stop-exposure scenario 2026-01-09 | Yes |
| 5 | $50,000 | 2024-08-06 | $448.13 | 2025-04-10 | funded | Yes |
| 6 | $100,000 | 2024-10-24 | $708.25 | 2026-01-05 | funded | Yes |
| 7 | $10,000 | 2024-11-22 | $117.06 | 2026-01-05 | Failed stop-exposure scenario 2026-01-09 | No |
| 8 | $10,000 | 2024-11-25 | $117.06 | 2026-01-05 | Failed stop-exposure scenario 2026-01-09 | No |
| 9 | $25,000 | 2024-11-25 | $329.89 | 2026-01-05 | funded | Yes |
| 10 | $10,000 | 2024-12-06 | $117.06 | 2026-01-05 | Failed stop-exposure scenario 2026-01-09 | No |
| 11 | $100,000 | 2025-01-08 | $708.25 | 2026-02-10 | funded | Yes |
| 12 | $100,000 | 2026-01-30 | $708.25 | 2026-07-21 | funded | Yes |
| 13 | $25,000 | 2026-01-30 | $329.89 | 2026-07-21 | funded | Yes |

## Sensitivity: same reinvestment policy, different execution/breach assumptions

| Scenario | Net cash profit | Modelled failures | End funded allocation |
|---|---:|---:|---:|
| stressed-stop-check | $34,440.40 | 7 | $400,000 |
| stressed-closed-only | $43,690.31 | 0 | $345,000 |
| recorded-fill-reference | $198,817.39 | 0 | $360,000 |

The recorded-fill reference is optimistic and is NOT the recommended expectation. Differences are not statistical confidence intervals: they demonstrate model sensitivity.

## EA contributions in a separate constant-$10K funded-start check

This verifies the replacement at the small account size; it is NOT the reinvestment wallet. Payout pauses and account-wide controls are active.

| EA | Closed trades | Net simulated P/L | Win rate | PF |
|---|---:|---:|---:|---:|
| News Pulse XAG | 86 | $789.61 | 48.8% | 1.38 |
| ORB Volume Profile Confirmed | 52 | $332.88 | 40.4% | 1.41 |
| XAU Trend Progression | 71 | $1,722.71 | 64.8% | 2.33 |
| USDJPY London Open Momentum | 354 | $467.22 | 45.8% | 1.11 |
| US100 ORB New York M30 | 52 | $385.17 | 48.1% | 1.40 |
| US100 H1 ORB 13UTC | 142 | $1,288.12 | 52.8% | 1.57 |
| EMA3 Safe | 55 | $1,597.90 | 67.3% | 2.24 |
| XAU Squeeze Momentum Standard | 74 | $344.00 | 47.3% | 1.26 |
| XAU RSI VWAP | 111 | $327.56 | 76.6% | 1.25 |
| DMC Fresh Reaction US100 | 36 | $335.29 | 66.7% | 1.68 |

Across all copied evaluation/funded accounts the replay records 7,206 closed trades, $353,755.59 gross losing-trade P/L and $131,071.59 net simulated trading balance flow. These are fictitious-account trading amounts, not personal cash losses or income. Only settled rewards/refunds minus paid fees enter the cash ledger.

## Validation

12 deterministic tests passed: seed fee basis, batch budget/headroom, cash/month/year reconciliation, allocation cap, settlement after funding, new phase requirements, correlated failures, once-only refunds, minimum-lot rounding and account-size loss thresholds. Every account replay also checks accounting identities and no orphan/post-failure trades.

## Sources checked 13 September 2026

- User-provided screenshot: €99/€279/€379/€599/€1,080 fees for $10K/$25K/$50K/$100K/$200K accounts.
- [FTMO maximum allocation](https://ftmo.com/faq/how-many-accounts-can-i-have/)
- [FTMO 2-Step evaluation objectives](https://ftmo.com/en/trading-objectives/)
- [FTMO rewards, timing and profit share](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)
- [FTMO fees/refund](https://ftmo.com/faq/are-the-fees-recurrent/)
- [ECB EUR/USD reference rate](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
- [FTMO published Swing leverage by asset class](https://ftmo.com/en/blog/a-few-answers-to-your-questions/)

Recommendation: validate the replacement and news fills on full FTMO tick evidence before treating this as an investment plan. Compare waiting for larger tiers against repeatedly buying $10K accounts; the latter maximises early nominal allocation but produced concentrated small-account failures in this stress scenario.
