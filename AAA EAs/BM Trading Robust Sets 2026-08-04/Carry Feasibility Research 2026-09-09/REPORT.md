# Currency carry: data and broker feasibility

Decision: park the CFD implementation pending historical forward quotes and broker financing. No backtest or promotion performed.

The connected terminal was checked read-only on 2026-09-09 and reported Exness-MT5Trial16. Current symbol swap settings are points per lot under swap mode 1. These are a snapshot, not historical rates or a guarantee of account-specific charges.

| Symbol | Long swap | Short swap |
|---|---:|---:|
| EURUSD | -5.7 | 0.0 |
| GBPUSD | -1.4 | -1.4 |
| USDJPY | 0.0 | -13.3 |
| AUDUSD | 0.0 | -1.8 |
| NZDUSD | -3.9 | 0.0 |
| USDCAD | 0.0 | -8.1 |
| USDCHF | 0.0 | -9.4 |

None of these seven symbols currently advertises a positive swap credit. Selecting a zero-cost side can avoid a charge, but does not reproduce institutional carry income. A forward-implied signal could still predict spot returns; that separate hypothesis has not been tested here.

## Sources checked

- Carry, Koijen et al., published 2018: https://www.aqr.com/Insights/Research/Journal-Article/Carry
- Original paper data description uses currency spot and one-month forwards: https://www.fmg.ac.uk/sites/default/files/2020-08/Ralph-Koijen-paper.pdf
- AQR factor dataset page includes carry factor evidence, but is not a verified per-currency forward quote and broker financing dataset: https://www.aqr.com/Insights/Datasets/Century-of-Factor-Premia-Monthly
- Related replication package located (different paper); contents and coverage not verified: https://www.openicpsr.org/openicpsr/project/231408/version/V1/view
- Exness public tick history supplies bid/ask price history, not a historical financing schedule: https://www.exness.global/tick-history/
- Exness swap explanation: https://get.exness.help/hc/en-us/articles/360014709151-About-swap
- Account-specific swap-free eligibility: https://get.exness.help/hc/en-us/articles/4402341895570-Swap-free-status

No matching historical financing archive was found in the local filename search or the official public sources checked. This does not establish that none exists; broker support or a licensed data provider may supply it.

## What would make a raw test possible

1. Timestamped spot and one-month forward bid/ask quotes for a fixed currency universe, with quote conventions and maturities.
2. Historical broker swap charges/credits and commission terms for the target account over the same interval.
3. Monthly carry rankings built only from information available at rebalance; separate institutional forward returns from CFD spot P/L plus actual financing.

Current swaps cannot be applied retroactively to claim a faithful historical test. Policy-rate differences would be a proxy, requiring separate labeling and a separate research hypothesis.
