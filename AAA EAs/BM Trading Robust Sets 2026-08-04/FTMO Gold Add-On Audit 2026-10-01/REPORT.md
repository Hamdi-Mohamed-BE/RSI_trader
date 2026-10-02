# FTMO 2-Step Swing — new 3 Way Gold add-on audit

1 October 2026. Research only; no terminal, chart, risk setting, website or deployment changed.

## Decision

**No demonstrated upgrade. Keep the previous 13 as the benchmark; demo-test the new Gold separately.**
The saved FTMO package already contains the new Gold market-entry variant as EA14, but this audit does not establish that it is installed on any running terminal.

The website's standard version uses limit entries. The FTMO variant changes A/B to market entries because the current guard rejects pending orders. These are different strategies, not interchangeable website performance figures.

## Evidence and limits — read before using the numbers

This is an exploratory offline shared-account replay of native position ledgers, not a fresh shared-account MT5 test. Baseline uses the updated Nasdaq 0.60% stop / ATR6 trail version. Common complete-position history: 29 September 2025 to 26 September 2026 exclusive (362 days). The new Gold native year ends September29; clipping makes comparisons consistent.

Risk is fixed $50 maximum planned initial-stop risk per entry, down-rounded to 0.01 lot. Existing modeled gates: $225 aggregate open risk, $150 per symbol, $300 daily reserved-loss admissions, $9,200 projected floor, seven entries/day, stop new entries after three losing closes. No daily -2%/+4% forced liquidation; that is a different prior research policy. Native costs plus FTMO commission floors; stress reduces gross winners10%, enlarges gross losers10%, adds adverse execution and doubles negative swaps.

**Important sizing limitation:** Gold's native positions were generated at 1% per module with upward lot rounding. This overlay rescales their aggregated final cash. At $50 many trades cannot fit the broker minimum. Also most accepted trades become0.01 lot, so their50% partial close cannot execute. Production source explicitly skips such a partial (`3 Way Gold EA.mq5`, lines207–210). Rescaling native partial-exit cash cannot reproduce that changed management. A new native down-rounded-$50 market-entry run is required before treating these figures as exact package performance.

Floating equity uses an initial-stop reserve proxy, not market marks or ticks. The actual guard has additional $5/position reserves, floating-equity checks and execution reconciliation not reproduced here. Proxy zero breaches cannot certify FTMO compliance. Weekly resampling retains contemporaneous dependencies but distorts multiweek holding and month-end regimes. Settings were selected on overlapping history; these are fitted-history scenario frequencies, not forecast probabilities.

## Common-history continuous account — reference costs

| Metric | Previous13 | Plus market-entry Gold14 |
|---|---:|---:|
| Closed return | +63.61% | +63.43% |
| Profit factor |1.488|1.465|
| Win rate |52.90%|52.75%|
| Closed-balance drawdown |3.95%|3.76%|
| Stop-reserve drawdown (not equity DD)|5.22%|5.40%|
| Trades |775|800|
| Trades/month |65.16|67.27|

Only the breakout module is accepted:29 trades,14 winners, -$120.68 net contribution, PF0.80. Momentum and turn-of-month have zero accepted trades. Gold can displace existing portfolio trades, so its contribution does not equal the whole-account difference. Under stress:28 Gold trades, -$213.84.

## Paired resampled lifecycle — 1,000 paths per case

51 complete source weeks, same random week choices in both portfolios, seed20261001. Horizon180 calendar days. Medians are conditional on reaching the respective milestone; unsuccessful/unfinished paths remain in frequency denominators. Phase2's duration starts after its availability, so separate medians do not sum to total elapsed median.

| Reference metric | Previous13 | Plus Gold14 |
|---|---:|---:|
| Phase1 median |50.0 days|50.7 days|
| Phase2 median from availability |27.0 days|26.8 days|
| Both phases median elapsed |85.6 days|86.6 days|
| Funded activation median |92.4 days|93.1 days|
| First modeled reward receipt median |114.1 days|115.0 days|
| Both phases completed by180d |93.5%|93.1%|
| First modeled receipt by180d |86.5%|85.7%|
| Median first reward among recipients |$212|$216|
| Mean first reward across all paths incl. zeros |$231|$231|

| Stress metric | Previous13 | Plus Gold14 |
|---|---:|---:|
| Historical closed return |+21.92%|+21.15%|
| PF |1.149|1.138|
| Closed-balance DD |8.48%|8.95%|
| Phase1 median |81.6 days|84.6 days|
| Both phases median elapsed |115.0 days|115.9 days|
| First modeled receipt median |135.0 days|138.0 days|
| Both phases by180d |41.1%|38.3%|
| First modeled receipt by180d |26.7%|25.5%|

The small reference differences do not establish statistical superiority or inferiority. Stress is less favorable with Gold. No modeled reserve-proxy breach occurred in these paths; unfinished evaluation is not a rule failure. Post-first-reward survival is not modeled.

## Why the website headline is insufficient

Local cached3y website report (2023-09-05 to2026-09-05): +66.57%, PF1.46,73.28% reported win rate,8.89% native equity DD,378 reported trades. This report is the standard limit-entry build and uses a different period/sizing/trade-count basis from the position-aggregated pipeline. It is not a14-EA FTMO account result. Public URL could not be fetched during this audit; cached native evidence was used.

The frozen BEST pipeline lost20.3%, PF0.74 on the older2019–2021 holdout. Its market-entry compatibility diagnostic lost6.59%, PF0.931 there. Deflated Sharpe for BEST was63%, below the pipeline95% gate. Neither full trio is independently qualified for promotion.

## FTMO rules and timing conventions

Official2-Step objectives checked1 October2026: +10% Challenge, +5% Verification, four opening days per phase,5% daily equity loss and10% static overall loss. Reward request eligibility after at least14 days from first funded trade, positive closed profit and flat account. Base reward share80%.

This replay assumes two business days between phases, five to funded activation, at least$25 funded closed profit,14 calendar days from first funded trade and four business days from request to receipt. These are planning conventions, not promised FTMO processing times. No fees/refunds/taxes or subsequent payouts modeled.

Sources: https://ftmo.com/en/trading-objectives/ and https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/

Results, source hashes, cash reconciliation and inherited engine tests are saved in RESULTS.json, PROVENANCE.json and CHECKS.json. No live-account audit was performed.
