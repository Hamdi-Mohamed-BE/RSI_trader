# Paper application: matched $10,000 FTMO 2-Step Swing scenarios

Research only, 26 September 2026. No live settings, orders, website or launchers changed.

## What is being tested

The three papers are contract valuation frameworks, not three EA entry strategies. Use the contract-specific logic of paper 3, stable dollar sizing from paper 1, and the pass-to-cash funnel from paper 2. Do not transplant Topstep random-direction results to FTMO.

Eight predeclared configurations reuse existing strategy ledgers, without changing entries or optimizing parameters. Five- and eight-EA lists were selected in earlier studies; their prior strategy development and repeated reuse of history prevent calling these results pristine out-of-sample evidence. Risk is $50, $71.43 or $100 per ordinary entry, fixed dollars rather than compounding. News comparisons use $10 per side, both sides retained; news parameters were fitted to the same history and their contractual eligibility is unresolved.

## Data and resampling

- Audited native MT5 trade ledger snapshot from 19 September, ending 31 August 2026 exclusive. This is NOT newly run FTMO tick testing and excludes September results.
- Source pools: 26 joint weeks, 2 March–30 August 2026; 101 joint weeks, 23 September 2024–30 August 2026. News has insufficient coverage for the longer comparison, so it is excluded there.
- 1,000 resampled paths per configuration/cost/pool; same random draws across configurations. Preserve all EAs' within-week correlations and trade durations. One-week blocks do not retain multi-week dependence; trades spanning blocks can overlap artificially. Calendar timestamps shifted to preserve New York local timing; other sessions and holiday structure are approximations.
- Synthetic Monday start: 28 September 2026. Horizons: 30, 60, 120 and 180 calendar days. These are deadlines for reporting, NOT FTMO evaluation expiry dates.
- Source SHA-256 hashes verified against the prior manifest; exact historical replay parity checked.
- Wilson intervals quantify Monte Carlo sampling error ONLY, not uncertainty from six months of data, selection, market change or execution.

## Account and execution assumptions

- Initial balance $10,000, targets $1,000 then $500, four separate trading days per phase, flat at completion. Both phases use 5% initial-capital daily loss and 10% static total loss limits. No 2-Step best-day limit.
- Daily reset uses midnight Europe/Prague including DST. Shared balance, pending orders, floating-risk reserve and margin across all EAs.
- Assumed transfer delays: 2 business days between evaluations and 5 to funded. First reward after at least 14 calendar days from first funded entry, flat with no pending orders; minimum modeled closed profit $25, bank-payment assumption. Four further business days for review/payment. Delays exclude public holidays and individual KYC delays.
- First reward only, 80% share; simulation stops at that request. It does not measure continued funded-account survival or annual income.
- Lot minimum/step 0.01; round UP as in the previous study, then reject if exposure/margin caps fail. Actual risk can exceed the nominal risk by one lot step. These are scenario specifications, not a query of the current account.
- Scenario leverage: metals and USTEC 1:15, FX 1:30, crypto 1:1; contracts XAU 100 oz, XAG 5,000 oz, USTEC $1/point, FX 100,000, BTC 1, ETH 10.
- Internal guards: reserve no more than 80% of modeled available equity for margin; $225 total simultaneous initial risk, $150 correlated metals or per-symbol risk, $300 daily admission budget, $9,200 total internal equity buffer, maximum 7 admitted entries/day and stop new entries after 3 closed losses. Both pending news sides consume resources.
- Full-stop floating-loss approximation: 1R ordinary / 1.25R news in reference; 1.25R ordinary / 2R news in stress. NOT measured tick equity, nor a guaranteed bound on gap loss. Zero simulated breaches under these gates does not mean zero real-world breach risk.
- Reference costs retain recorded spread/gap fills and at least $7/lot round trip except XAG $47.50 and USTEC $0.70. Crypto 0.0325% each side. Stress reduces gross wins 10%, enlarges gross losses 10%, adds adverse price movement ($0.20 gold, $1 news gold, $0.04 silver, 2 USTEC points, etc.), doubles negative swaps and reserves extra carry. These are assumptions, NOT measured FTMO execution statistics.
- Remove the previous study's artificial 30-day no-entry termination. Otherwise reuse reviewed engine functions without importing website or trading code.

## Cash accounting

Report funded probability, first-reward receipt probability, unfinished status and modeled breaches separately. Mean reward per purchase includes zero for every path without a received reward. For an illustrative $100 fee, net cash by horizon = mean received reward - $100 * (1 - probability of receipt), assuming first-reward fee refund. This is not the current checkout quote, does not include taxes/FX/VPS, and unfinished accounts retain potential value. Losing the fictitious account balance is not a $10,000 cash loss.

## Official references checked

- https://ftmo.com/en/comparison-table/
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://ftmo.com/en/faq/ftmo-swing-account-type/
- https://ftmo.com/en/forbidden-trading-practices/

Swing's general news permission does not override forbidden gap/execution exploitation practices. Do not infer approval of the exact News Pulse pre-event two-sided strategy from generic news permission.
